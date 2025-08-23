#!/usr/bin/env python3
"""
Enhanced PBIX UI Parser
Parses the extracted visual configuration data to provide detailed information
about each visualization type, data bindings, and DAX queries.
"""

import json
import re
from typing import Dict, List, Any, Optional


class PBIXVisualParser:
    """Parse Power BI visual configurations and extract detailed information."""
    
    # Map of Power BI visual type codes to readable names
    VISUAL_TYPE_MAP = {
        'actionButton': 'Action Button',
        'card': 'Card',
        'columnChart': 'Column Chart',
        'barChart': 'Bar Chart',
        'lineChart': 'Line Chart',
        'areaChart': 'Area Chart',
        'pieChart': 'Pie Chart',
        'donutChart': 'Donut Chart',
        'tableEx': 'Table',
        'matrix': 'Matrix',
        'slicer': 'Slicer',
        'gauge': 'Gauge',
        'scatterChart': 'Scatter Chart',
        'map': 'Map',
        'filledMap': 'Filled Map',
        'treemap': 'Treemap',
        'waterfallChart': 'Waterfall Chart',
        'funnelChart': 'Funnel Chart',
        'ribbonChart': 'Ribbon Chart',
        'textbox': 'Text Box',
        'shape': 'Shape',
        'image': 'Image',
        'multiRowCard': 'Multi-row Card',
        'kpi': 'KPI',
        'stackedAreaChart': 'Stacked Area Chart',
        'clusteredBarChart': 'Clustered Bar Chart',
        'stackedBarChart': 'Stacked Bar Chart',
        'clusteredColumnChart': 'Clustered Column Chart',
        'stackedColumnChart': 'Stacked Column Chart',
        'lineStackedColumnComboChart': 'Line and Stacked Column Chart',
        'lineClusteredColumnComboChart': 'Line and Clustered Column Chart',
        '100stackedBarChart': '100% Stacked Bar Chart',
        '100stackedColumnChart': '100% Stacked Column Chart',
        'htmlViewer': 'HTML Viewer'
    }
    
    def __init__(self):
        self.parsed_visuals = []
        self.visual_queries = []
        self.report_summary = {}
    
    def parse_visual_config(self, config_str: str) -> Dict[str, Any]:
        """Parse the visual configuration JSON string."""
        try:
            if config_str.startswith('{'):
                config = json.loads(config_str)
            else:
                # Sometimes the config is nested in quotes
                config = json.loads(config_str.strip('"'))
        except (json.JSONDecodeError, ValueError):
            return {"error": "Failed to parse config", "raw": config_str[:200]}
        
        return config
    
    def extract_visual_type(self, config: Dict) -> str:
        """Extract the visual type from configuration."""
        if 'singleVisual' in config and 'visualType' in config['singleVisual']:
            visual_type = config['singleVisual']['visualType']
            return self.VISUAL_TYPE_MAP.get(visual_type, visual_type)
        
        return "Unknown"
    
    def extract_data_roles(self, config: Dict) -> List[Dict]:
        """Extract data roles (field bindings) from visual configuration."""
        data_roles = []
        
        try:
            if 'singleVisual' in config:
                single_visual = config['singleVisual']
                
                # Look for query information
                if 'query' in single_visual:
                    query = single_visual['query']
                    if 'dataRoles' in query:
                        data_roles = query['dataRoles']
                
                # Look for projections (field bindings)
                if 'projections' in single_visual:
                    projections = single_visual['projections']
                    for role_name, fields in projections.items():
                        if isinstance(fields, list):
                            for field in fields:
                                data_roles.append({
                                    'role': role_name,
                                    'field': field
                                })
                
                # Look for dataRoles directly
                if 'dataRoles' in single_visual:
                    data_roles.extend(single_visual['dataRoles'])
        
        except Exception as e:
            data_roles.append({"error": str(e)})
        
        return data_roles
    
    def extract_visual_properties(self, config: Dict) -> Dict:
        """Extract visual formatting properties."""
        properties = {}
        
        try:
            if 'singleVisual' in config and 'objects' in config['singleVisual']:
                objects = config['singleVisual']['objects']
                
                for object_name, object_configs in objects.items():
                    properties[object_name] = []
                    
                    if isinstance(object_configs, list):
                        for obj_config in object_configs:
                            if 'properties' in obj_config:
                                properties[object_name].append(obj_config['properties'])
        
        except Exception as e:
            properties['error'] = str(e)
        
        return properties
    
    def extract_text_content(self, config: Dict) -> Optional[str]:
        """Extract text content from text-based visuals."""
        try:
            if 'singleVisual' in config and 'objects' in config['singleVisual']:
                objects = config['singleVisual']['objects']
                
                # Look for text in various locations
                if 'text' in objects:
                    for text_config in objects['text']:
                        if 'properties' in text_config and 'text' in text_config['properties']:
                            text_expr = text_config['properties']['text']
                            if 'expr' in text_expr and 'Literal' in text_expr['expr']:
                                return text_expr['expr']['Literal']['Value'].strip("'")
                
                # Look for general properties that might contain text
                for obj_name, obj_configs in objects.items():
                    if isinstance(obj_configs, list):
                        for obj_config in obj_configs:
                            if 'properties' in obj_config:
                                props = obj_config['properties']
                                for prop_name, prop_value in props.items():
                                    if 'text' in prop_name.lower() and isinstance(prop_value, dict):
                                        if 'expr' in prop_value and 'Literal' in prop_value['expr']:
                                            return prop_value['expr']['Literal']['Value'].strip("'")
        
        except Exception:
            pass
        
        return None
    
    def extract_bookmarks_and_actions(self, config: Dict) -> Dict:
        """Extract bookmark and action information."""
        actions = {}
        
        try:
            if 'singleVisual' in config and 'vcObjects' in config['singleVisual']:
                vc_objects = config['singleVisual']['vcObjects']
                
                if 'visualLink' in vc_objects:
                    for link_config in vc_objects['visualLink']:
                        if 'properties' in link_config:
                            props = link_config['properties']
                            
                            link_type = None
                            bookmark = None
                            
                            if 'type' in props and 'expr' in props['type']:
                                link_type = props['type']['expr']['Literal']['Value'].strip("'")
                            
                            if 'bookmark' in props and 'expr' in props['bookmark']:
                                bookmark = props['bookmark']['expr']['Literal']['Value'].strip("'")
                            
                            actions['link_type'] = link_type
                            actions['bookmark'] = bookmark
        
        except Exception as e:
            actions['error'] = str(e)
        
        return actions
    
    def parse_ui_data(self, ui_data_file: str) -> Dict[str, Any]:
        """Parse the extracted UI data and enhance it with detailed analysis."""
        with open(ui_data_file, 'r', encoding='utf-8') as f:
            ui_data = json.load(f)
        
        enhanced_data = {
            "report_summary": self._create_report_summary(ui_data),
            "pages": [],
            "all_visualizations": [],
            "visual_types": {},
            "bookmarks": [],
            "custom_visuals": ui_data.get("custom_visuals", [])
        }
        
        # Process each page
        for page in ui_data.get("report_pages", []):
            enhanced_page = self._enhance_page_data(page)
            enhanced_data["pages"].append(enhanced_page)
            enhanced_data["all_visualizations"].extend(enhanced_page["visualizations"])
        
        # Create visual type summary
        for visual in enhanced_data["all_visualizations"]:
            vtype = visual["enhanced_type"]
            enhanced_data["visual_types"][vtype] = enhanced_data["visual_types"].get(vtype, 0) + 1
        
        # Extract all bookmarks
        for visual in enhanced_data["all_visualizations"]:
            if visual["actions"].get("bookmark"):
                enhanced_data["bookmarks"].append({
                    "bookmark_id": visual["actions"]["bookmark"],
                    "visual_id": visual["id"],
                    "visual_type": visual["enhanced_type"],
                    "page": visual.get("page_name", "Unknown")
                })
        
        return enhanced_data
    
    def _create_report_summary(self, ui_data: Dict) -> Dict:
        """Create a high-level summary of the report."""
        return {
            "total_pages": len(ui_data.get("report_pages", [])),
            "total_visuals": len(ui_data.get("visualizations", [])),
            "custom_visuals_count": len(ui_data.get("custom_visuals", [])),
            "report_size": f"{ui_data.get('report_pages', [{}])[0].get('width', 0)}x{ui_data.get('report_pages', [{}])[0].get('height', 0)}" if ui_data.get("report_pages") else "Unknown"
        }
    
    def _enhance_page_data(self, page: Dict) -> Dict:
        """Enhance page data with detailed visual analysis."""
        enhanced_page = {
            "name": page.get("name", "Unknown"),
            "display_name": self._clean_page_name(page.get("name", "Unknown")),
            "id": page.get("id"),
            "size": f"{page.get('width', 0)}x{page.get('height', 0)}",
            "visual_count": len(page.get("visualizations", [])),
            "visualizations": []
        }
        
        for visual in page.get("visualizations", []):
            enhanced_visual = self._enhance_visual_data(visual, page.get("name", "Unknown"))
            enhanced_page["visualizations"].append(enhanced_visual)
        
        return enhanced_page
    
    def _enhance_visual_data(self, visual: Dict, page_name: str) -> Dict:
        """Enhance visual data with parsed configuration."""
        config_str = visual.get("properties", "{}")
        config = self.parse_visual_config(config_str)
        
        enhanced_visual = {
            "id": visual.get("id"),
            "page_name": page_name,
            "enhanced_type": self.extract_visual_type(config),
            "original_type": visual.get("type", "unknown"),
            "position": {
                "x": round(visual.get("x", 0), 1),
                "y": round(visual.get("y", 0), 1),
                "width": round(visual.get("width", 0), 1),
                "height": round(visual.get("height", 0), 1),
                "z_order": visual.get("z_order", 0)
            },
            "data_roles": self.extract_data_roles(config),
            "properties": self.extract_visual_properties(config),
            "text_content": self.extract_text_content(config),
            "actions": self.extract_bookmarks_and_actions(config),
            "config_size": len(config_str)
        }
        
        return enhanced_visual
    
    def _clean_page_name(self, name: str) -> str:
        """Convert technical page names to more readable format."""
        if name.startswith("ReportSection"):
            # Try to extract meaningful name or use default
            if len(name) > 50:  # Likely a UUID-style name
                return f"Page {name[-4:]}"  # Use last 4 chars as identifier
            else:
                return name.replace("ReportSection", "Page ")
        return name
    
    def generate_report(self, enhanced_data: Dict) -> str:
        """Generate a comprehensive report of the Power BI structure."""
        report = []
        
        # Header
        report.append("="*80)
        report.append("POWER BI REPORT STRUCTURE - DETAILED ANALYSIS")
        report.append("="*80)
        
        # Summary
        summary = enhanced_data["report_summary"]
        report.append(f"\\n📊 REPORT SUMMARY")
        report.append("-" * 40)
        report.append(f"Pages: {summary['total_pages']}")
        report.append(f"Total Visualizations: {summary['total_visuals']}")
        report.append(f"Custom Visuals: {summary['custom_visuals_count']}")
        report.append(f"Report Size: {summary['report_size']}")
        
        # Visual Types
        report.append(f"\\n📈 VISUALIZATION TYPES")
        report.append("-" * 40)
        for vtype, count in sorted(enhanced_data["visual_types"].items()):
            report.append(f"{vtype}: {count}")
        
        # Pages Detail
        report.append(f"\\n📄 PAGES DETAIL")
        report.append("-" * 40)
        
        for i, page in enumerate(enhanced_data["pages"], 1):
            report.append(f"\\n{i}. {page['display_name']}")
            report.append(f"   Technical Name: {page['name']}")
            report.append(f"   Size: {page['size']}")
            report.append(f"   Visuals: {page['visual_count']}")
            
            # Show visualizations on this page
            for j, visual in enumerate(page["visualizations"], 1):
                report.append(f"   {j}. {visual['enhanced_type']} (ID: {visual['id']})")
                report.append(f"      Position: ({visual['position']['x']}, {visual['position']['y']})")
                report.append(f"      Size: {visual['position']['width']}x{visual['position']['height']}")
                
                if visual['text_content']:
                    report.append(f"      Text: '{visual['text_content']}'")
                
                if visual['data_roles']:
                    report.append(f"      Data Roles: {len(visual['data_roles'])}")
                
                if visual['actions'].get('bookmark'):
                    report.append(f"      Action: Bookmark ({visual['actions']['bookmark']})")
        
        # Bookmarks
        if enhanced_data["bookmarks"]:
            report.append(f"\\n🔖 BOOKMARKS")
            report.append("-" * 40)
            for bookmark in enhanced_data["bookmarks"]:
                report.append(f"  {bookmark['bookmark_id']}")
                report.append(f"    Visual: {bookmark['visual_type']} (ID: {bookmark['visual_id']})")
                report.append(f"    Page: {bookmark['page']}")
        
        # Custom Visuals
        if enhanced_data["custom_visuals"]:
            report.append(f"\\n🎨 CUSTOM VISUALS")
            report.append("-" * 40)
            for visual in enhanced_data["custom_visuals"]:
                report.append(f"  {visual['file_path']}")
                report.append(f"    Size: {visual['size']} bytes")
        
        return "\\n".join(report)


def main():
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Parse extracted Power BI UI data")
    parser.add_argument("ui_data_file", help="Path to ui_components.json file")
    parser.add_argument("--output", "-o", help="Output file for enhanced data")
    parser.add_argument("--report", "-r", help="Output file for text report")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.ui_data_file):
        print(f"Error: UI data file not found: {args.ui_data_file}")
        sys.exit(1)
    
    parser = PBIXVisualParser()
    enhanced_data = parser.parse_ui_data(args.ui_data_file)
    
    # Save enhanced data
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(enhanced_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"Enhanced data saved to: {args.output}")
    
    # Generate report
    report = parser.generate_report(enhanced_data)
    
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved to: {args.report}")
    else:
        print(report)


if __name__ == "__main__":
    import os
    main()