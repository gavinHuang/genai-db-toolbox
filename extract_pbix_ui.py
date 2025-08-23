#!/usr/bin/env python3
"""
Advanced PBIX UI Layer Extraction Tool
Extracts report pages, visualizations, and UI elements directly from PBIX files
without requiring Power BI Desktop or pbi-tools dependencies.
"""

import zipfile
import json
import argparse
import os
import sys
from pathlib import Path
import base64
from typing import Dict, List, Any, Optional


class PBIXUIExtractor:
    """Extract UI layer components from PBIX files."""
    
    def __init__(self, pbix_path: str):
        self.pbix_path = Path(pbix_path)
        self.temp_dir = None
        
    def extract_ui_components(self, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Extract all UI components from the PBIX file."""
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        ui_data = {
            "report_pages": [],
            "visualizations": [],
            "layouts": {},
            "themes": {},
            "bookmarks": [],
            "custom_visuals": [],
            "filters": [],
            "report_metadata": {}
        }
        
        try:
            with zipfile.ZipFile(self.pbix_path, 'r') as pbix_zip:
                # List all files in the PBIX
                file_list = pbix_zip.namelist()
                print(f"Files in PBIX: {len(file_list)}")
                for file_name in file_list:
                    print(f"  - {file_name}")
                
                # Extract Layout JSON (contains report pages and visuals)
                layout_files = [f for f in file_list if 'Layout' in f or 'layout' in f]
                for layout_file in layout_files:
                    print(f"\n=== Extracting Layout: {layout_file} ===")
                    layout_data = self._extract_layout_file(pbix_zip, layout_file)
                    if layout_data:
                        ui_data["layouts"][layout_file] = layout_data
                        
                        # Parse report pages
                        pages = self._parse_report_pages(layout_data)
                        ui_data["report_pages"].extend(pages)
                        
                        # Parse visualizations
                        visuals = self._parse_visualizations(layout_data)
                        ui_data["visualizations"].extend(visuals)
                        
                        # Parse filters
                        filters = self._parse_filters(layout_data)
                        ui_data["filters"].extend(filters)
                
                # Extract Report metadata
                metadata_files = [f for f in file_list if 'Metadata' in f or 'metadata' in f]
                for metadata_file in metadata_files:
                    print(f"\n=== Extracting Metadata: {metadata_file} ===")
                    metadata = self._extract_metadata_file(pbix_zip, metadata_file)
                    if metadata:
                        ui_data["report_metadata"][metadata_file] = metadata
                
                # Extract Custom Visuals
                visual_files = [f for f in file_list if '.visual' in f or 'CustomVisuals' in f]
                for visual_file in visual_files:
                    print(f"\n=== Extracting Custom Visual: {visual_file} ===")
                    visual_data = self._extract_custom_visual(pbix_zip, visual_file)
                    if visual_data:
                        ui_data["custom_visuals"].append(visual_data)
                
                # Extract Version and other metadata
                version_files = [f for f in file_list if 'Version' in f or 'version' in f]
                for version_file in version_files:
                    print(f"\n=== Extracting Version: {version_file} ===")
                    version_data = self._extract_text_file(pbix_zip, version_file)
                    if version_data:
                        ui_data["report_metadata"][version_file] = version_data
                
                # Save extracted data if output directory specified
                if output_dir:
                    self._save_ui_data(ui_data, output_dir)
                    
        except Exception as e:
            print(f"Error extracting UI components: {e}")
            import traceback
            traceback.print_exc()
            
        return ui_data
    
    def _extract_layout_file(self, pbix_zip: zipfile.ZipFile, file_path: str) -> Optional[Dict]:
        """Extract and parse layout JSON file."""
        try:
            with pbix_zip.open(file_path) as file:
                content = file.read()
                
                # Try to decode as UTF-16 first (common in PBIX files)
                try:
                    text_content = content.decode('utf-16le')
                except UnicodeDecodeError:
                    try:
                        text_content = content.decode('utf-8')
                    except UnicodeDecodeError:
                        text_content = content.decode('utf-8', errors='ignore')
                
                # Parse JSON
                if text_content.strip():
                    try:
                        return json.loads(text_content)
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error in {file_path}: {e}")
                        # Save raw content for inspection
                        return {"raw_content": text_content[:1000] + "..." if len(text_content) > 1000 else text_content}
                        
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
        return None
    
    def _extract_metadata_file(self, pbix_zip: zipfile.ZipFile, file_path: str) -> Optional[Dict]:
        """Extract metadata file."""
        return self._extract_layout_file(pbix_zip, file_path)
    
    def _extract_custom_visual(self, pbix_zip: zipfile.ZipFile, file_path: str) -> Optional[Dict]:
        """Extract custom visual information."""
        try:
            with pbix_zip.open(file_path) as file:
                content = file.read()
                
                # For binary files, just return basic info
                return {
                    "file_path": file_path,
                    "size": len(content),
                    "type": "custom_visual"
                }
        except Exception as e:
            print(f"Error reading custom visual {file_path}: {e}")
            
        return None
    
    def _extract_text_file(self, pbix_zip: zipfile.ZipFile, file_path: str) -> Optional[str]:
        """Extract simple text file."""
        try:
            with pbix_zip.open(file_path) as file:
                content = file.read()
                
                try:
                    return content.decode('utf-16le')
                except UnicodeDecodeError:
                    try:
                        return content.decode('utf-8')
                    except UnicodeDecodeError:
                        return content.decode('utf-8', errors='ignore')
                        
        except Exception as e:
            print(f"Error reading text file {file_path}: {e}")
            
        return None
    
    def _parse_report_pages(self, layout_data: Dict) -> List[Dict]:
        """Parse report pages from layout data."""
        pages = []
        
        try:
            # Look for pages in various possible locations
            if isinstance(layout_data, dict):
                # Common locations for page information
                possible_page_keys = ['pages', 'reportPages', 'sections', 'Pages', 'ReportPages']
                
                for key in possible_page_keys:
                    if key in layout_data:
                        page_data = layout_data[key]
                        if isinstance(page_data, list):
                            for page in page_data:
                                pages.append(self._parse_single_page(page))
                        elif isinstance(page_data, dict):
                            pages.append(self._parse_single_page(page_data))
                
                # Also check for nested structures
                for key, value in layout_data.items():
                    if isinstance(value, dict) and any(pk in value for pk in possible_page_keys):
                        nested_pages = self._parse_report_pages(value)
                        pages.extend(nested_pages)
                        
        except Exception as e:
            print(f"Error parsing report pages: {e}")
            
        return pages
    
    def _parse_single_page(self, page_data: Dict) -> Dict:
        """Parse a single report page."""
        page_info = {
            "name": page_data.get("name", page_data.get("displayName", "Unknown Page")),
            "id": page_data.get("id", page_data.get("ordinal")),
            "ordinal": page_data.get("ordinal", 0),
            "visibility": page_data.get("visibility", "visible"),
            "width": page_data.get("width", 0),
            "height": page_data.get("height", 0),
            "visualizations": [],
            "filters": [],
            "background": page_data.get("background", {}),
            "raw_data": page_data  # Keep full data for analysis
        }
        
        # Parse visualizations on this page
        visual_keys = ['visuals', 'visualContainers', 'visualizations']
        for vkey in visual_keys:
            if vkey in page_data:
                visuals = page_data[vkey]
                if isinstance(visuals, list):
                    for visual in visuals:
                        page_info["visualizations"].append(self._parse_single_visual(visual))
        
        return page_info
    
    def _parse_visualizations(self, layout_data: Dict) -> List[Dict]:
        """Parse all visualizations from layout data."""
        visuals = []
        
        try:
            # Recursively search for visualizations
            def find_visuals(data, path=""):
                if isinstance(data, dict):
                    # Check for visual indicators
                    if any(key in data for key in ['visualType', 'type', 'config']):
                        visuals.append(self._parse_single_visual(data, path))
                    
                    # Recurse into nested structures
                    for key, value in data.items():
                        find_visuals(value, f"{path}.{key}" if path else key)
                        
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        find_visuals(item, f"{path}[{i}]")
            
            find_visuals(layout_data)
            
        except Exception as e:
            print(f"Error parsing visualizations: {e}")
            
        return visuals
    
    def _parse_single_visual(self, visual_data: Dict, path: str = "") -> Dict:
        """Parse a single visualization."""
        visual_info = {
            "id": visual_data.get("id", visual_data.get("name")),
            "type": visual_data.get("visualType", visual_data.get("type", "unknown")),
            "title": visual_data.get("title", visual_data.get("displayName", "")),
            "x": visual_data.get("x", 0),
            "y": visual_data.get("y", 0),
            "width": visual_data.get("width", 0),
            "height": visual_data.get("height", 0),
            "z_order": visual_data.get("z", visual_data.get("zOrder", 0)),
            "path": path,
            "data_roles": [],
            "properties": {},
            "filters": [],
            "raw_data": visual_data
        }
        
        # Extract data roles (fields used in the visual)
        if "dataRoles" in visual_data:
            visual_info["data_roles"] = visual_data["dataRoles"]
        elif "query" in visual_data and "dataRoles" in visual_data["query"]:
            visual_info["data_roles"] = visual_data["query"]["dataRoles"]
            
        # Extract properties
        if "properties" in visual_data:
            visual_info["properties"] = visual_data["properties"]
        elif "config" in visual_data:
            visual_info["properties"] = visual_data["config"]
            
        # Extract filters
        if "filters" in visual_data:
            visual_info["filters"] = visual_data["filters"]
        
        return visual_info
    
    def _parse_filters(self, layout_data: Dict) -> List[Dict]:
        """Parse filter information from layout data."""
        filters = []
        
        try:
            def find_filters(data, path=""):
                if isinstance(data, dict):
                    if "filters" in data and isinstance(data["filters"], list):
                        for filter_data in data["filters"]:
                            filters.append({
                                "path": path,
                                "filter": filter_data
                            })
                    
                    for key, value in data.items():
                        if key == "filters" and isinstance(value, list):
                            continue  # Already processed above
                        find_filters(value, f"{path}.{key}" if path else key)
                        
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        find_filters(item, f"{path}[{i}]")
            
            find_filters(layout_data)
            
        except Exception as e:
            print(f"Error parsing filters: {e}")
            
        return filters
    
    def _save_ui_data(self, ui_data: Dict, output_dir: str):
        """Save extracted UI data to files."""
        output_path = Path(output_dir)
        
        # Save main UI data as JSON
        with open(output_path / "ui_components.json", 'w', encoding='utf-8') as f:
            json.dump(ui_data, f, indent=2, ensure_ascii=False, default=str)
        
        # Save individual components
        if ui_data["report_pages"]:
            with open(output_path / "report_pages.json", 'w', encoding='utf-8') as f:
                json.dump(ui_data["report_pages"], f, indent=2, ensure_ascii=False, default=str)
        
        if ui_data["visualizations"]:
            with open(output_path / "visualizations.json", 'w', encoding='utf-8') as f:
                json.dump(ui_data["visualizations"], f, indent=2, ensure_ascii=False, default=str)
        
        if ui_data["layouts"]:
            with open(output_path / "layouts.json", 'w', encoding='utf-8') as f:
                json.dump(ui_data["layouts"], f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\nUI data saved to: {output_path}")
        print(f"  - ui_components.json: Complete UI structure")
        print(f"  - report_pages.json: {len(ui_data['report_pages'])} pages")
        print(f"  - visualizations.json: {len(ui_data['visualizations'])} visualizations")
        print(f"  - layouts.json: Raw layout data")


def print_ui_summary(ui_data: Dict):
    """Print a summary of extracted UI components."""
    print("\n" + "="*60)
    print("POWER BI UI STRUCTURE SUMMARY")
    print("="*60)
    
    # Report Pages
    print(f"\n📄 REPORT PAGES ({len(ui_data['report_pages'])})")
    print("-" * 40)
    for i, page in enumerate(ui_data['report_pages'], 1):
        print(f"  {i}. {page['name']}")
        print(f"     ID: {page['id']}")
        print(f"     Size: {page['width']}x{page['height']}")
        print(f"     Visuals: {len(page['visualizations'])}")
        print(f"     Filters: {len(page['filters'])}")
    
    # Visualizations
    print(f"\n📊 VISUALIZATIONS ({len(ui_data['visualizations'])})")
    print("-" * 40)
    visual_types = {}
    for visual in ui_data['visualizations']:
        vtype = visual['type']
        visual_types[vtype] = visual_types.get(vtype, 0) + 1
        
    for vtype, count in visual_types.items():
        print(f"  {vtype}: {count}")
    
    # Show first few visualizations with details
    for i, visual in enumerate(ui_data['visualizations'][:5], 1):
        print(f"\n  Visual {i}: {visual['type']}")
        print(f"    Title: {visual['title']}")
        print(f"    Position: ({visual['x']}, {visual['y']})")
        print(f"    Size: {visual['width']}x{visual['height']}")
        print(f"    Data Roles: {len(visual['data_roles'])}")
        print(f"    Properties: {len(visual['properties'])}")
    
    if len(ui_data['visualizations']) > 5:
        print(f"    ... and {len(ui_data['visualizations']) - 5} more visualizations")
    
    # Filters
    print(f"\n🔍 FILTERS ({len(ui_data['filters'])})")
    print("-" * 40)
    for i, filter_info in enumerate(ui_data['filters'][:10], 1):
        print(f"  {i}. Path: {filter_info['path']}")
        print(f"     Filter: {str(filter_info['filter'])[:100]}...")
    
    if len(ui_data['filters']) > 10:
        print(f"    ... and {len(ui_data['filters']) - 10} more filters")
    
    # Custom Visuals
    if ui_data['custom_visuals']:
        print(f"\n🎨 CUSTOM VISUALS ({len(ui_data['custom_visuals'])})")
        print("-" * 40)
        for visual in ui_data['custom_visuals']:
            print(f"  {visual['file_path']} ({visual['size']} bytes)")
    
    # Metadata
    if ui_data['report_metadata']:
        print(f"\n📋 METADATA ({len(ui_data['report_metadata'])} files)")
        print("-" * 40)
        for filename in ui_data['report_metadata']:
            print(f"  {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract UI layer components from Power BI (.pbix) files"
    )
    parser.add_argument("pbix_file", help="Path to the PBIX file")
    parser.add_argument("--output-dir", "-o", help="Output directory for extracted files")
    parser.add_argument("--save-raw", action="store_true", help="Save raw layout files")
    parser.add_argument("--no-summary", action="store_true", help="Don't print summary")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pbix_file):
        print(f"Error: PBIX file not found: {args.pbix_file}")
        sys.exit(1)
    
    print(f"Extracting UI components from: {args.pbix_file}")
    
    extractor = PBIXUIExtractor(args.pbix_file)
    ui_data = extractor.extract_ui_components(args.output_dir)
    
    if not args.no_summary:
        print_ui_summary(ui_data)
    
    if args.output_dir:
        print(f"\nExtracted UI data saved to: {args.output_dir}")


if __name__ == "__main__":
    main()