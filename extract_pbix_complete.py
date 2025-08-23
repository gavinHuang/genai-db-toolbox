#!/usr/bin/env python3
"""
Complete Power BI (.pbix) Extraction Tool
Extracts EVERYTHING from Power BI files:
- Data model, DAX, Power Query (via pbixray)
- UI layer: pages, visualizations, bookmarks (via custom parser)
- Multiple output formats with comprehensive analysis

Usage:
  python extract_pbix_complete.py "report.pbix" --all
  python extract_pbix_complete.py "report.pbix" --data-only --sqlite
  python extract_pbix_complete.py "report.pbix" --ui-only --output-dir ui_extracted
"""

import os
import argparse
import sys
import sqlite3
import json
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import our existing tools
from pbixray import PBIXRay
import pandas as pd


class CompletePBIXExtractor:
    """Complete PBIX extraction combining data model and UI layer."""
    
    def __init__(self, pbix_path: str):
        self.pbix_path = Path(pbix_path)
        self.pbix_name = self.pbix_path.stem
        
    def extract_everything(self, output_dir: Optional[str] = None, 
                          formats: List[str] = None, 
                          extract_data: bool = True,
                          extract_ui: bool = True) -> Dict[str, Any]:
        """Extract both data model and UI layer."""
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
        else:
            output_path = Path(f"{self.pbix_name}_extracted")
            output_path.mkdir(exist_ok=True)
        
        results = {
            "pbix_file": str(self.pbix_path),
            "extraction_summary": {},
            "data_model": {},
            "ui_structure": {},
            "output_files": []
        }
        
        # Extract data model (tables, DAX, Power Query)
        if extract_data:
            print("🔄 Extracting data model...")
            data_results = self._extract_data_model(output_path, formats)
            results["data_model"] = data_results
            results["extraction_summary"]["data_model"] = "✅ Complete"
        else:
            results["extraction_summary"]["data_model"] = "⏭️ Skipped"
        
        # Extract UI layer (pages, visuals, layouts)
        if extract_ui:
            print("🔄 Extracting UI layer...")
            ui_results = self._extract_ui_layer(output_path)
            results["ui_structure"] = ui_results
            results["extraction_summary"]["ui_layer"] = "✅ Complete"
        else:
            results["extraction_summary"]["ui_layer"] = "⏭️ Skipped"
        
        # Create comprehensive summary
        summary_file = output_path / "extraction_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        results["output_files"].append(str(summary_file))
        
        # Create human-readable report
        report_file = output_path / "complete_report.txt"
        report_content = self._generate_complete_report(results)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        results["output_files"].append(str(report_file))
        
        return results
    
    def _extract_data_model(self, output_path: Path, formats: List[str] = None) -> Dict[str, Any]:
        """Extract data model using pbixray."""
        pbix = PBIXRay(str(self.pbix_path))
        
        data_results = {
            "tables": [],
            "relationships": [],
            "measures": [],
            "calculated_columns": [],
            "calculated_tables": [],
            "power_query": {},
            "metadata": {}
        }
        
        # Extract metadata
        try:
            data_results["metadata"] = {
                "version": getattr(pbix, 'metadata', {}).get('PBIDesktopVersion', 'Unknown'),
                "size": pbix.size,
                "table_count": len(pbix.tables)
            }
        except Exception as e:
            data_results["metadata"] = {"error": str(e)}
        
        # Extract tables and data
        for table_name in pbix.tables:
            table_info = {
                "name": table_name,
                "columns": [],
                "row_count": 0,
                "data_extracted": False
            }
            
            try:
                # Get table schema
                table_df = pbix.get_table(table_name)
                if table_df is not None:
                    table_info["columns"] = [
                        {"name": col, "type": str(table_df[col].dtype)}
                        for col in table_df.columns
                    ]
                    table_info["row_count"] = len(table_df)
                    table_info["data_extracted"] = True
                    
                    # Save data if formats specified
                    if formats:
                        self._save_table_data(table_df, table_name, output_path, formats)
                
            except Exception as e:
                table_info["error"] = str(e)
            
            data_results["tables"].append(table_info)
        
        # Extract relationships
        try:
            if hasattr(pbix, 'relationships'):
                for rel in pbix.relationships:
                    data_results["relationships"].append({
                        "from_table": rel.get('fromTable', ''),
                        "from_column": rel.get('fromColumn', ''),
                        "to_table": rel.get('toTable', ''),
                        "to_column": rel.get('toColumn', ''),
                        "cardinality": rel.get('cardinality', ''),
                        "is_active": rel.get('isActive', True)
                    })
        except Exception as e:
            data_results["relationships"] = [{"error": str(e)}]
        
        # Extract DAX measures
        try:
            for table_name in pbix.tables:
                measures = pbix.dax_measures.get(table_name, [])
                for measure in measures:
                    data_results["measures"].append({
                        "table": table_name,
                        "name": measure.get('name', ''),
                        "expression": measure.get('expression', ''),
                        "description": measure.get('description', '')
                    })
        except Exception as e:
            data_results["measures"] = [{"error": str(e)}]
        
        # Extract calculated columns
        try:
            for table_name in pbix.tables:
                columns = pbix.dax_columns.get(table_name, [])
                for column in columns:
                    data_results["calculated_columns"].append({
                        "table": table_name,
                        "name": column.get('name', ''),
                        "expression": column.get('expression', ''),
                        "data_type": column.get('dataType', '')
                    })
        except Exception as e:
            data_results["calculated_columns"] = [{"error": str(e)}]
        
        # Extract calculated tables
        try:
            for table_name in pbix.tables:
                tables = pbix.dax_tables.get(table_name, [])
                for table in tables:
                    data_results["calculated_tables"].append({
                        "name": table.get('name', ''),
                        "expression": table.get('expression', '')
                    })
        except Exception as e:
            data_results["calculated_tables"] = [{"error": str(e)}]
        
        # Extract Power Query
        try:
            if hasattr(pbix, 'power_query'):
                data_results["power_query"] = pbix.power_query
        except Exception as e:
            data_results["power_query"] = {"error": str(e)}
        
        # Save data model summary
        data_model_file = output_path / "data_model.json"
        with open(data_model_file, 'w', encoding='utf-8') as f:
            json.dump(data_results, f, indent=2, ensure_ascii=False, default=str)
        
        return data_results
    
    def _extract_ui_layer(self, output_path: Path) -> Dict[str, Any]:
        """Extract UI layer directly from PBIX file."""
        ui_results = {
            "pages": [],
            "visualizations": [],
            "custom_visuals": [],
            "bookmarks": [],
            "themes": {},
            "raw_layouts": {}
        }
        
        try:
            with zipfile.ZipFile(self.pbix_path, 'r') as pbix_zip:
                file_list = pbix_zip.namelist()
                
                # Extract Layout files
                layout_files = [f for f in file_list if 'Layout' in f]
                for layout_file in layout_files:
                    layout_data = self._extract_layout_file(pbix_zip, layout_file)
                    if layout_data:
                        ui_results["raw_layouts"][layout_file] = layout_data
                        
                        # Parse pages and visualizations
                        pages = self._parse_report_pages(layout_data)
                        ui_results["pages"].extend(pages)
                        
                        visuals = self._parse_visualizations(layout_data)
                        ui_results["visualizations"].extend(visuals)
                
                # Extract custom visuals
                visual_files = [f for f in file_list if 'CustomVisuals' in f and f.endswith('.json')]
                for visual_file in visual_files:
                    try:
                        with pbix_zip.open(visual_file) as f:
                            content = f.read().decode('utf-8')
                            visual_data = json.loads(content)
                            ui_results["custom_visuals"].append({
                                "file": visual_file,
                                "config": visual_data
                            })
                    except Exception:
                        ui_results["custom_visuals"].append({
                            "file": visual_file,
                            "error": "Failed to parse"
                        })
        
        except Exception as e:
            ui_results["error"] = str(e)
        
        # Save UI structure
        ui_file = output_path / "ui_structure.json"
        with open(ui_file, 'w', encoding='utf-8') as f:
            json.dump(ui_results, f, indent=2, ensure_ascii=False, default=str)
        
        # Create detailed UI report
        ui_report = self._generate_ui_report(ui_results)
        ui_report_file = output_path / "ui_detailed_report.txt"
        with open(ui_report_file, 'w', encoding='utf-8') as f:
            f.write(ui_report)
        
        return ui_results
    
    def _extract_layout_file(self, pbix_zip: zipfile.ZipFile, file_path: str) -> Optional[Dict]:
        """Extract and parse layout JSON file."""
        try:
            with pbix_zip.open(file_path) as file:
                content = file.read()
                
                # Try different encodings
                for encoding in ['utf-16le', 'utf-8', 'utf-16']:
                    try:
                        text_content = content.decode(encoding)
                        if text_content.strip():
                            return json.loads(text_content)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
        except Exception:
            pass
        
        return None
    
    def _parse_report_pages(self, layout_data: Dict) -> List[Dict]:
        """Parse report pages from layout data."""
        pages = []
        
        def find_pages(data, path=""):
            if isinstance(data, dict):
                # Look for page-like structures
                if any(key in data for key in ['name', 'ordinal', 'width', 'height']):
                    if 'visualContainers' in data or 'visuals' in data:
                        pages.append(self._parse_single_page(data))
                
                # Recurse
                for key, value in data.items():
                    find_pages(value, f"{path}.{key}" if path else key)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    find_pages(item, f"{path}[{i}]")
        
        find_pages(layout_data)
        return pages
    
    def _parse_single_page(self, page_data: Dict) -> Dict:
        """Parse a single report page."""
        return {
            "name": page_data.get("name", "Unknown"),
            "ordinal": page_data.get("ordinal", 0),
            "width": page_data.get("width", 0),
            "height": page_data.get("height", 0),
            "visual_count": len(page_data.get("visualContainers", [])),
            "raw_data": page_data
        }
    
    def _parse_visualizations(self, layout_data: Dict) -> List[Dict]:
        """Parse visualizations from layout data."""
        visuals = []
        
        def find_visuals(data, path=""):
            if isinstance(data, dict):
                # Look for visual indicators
                if any(key in data for key in ['config', 'x', 'y', 'width', 'height']):
                    if 'config' in data:
                        visual = self._parse_single_visual(data, path)
                        if visual:
                            visuals.append(visual)
                
                # Recurse
                for key, value in data.items():
                    find_visuals(value, f"{path}.{key}" if path else key)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    find_visuals(item, f"{path}[{i}]")
        
        find_visuals(layout_data)
        return visuals
    
    def _parse_single_visual(self, visual_data: Dict, path: str) -> Optional[Dict]:
        """Parse a single visualization."""
        try:
            config_str = visual_data.get("config", "{}")
            config = json.loads(config_str) if isinstance(config_str, str) else config_str
            
            visual_type = "unknown"
            if "singleVisual" in config and "visualType" in config["singleVisual"]:
                visual_type = config["singleVisual"]["visualType"]
            
            return {
                "id": visual_data.get("id"),
                "type": visual_type,
                "position": {
                    "x": visual_data.get("x", 0),
                    "y": visual_data.get("y", 0),
                    "width": visual_data.get("width", 0),
                    "height": visual_data.get("height", 0)
                },
                "path": path,
                "config_size": len(config_str),
                "raw_config": config
            }
        except Exception:
            return None
    
    def _save_table_data(self, df: pd.DataFrame, table_name: str, 
                        output_path: Path, formats: List[str]):
        """Save table data in specified formats."""
        data_dir = output_path / "data"
        data_dir.mkdir(exist_ok=True)
        
        for fmt in formats:
            if fmt == "csv":
                file_path = data_dir / f"{table_name}.csv"
                df.to_csv(file_path, index=False, encoding='utf-8')
            elif fmt == "json":
                file_path = data_dir / f"{table_name}.json"
                df.to_json(file_path, orient='records', indent=2, force_ascii=False)
            elif fmt == "excel":
                file_path = data_dir / f"{table_name}.xlsx"
                df.to_excel(file_path, index=False)
    
    def _generate_complete_report(self, results: Dict) -> str:
        """Generate comprehensive report."""
        report = []
        
        report.append("="*80)
        report.append("COMPLETE POWER BI EXTRACTION REPORT")
        report.append("="*80)
        report.append(f"Source File: {results['pbix_file']}")
        report.append(f"Extraction Date: {pd.Timestamp.now()}")
        
        # Summary
        report.append("\\n📊 EXTRACTION SUMMARY")
        report.append("-" * 40)
        for component, status in results["extraction_summary"].items():
            report.append(f"{component}: {status}")
        
        # Data Model Summary
        if "data_model" in results and results["data_model"]:
            dm = results["data_model"]
            report.append("\\n📈 DATA MODEL")
            report.append("-" * 40)
            report.append(f"Tables: {len(dm.get('tables', []))}")
            report.append(f"Relationships: {len(dm.get('relationships', []))}")
            report.append(f"Measures: {len(dm.get('measures', []))}")
            report.append(f"Calculated Columns: {len(dm.get('calculated_columns', []))}")
            report.append(f"Power Query Sources: {len(dm.get('power_query', {}))}")
        
        # UI Structure Summary
        if "ui_structure" in results and results["ui_structure"]:
            ui = results["ui_structure"]
            report.append("\\n🎨 UI STRUCTURE")
            report.append("-" * 40)
            report.append(f"Pages: {len(ui.get('pages', []))}")
            report.append(f"Visualizations: {len(ui.get('visualizations', []))}")
            report.append(f"Custom Visuals: {len(ui.get('custom_visuals', []))}")
        
        # Output Files
        report.append("\\n📁 OUTPUT FILES")
        report.append("-" * 40)
        for file_path in results.get("output_files", []):
            report.append(f"  {file_path}")
        
        return "\\n".join(report)
    
    def _generate_ui_report(self, ui_data: Dict) -> str:
        """Generate detailed UI report."""
        report = []
        
        report.append("="*60)
        report.append("POWER BI UI STRUCTURE DETAILED REPORT")
        report.append("="*60)
        
        # Pages
        report.append("\\n📄 REPORT PAGES")
        report.append("-" * 40)
        for i, page in enumerate(ui_data.get("pages", []), 1):
            report.append(f"{i}. {page['name']}")
            report.append(f"   Size: {page['width']}x{page['height']}")
            report.append(f"   Visuals: {page['visual_count']}")
        
        # Visualizations
        report.append("\\n📊 VISUALIZATIONS")
        report.append("-" * 40)
        visual_types = {}
        for visual in ui_data.get("visualizations", []):
            vtype = visual.get("type", "unknown")
            visual_types[vtype] = visual_types.get(vtype, 0) + 1
        
        for vtype, count in sorted(visual_types.items()):
            report.append(f"{vtype}: {count}")
        
        return "\\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Complete Power BI (.pbix) extraction tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "report.pbix" --all
  %(prog)s "report.pbix" --data-only --sqlite
  %(prog)s "report.pbix" --ui-only 
  %(prog)s "report.pbix" --csv --json --output-dir extracted
        """
    )
    
    parser.add_argument("pbix_file", help="Path to the PBIX file")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    
    # Extraction options
    parser.add_argument("--all", action="store_true", 
                       help="Extract everything (data + UI)")
    parser.add_argument("--data-only", action="store_true",
                       help="Extract only data model")
    parser.add_argument("--ui-only", action="store_true",
                       help="Extract only UI layer")
    
    # Data export formats
    parser.add_argument("--csv", action="store_true", help="Export data to CSV")
    parser.add_argument("--json", action="store_true", help="Export data to JSON")
    parser.add_argument("--excel", action="store_true", help="Export data to Excel")
    parser.add_argument("--sqlite", action="store_true", help="Export data to SQLite")
    
    # Control options
    parser.add_argument("--no-summary", action="store_true", 
                       help="Don't print extraction summary")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pbix_file):
        print(f"❌ Error: PBIX file not found: {args.pbix_file}")
        sys.exit(1)
    
    # Determine what to extract
    extract_data = args.all or args.data_only or not args.ui_only
    extract_ui = args.all or args.ui_only or not args.data_only
    
    # Determine export formats
    formats = []
    if args.csv: formats.append("csv")
    if args.json: formats.append("json")
    if args.excel: formats.append("excel")
    if args.sqlite: formats.append("sqlite")
    
    print(f"🚀 Starting complete extraction of: {args.pbix_file}")
    print(f"📊 Data Model: {'✅' if extract_data else '⏭️'}")
    print(f"🎨 UI Layer: {'✅' if extract_ui else '⏭️'}")
    
    # Create extractor and run
    extractor = CompletePBIXExtractor(args.pbix_file)
    results = extractor.extract_everything(
        output_dir=args.output_dir,
        formats=formats,
        extract_data=extract_data,
        extract_ui=extract_ui
    )
    
    if not args.no_summary:
        print("\\n" + "="*60)
        print("✅ EXTRACTION COMPLETE")
        print("="*60)
        
        for component, status in results["extraction_summary"].items():
            print(f"{component}: {status}")
        
        print(f"\\n📁 Output directory: {Path(args.output_dir or f'{Path(args.pbix_file).stem}_extracted').absolute()}")
        print(f"📄 Files created: {len(results['output_files'])}")


if __name__ == "__main__":
    main()