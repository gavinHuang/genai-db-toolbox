import os
import argparse
import sys
import sqlite3
import json
import zipfile
from pathlib import Path
from pbixray import PBIXRay
import pandas as pd  # Optional, for nicer output


# Visual type mapping for better readability
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
    'textbox': 'Text Box',
    'shape': 'Shape',
    'image': 'Image',
    'decompositionTreeVisual': 'Decomposition Tree',
    'keyDriversVisual': 'Key Influencers',
    'qnaVisual': 'Q&A Visual',
    'esriVisual': 'ArcGIS Map'
}


def extract_ui_layer(pbix_path):
    """Extract UI layer (pages, visualizations, bookmarks) from PBIX file."""
    ui_data = {
        "report_pages": [],
        "visualizations": [],
        "visual_summary": {},
        "custom_visuals": [],
        "extraction_info": {
            "method": "Direct PBIX parsing",
            "extracted_files": []
        }
    }
    
    try:
        with zipfile.ZipFile(pbix_path, 'r') as pbix_zip:
            file_list = pbix_zip.namelist()
            
            # Extract Layout files (contains report structure)
            layout_files = [f for f in file_list if 'Layout' in f]
            for layout_file in layout_files:
                ui_data["extraction_info"]["extracted_files"].append(layout_file)
                layout_data = extract_layout_file(pbix_zip, layout_file)
                if layout_data:
                    # Parse pages and visualizations
                    pages = parse_report_pages(layout_data)
                    ui_data["report_pages"].extend(pages)
                    
                    visuals = parse_visualizations(layout_data)
                    ui_data["visualizations"].extend(visuals)
            
            # Extract custom visual information
            visual_files = [f for f in file_list if 'CustomVisuals' in f and f.endswith('.json')]
            for visual_file in visual_files:
                try:
                    with pbix_zip.open(visual_file) as f:
                        content = f.read().decode('utf-8')
                        visual_data = json.loads(content)
                        ui_data["custom_visuals"].append({
                            "file": visual_file,
                            "name": visual_data.get("name", "Unknown"),
                            "version": visual_data.get("version", "Unknown")
                        })
                except Exception:
                    ui_data["custom_visuals"].append({
                        "file": visual_file,
                        "error": "Failed to parse"
                    })
        
        # Create visual type summary
        visual_types = {}
        for visual in ui_data["visualizations"]:
            vtype = visual.get("enhanced_type", visual.get("type", "unknown"))
            visual_types[vtype] = visual_types.get(vtype, 0) + 1
        ui_data["visual_summary"] = visual_types
        
    except Exception as e:
        ui_data["error"] = str(e)
    
    return ui_data


def extract_layout_file(pbix_zip, file_path):
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


def parse_report_pages(layout_data):
    """Parse report pages from layout data."""
    pages = []
    
    def find_pages(data, path=""):
        if isinstance(data, dict):
            # Look for page-like structures
            if "sections" in data and isinstance(data["sections"], list):
                for section in data["sections"]:
                    page = parse_single_page(section)
                    if page:
                        pages.append(page)
            
            # Also check for direct page data
            if any(key in data for key in ['name', 'ordinal', 'width', 'height']):
                if 'visualContainers' in data or 'visuals' in data:
                    page = parse_single_page(data)
                    if page:
                        pages.append(page)
            
            # Recurse through nested structures
            for key, value in data.items():
                if key not in ['sections']:  # Avoid double processing
                    find_pages(value, f"{path}.{key}" if path else key)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                find_pages(item, f"{path}[{i}]")
    
    find_pages(layout_data)
    return pages


def parse_single_page(page_data):
    """Parse a single report page."""
    if not isinstance(page_data, dict):
        return None
    
    page_info = {
        "name": page_data.get("name", f"Page_{page_data.get('ordinal', 'Unknown')}"),
        "display_name": clean_page_name(page_data.get("name", "Unknown Page")),
        "ordinal": page_data.get("ordinal", 0),
        "width": page_data.get("width", 1280),
        "height": page_data.get("height", 720),
        "visual_count": 0,
        "background": page_data.get("background", {}),
        "filters": page_data.get("filters", [])
    }
    
    # Count visualizations
    visual_containers = page_data.get("visualContainers", [])
    if isinstance(visual_containers, list):
        page_info["visual_count"] = len(visual_containers)
    
    return page_info


def parse_visualizations(layout_data):
    """Parse visualizations from layout data."""
    visuals = []
    
    def find_visuals(data, path=""):
        if isinstance(data, dict):
            # Look for visual containers or individual visuals
            if "visualContainers" in data and isinstance(data["visualContainers"], list):
                for visual in data["visualContainers"]:
                    parsed_visual = parse_single_visual(visual, path)
                    if parsed_visual:
                        visuals.append(parsed_visual)
            
            # Look for direct visual configuration
            if "config" in data and isinstance(data.get("config"), str):
                parsed_visual = parse_single_visual(data, path)
                if parsed_visual:
                    visuals.append(parsed_visual)
            
            # Recurse through nested structures
            for key, value in data.items():
                if key not in ['visualContainers']:  # Avoid double processing
                    find_visuals(value, f"{path}.{key}" if path else key)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                find_visuals(item, f"{path}[{i}]")
    
    find_visuals(layout_data)
    return visuals


def parse_single_visual(visual_data, path):
    """Parse a single visualization."""
    if not isinstance(visual_data, dict):
        return None
    
    try:
        # Extract basic position and size
        position_info = {
            "x": round(visual_data.get("x", 0), 1),
            "y": round(visual_data.get("y", 0), 1),
            "width": round(visual_data.get("width", 0), 1),
            "height": round(visual_data.get("height", 0), 1),
            "z_order": visual_data.get("z", visual_data.get("zOrder", 0))
        }
        
        # Parse configuration
        config_str = visual_data.get("config", "{}")
        visual_type = "unknown"
        text_content = None
        data_roles_count = 0
        bookmark_action = None
        
        try:
            if isinstance(config_str, str) and config_str.strip():
                config = json.loads(config_str)
                
                # Extract visual type
                if "singleVisual" in config:
                    single_visual = config["singleVisual"]
                    visual_type = single_visual.get("visualType", "unknown")
                    
                    # Extract data roles count
                    if "projections" in single_visual:
                        projections = single_visual["projections"]
                        data_roles_count = sum(len(v) for v in projections.values() if isinstance(v, list))
                    
                    # Extract text content
                    if "objects" in single_visual:
                        text_content = extract_text_from_objects(single_visual["objects"])
                
                # Extract bookmark actions
                if "vcObjects" in config.get("singleVisual", {}):
                    vc_objects = config["singleVisual"]["vcObjects"]
                    bookmark_action = extract_bookmark_action(vc_objects)
        
        except (json.JSONDecodeError, KeyError):
            pass
        
        # Get human-readable visual type
        enhanced_type = VISUAL_TYPE_MAP.get(visual_type, visual_type.title() if visual_type else "Unknown")
        
        return {
            "id": visual_data.get("id"),
            "type": visual_type,
            "enhanced_type": enhanced_type,
            "position": position_info,
            "text_content": text_content,
            "data_roles_count": data_roles_count,
            "bookmark_action": bookmark_action,
            "config_size": len(config_str),
            "path": path
        }
    
    except Exception:
        return None


def extract_text_from_objects(objects):
    """Extract text content from visual objects."""
    try:
        if "text" in objects:
            for text_config in objects["text"]:
                if "properties" in text_config and "text" in text_config["properties"]:
                    text_expr = text_config["properties"]["text"]
                    if "expr" in text_expr and "Literal" in text_expr["expr"]:
                        return text_expr["expr"]["Literal"]["Value"].strip("'")
    except Exception:
        pass
    return None


def extract_bookmark_action(vc_objects):
    """Extract bookmark action information."""
    try:
        if "visualLink" in vc_objects:
            for link_config in vc_objects["visualLink"]:
                if "properties" in link_config:
                    props = link_config["properties"]
                    if "bookmark" in props and "expr" in props["bookmark"]:
                        return props["bookmark"]["expr"]["Literal"]["Value"].strip("'")
    except Exception:
        pass
    return None


def clean_page_name(name):
    """Convert technical page names to more readable format."""
    if name.startswith("ReportSection"):
        if len(name) > 20:  # Likely a UUID-style name
            return f"Page {name[-4:]}"
        else:
            return name.replace("ReportSection", "Page ")
    return name


def save_table_data(tables, output_dir, data_format, quiet=False):
    """Save table data to files in the specified format"""
    data_dir = os.path.join(output_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    if data_format == 'sqlite':
        # Create SQLite database with all tables
        db_path = os.path.join(data_dir, 'powerbi_data.db')
        save_to_sqlite(tables, db_path, quiet)
    else:
        # Save individual files for other formats
        for table in tables:
            if 'data' in table and table['data'] is not None:
                table_name = table['name']
                # Sanitize filename
                safe_name = "".join(c for c in table_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_name = safe_name.replace(' ', '_')
                
                try:
                    if data_format == 'csv':
                        file_path = os.path.join(data_dir, f"{safe_name}.csv")
                        table['data'].to_csv(file_path, index=False, encoding='utf-8')
                    elif data_format == 'json':
                        file_path = os.path.join(data_dir, f"{safe_name}.json")
                        table['data'].to_json(file_path, orient='records', indent=2)
                    elif data_format == 'excel':
                        file_path = os.path.join(data_dir, f"{safe_name}.xlsx")
                        table['data'].to_excel(file_path, index=False)
                    
                    if not quiet:
                        print(f"Saved {len(table['data'])} rows from '{table_name}' to {file_path}")
                        
                except Exception as e:
                    print(f"Error saving data for table '{table_name}': {e}")


def save_to_sqlite(tables, db_path, quiet=False):
    """Save all table data to a single SQLite database"""
    try:
        # Remove existing database if it exists
        if os.path.exists(db_path):
            os.remove(db_path)
        
        # Create connection to SQLite database
        conn = sqlite3.connect(db_path)
        
        tables_saved = 0
        total_rows = 0
        
        for table in tables:
            if 'data' in table and table['data'] is not None:
                table_name = table['name']
                # Sanitize table name for SQLite
                safe_table_name = "".join(c for c in table_name if c.isalnum() or c in ('_',))
                if not safe_table_name[0].isalpha():
                    safe_table_name = f"table_{safe_table_name}"
                
                try:
                    # Save DataFrame to SQLite
                    table['data'].to_sql(safe_table_name, conn, index=False, if_exists='replace')
                    tables_saved += 1
                    total_rows += len(table['data'])
                    
                    if not quiet:
                        print(f"Saved {len(table['data'])} rows from '{table_name}' to table '{safe_table_name}' in SQLite database")
                        
                except Exception as e:
                    print(f"Error saving table '{table_name}' to SQLite: {e}")
        
        # Create metadata table with information about the extraction
        metadata = pd.DataFrame([
            {
                'extraction_date': pd.Timestamp.now().isoformat(),
                'total_tables': tables_saved,
                'total_rows': total_rows,
                'source_file': 'Power BI (.pbix)',
                'extraction_tool': 'extract_dax_pbi.py'
            }
        ])
        metadata.to_sql('_extraction_metadata', conn, index=False, if_exists='replace')
        
        conn.close()
        
        if not quiet:
            print(f"\nSQLite database created: {db_path}")
            print(f"Total tables: {tables_saved}, Total rows: {total_rows}")
            
    except Exception as e:
        print(f"Error creating SQLite database: {e}")


def extract_dax_from_pbix(pbix_path, output_dir, quiet=False, no_file=False, extract_data=False, data_limit=100, data_format='csv', extract_ui=True):
    # Initialize pbixray
    model = PBIXRay(pbix_path)
    
    # Extract additional metadata and structure information
    report_pages = []
    visualizations = []
    visual_queries = []
    relationships = []
    power_query_info = []
    ui_data = {}
    
    try:
        # Explore metadata
        if hasattr(model, 'metadata') and model.metadata is not None:
            metadata = model.metadata
            if hasattr(metadata, 'iterrows'):
                # Extract useful metadata
                for _, meta_row in metadata.iterrows():
                    meta_name = meta_row.get('Name', 'Unknown')
                    meta_value = meta_row.get('Value', '')
                    if 'version' in meta_name.lower() or 'author' in meta_name.lower():
                        if not quiet:
                            print(f"Metadata - {meta_name}: {meta_value}")
        
        # Extract UI layer if requested
        if extract_ui:
            if not quiet:
                print("\n" + "="*60)
                print("EXTRACTING UI LAYER (REPORT PAGES & VISUALIZATIONS)")
                print("="*60)
            
            ui_data = extract_ui_layer(pbix_path)
            
            if ui_data.get("error"):
                if not quiet:
                    print(f"UI extraction error: {ui_data['error']}")
            else:
                if not quiet:
                    print(f"📄 Report Pages: {len(ui_data.get('report_pages', []))}")
                    print(f"📊 Visualizations: {len(ui_data.get('visualizations', []))}")
                    print(f"🎨 Custom Visuals: {len(ui_data.get('custom_visuals', []))}")
                    
                    # Show page details
                    for i, page in enumerate(ui_data.get('report_pages', []), 1):
                        print(f"  {i}. {page['display_name']} ({page['width']}x{page['height']}) - {page['visual_count']} visuals")
                    
                    # Show visual type summary
                    print(f"\n📈 Visual Types:")
                    for vtype, count in sorted(ui_data.get('visual_summary', {}).items()):
                        print(f"  {vtype}: {count}")
                    
                    # Show sample visualizations
                    visuals = ui_data.get('visualizations', [])
                    if visuals:
                        print(f"\n📊 Sample Visualizations:")
                        for i, visual in enumerate(visuals[:5], 1):
                            pos = visual.get('position', {})
                            print(f"  {i}. {visual.get('enhanced_type', 'Unknown')} at ({pos.get('x', 0):.0f}, {pos.get('y', 0):.0f})")
                            if visual.get('text_content'):
                                print(f"     Text: '{visual['text_content']}'")
                            if visual.get('bookmark_action'):
                                print(f"     Action: Bookmark ({visual['bookmark_action']})")
        
        # Explore relationships
        if hasattr(model, 'relationships') and model.relationships is not None:
            rel_data = model.relationships
            
            if hasattr(rel_data, 'iterrows'):  # DataFrame
                for _, rel_row in rel_data.iterrows():
                    # Get actual column names from the DataFrame
                    columns = rel_data.columns.tolist()
                    rel_info = {
                        'from_table': rel_row.get(columns[0] if len(columns) > 0 else 'FromTable', 'Unknown'),
                        'from_column': rel_row.get(columns[1] if len(columns) > 1 else 'FromColumn', 'Unknown'), 
                        'to_table': rel_row.get(columns[2] if len(columns) > 2 else 'ToTable', 'Unknown'),
                        'to_column': rel_row.get(columns[3] if len(columns) > 3 else 'ToColumn', 'Unknown'),
                        'type': rel_row.get(columns[4] if len(columns) > 4 else 'Type', 'One-to-Many'),
                        'active': rel_row.get(columns[5] if len(columns) > 5 else 'IsActive', True)
                    }
                    relationships.append(rel_info)
        
        # Explore Power Query information
        if hasattr(model, 'power_query') and model.power_query is not None:
            pq_data = model.power_query
            
            if hasattr(pq_data, 'iterrows'):  # DataFrame
                for _, pq_row in pq_data.iterrows():
                    # Get actual column names from the DataFrame
                    columns = pq_data.columns.tolist()
                    pq_info = {
                        'name': pq_row.get(columns[0] if len(columns) > 0 else 'Name', 'Unknown'),
                        'type': pq_row.get(columns[1] if len(columns) > 1 else 'Type', 'Query'),
                        'expression': pq_row.get(columns[2] if len(columns) > 2 else 'Expression', '')
                    }
                    power_query_info.append(pq_info)
        
        # Note about report pages and visualizations extraction
        if not report_pages and not visualizations and not quiet:
            print("\n" + "="*60)
            print("REPORT PAGES & VISUALIZATIONS EXTRACTION")
            print("="*60)
            print("The current version of pbixray doesn't expose report pages/visualizations")
            print("directly. To extract the complete UI structure, you would need:")
            print("")
            print("1. Advanced PBIX parsing tools like:")
            print("   - pbi-tools (requires .NET)")
            print("   - Power BI REST API")
            print("   - Custom JSON parsing of PBIX layout files")
            print("")
            print("2. The PBIX file contains these UI elements internally:")
            print("   - Report pages (tabs) with names, order, dimensions")  
            print("   - Visual objects (charts, tables, cards, etc.)")
            print("   - Visual properties (position, size, formatting)")
            print("   - DAX queries generated for each visual")
            print("   - Filter context and interactions")
            print("")
            print("3. What we CAN extract with current tools:")
            print("   ✅ Data model (tables, columns, relationships)")
            print("   ✅ DAX measures and calculated columns")
            print("   ✅ Power Query (M) code")
            print("   ✅ Table data")
            print("   ❌ Report pages/tabs")
            print("   ❌ Visual definitions and layout")
            print("   ❌ Visual-specific DAX queries")
            print("="*60)
        
        # Try to explore the raw PBIX structure for report layout
        # Note: This would require deeper integration with pbixray internals
        try:
            # Check if we have access to internal file structure
            if hasattr(model, '_pbix_file'):
                if not quiet:
                    print("PBIX file access available - could potentially extract layout")
        except:
            pass
            
    except Exception as e:
        if not quiet:
            print(f"Warning: Error exploring additional metadata: {e}")
    
    # Extract measures (DAX expressions)
    measures_df = model.dax_measures
    measures = []
    if not measures_df.empty:
        for _, row in measures_df.iterrows():
            measures.append({
                'table': row['TableName'],
                'name': row['Name'],
                'dax': row['Expression'].strip()
            })
    
    # Extract calculated columns (DAX expressions)
    columns_df = model.dax_columns
    calc_columns = []
    if not columns_df.empty:
        for _, row in columns_df.iterrows():
            calc_columns.append({
                'table': row['TableName'],
                'name': row['ColumnName'],
                'dax': row['Expression'].strip()
            })
    
    # Extract calculated tables (DAX expressions)
    tables_df = model.dax_tables
    calc_tables = []
    if not tables_df.empty:
        for _, row in tables_df.iterrows():
            calc_tables.append({
                'table': row['TableName'],
                'dax': row['Expression'].strip()
            })
    
    # Extract all tables and their columns
    all_tables = []
    try:
        # Try to get table information from the model's tables attribute
        if hasattr(model, 'tables') and model.tables is not None:
            tables_data = model.tables
            
            # Handle if tables is a numpy array or pandas DataFrame
            if hasattr(tables_data, 'shape'):  # numpy array
                for i, table_item in enumerate(tables_data):
                    if isinstance(table_item, dict):
                        table_name = table_item.get('Name', f'Table_{i}')
                    else:
                        table_name = str(table_item)
                    
                    all_tables.append({
                        'name': table_name,
                        'columns': [],
                        'type': 'Data Table'
                    })
            elif hasattr(tables_data, 'iterrows'):  # pandas DataFrame
                for _, table_row in tables_data.iterrows():
                    table_name = table_row.get('Name', table_row.get('TableName', 'Unknown'))
                    all_tables.append({
                        'name': table_name,
                        'columns': [],
                        'type': 'Data Table'
                    })
        
        # Try to get schema information
        if hasattr(model, 'schema') and model.schema is not None:
            schema_data = model.schema
            
            # Try to extract column information from schema
            if hasattr(schema_data, 'get'):
                tables_schema = schema_data.get('tables', {})
                for table_name, table_info in tables_schema.items():
                    columns_info = table_info.get('columns', [])
                    
                    # Find existing table or create new one
                    existing_table = next((t for t in all_tables if t['name'] == table_name), None)
                    if existing_table:
                        for col_info in columns_info:
                            existing_table['columns'].append({
                                'name': col_info.get('name', 'Unknown'),
                                'type': col_info.get('dataType', 'Unknown')
                            })
                    else:
                        columns = []
                        for col_info in columns_info:
                            columns.append({
                                'name': col_info.get('name', 'Unknown'),
                                'type': col_info.get('dataType', 'Unknown')
                            })
                        all_tables.append({
                            'name': table_name,
                            'columns': columns,
                            'type': 'Schema Table'
                        })
        
        # Try to use get_table method for each identified table
        if hasattr(model, 'get_table') and all_tables:
            for table in all_tables:
                try:
                    table_detail = model.get_table(table['name'])
                    if table_detail is not None and hasattr(table_detail, 'columns'):
                        # table_detail is a DataFrame - get column names and try to infer types
                        for col_name in table_detail.columns:
                            # Try to infer data type from the first few non-null values
                            col_data = table_detail[col_name].dropna()
                            if len(col_data) > 0:
                                first_val = col_data.iloc[0]
                                if isinstance(first_val, (int, float)):
                                    col_type = 'Number'
                                elif isinstance(first_val, str):
                                    col_type = 'Text'
                                elif hasattr(first_val, 'date'):
                                    col_type = 'Date'
                                else:
                                    col_type = str(type(first_val).__name__)
                            else:
                                col_type = 'Unknown'
                                
                            table['columns'].append({
                                'name': col_name,
                                'type': col_type
                            })
                            
                        # Extract actual data if requested
                        if extract_data and len(table_detail) > 0:
                            table['data'] = table_detail.head(data_limit).copy()
                            table['total_rows'] = len(table_detail)
                except Exception as e:
                    print(f"Could not get details for table {table['name']}: {e}")
        
        # If we still don't have detailed tables, extract from DAX references
        if not all_tables:
            # Get unique table names from measures, calculated columns, etc.
            table_names = set()
            
            # Add tables from measures
            for m in measures:
                table_names.add(m['table'])
            
            # Add tables from calculated columns  
            for c in calc_columns:
                table_names.add(c['table'])
                
            # Add calculated tables
            for t in calc_tables:
                table_names.add(t['table'])
            
            for table_name in table_names:
                all_tables.append({
                    'name': table_name,
                    'columns': [],
                    'type': 'DAX Referenced'
                })
                
    except Exception as e:
        print(f"Warning: Could not extract detailed table information: {e}")
        # Fallback: extract table names from DAX expressions
        table_names = set()
        
        # Add tables from measures
        for m in measures:
            table_names.add(m['table'])
        
        # Add tables from calculated columns
        for c in calc_columns:
            table_names.add(c['table'])
            
        # Add calculated tables
        for t in calc_tables:
            table_names.add(t['table'])
        
        for table_name in table_names:
            all_tables.append({
                'name': table_name,
                'columns': [],
                'type': 'Fallback Detection'
            })
    
    # Print results
    if not quiet:
        # Show relationships if found
        if relationships:
            print("Data Model Relationships:")
            for rel in relationships:
                status = "Active" if rel['active'] else "Inactive"
                print(f"  {rel['from_table']}[{rel['from_column']}] → {rel['to_table']}[{rel['to_column']}] ({rel['type']}) [{status}]")
            print("---")
        
        # Show Power Query information if found
        if power_query_info:
            print("Power Query Sources:")
            for pq in power_query_info:
                print(f"  {pq['name']} ({pq['type']})")
                if pq['expression'] and len(pq['expression']) < 200:
                    print(f"    Expression: {pq['expression']}")
                elif pq['expression']:
                    print(f"    Expression: {pq['expression'][:200]}...")
            print("---")
        
        # Show report structure (if we manage to extract it)
        if report_pages:
            print("Report Pages (Tabs):")
            for page in report_pages:
                print(f"Page: {page['name']} (ID: {page['id']})")
                print(f"  Order: {page['order']}")
                
                # Show visuals on this page
                page_visuals = [v for v in visualizations if v['page'] == page['name'] or v['page'] == page['id']]
                if page_visuals:
                    print(f"  Visualizations ({len(page_visuals)}):")
                    for visual in page_visuals:
                        print(f"    - {visual['name']} ({visual['type']})")
                        if visual.get('tables_used'):
                            print(f"      Tables: {', '.join(visual['tables_used'])}")
                        if visual.get('measures_used'):
                            print(f"      Measures: {', '.join(visual['measures_used'])}")
                else:
                    print("  No visualizations found")
                print("---")
        
        # Show visual queries (if found)
        if visual_queries:
            print("Visual DAX Queries:")
            for query in visual_queries:
                print(f"Visual ID: {query['visual_id']} (Page: {query['page']})")
                print(f"Query Type: {query['type']}")
                if query['query']:
                    display_query = query['query'][:500] + "..." if len(query['query']) > 500 else query['query']
                    print(f"Query: {display_query}")
                print("---")
        
        print("Tables and Columns:")
        for table in all_tables:
            print(f"Table: {table['name']} ({table.get('type', 'Unknown')})")
            if table['columns']:
                for col in table['columns']:
                    print(f"  - {col['name']} ({col['type']})")
            else:
                print("  - (No column information available)")
            
            # Show data info if extracted
            if 'data' in table:
                print(f"  Data: {len(table['data'])} rows extracted (Total: {table.get('total_rows', 'Unknown')} rows)")
            
            print("---")
        
        print("\nMeasures:")
        for m in measures:
            print(f"Table: {m['table']}\nName: {m['name']}\nDAX: {m['dax']}\n---")
        
        print("\nCalculated Columns:")
        for c in calc_columns:
            print(f"Table: {c['table']}\nName: {c['name']}\nDAX: {c['dax']}\n---")
        
        print("\nCalculated Tables:")
        for t in calc_tables:
            print(f"Table: {t['table']}\nDAX: {t['dax']}\n---")
    
    # Save data files if requested
    if extract_data and not no_file:
        save_table_data(all_tables, output_dir, data_format, quiet)
    
    # Optionally save to file
    if not no_file:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, 'dax_expressions.txt'), 'w', encoding='utf-8') as f:
            # Write report structure
            if report_pages:
                f.write("Report Pages (Tabs):\n")
                for page in report_pages:
                    f.write(f"Page: {page['name']} (ID: {page['id']})\n")
                    f.write(f"  Order: {page['order']}, Size: {page['width']}x{page['height']}\n")
                    
                    # Write visuals on this page
                    page_visuals = [v for v in visualizations if v['page'] == page['name'] or v['page'] == page['id']]
                    if page_visuals:
                        f.write(f"  Visualizations ({len(page_visuals)}):\n")
                        for visual in page_visuals:
                            f.write(f"    - {visual['name']} ({visual['type']})\n")
                            f.write(f"      Position: ({visual['x']}, {visual['y']}) Size: {visual['width']}x{visual['height']}\n")
                            if visual['tables_used']:
                                f.write(f"      Tables: {', '.join(visual['tables_used'])}\n")
                            if visual['measures_used']:
                                f.write(f"      Measures: {', '.join(visual['measures_used'])}\n")
                    else:
                        f.write("  No visualizations found\n")
                    f.write("---\n")
            
            # Write visual queries
            if visual_queries:
                f.write("\nVisual DAX Queries:\n")
                for query in visual_queries:
                    f.write(f"Visual ID: {query['visual_id']} (Page: {query['page']})\n")
                    f.write(f"Query Type: {query['type']}\n")
                    if query['query']:
                        f.write(f"Query: {query['query']}\n")
                    f.write("---\n")
            
            f.write("\nTables and Columns:\n")
            for table in all_tables:
                f.write(f"Table: {table['name']} ({table.get('type', 'Unknown')})\n")
                if table['columns']:
                    for col in table['columns']:
                        f.write(f"  - {col['name']} ({col['type']})\n")
                else:
                    f.write("  - (No column information available)\n")
                
                # Include data info if extracted
                if 'data' in table:
                    f.write(f"  Data: {len(table['data'])} rows extracted (Total: {table.get('total_rows', 'Unknown')} rows)\n")
                
                f.write("---\n")
            
            f.write("\nMeasures:\n")
            for m in measures:
                f.write(f"Table: {m['table']}\nName: {m['name']}\nDAX: {m['dax']}\n---\n")
            f.write("\nCalculated Columns:\n")
            for c in calc_columns:
                f.write(f"Table: {c['table']}\nName: {c['name']}\nDAX: {c['dax']}\n---\n")
            f.write("\nCalculated Tables:\n")
            for t in calc_tables:
                f.write(f"Table: {t['table']}\nDAX: {t['dax']}\n---\n")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Extract DAX expressions from Power BI (.pbix) files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s report.pbix
  %(prog)s report.pbix -o output_folder
  %(prog)s report.pbix --output-dir ./dax_output --quiet
  %(prog)s report.pbix --extract-data --data-limit 50 --data-format json
  %(prog)s report.pbix --extract-data --data-format sqlite
        '''
    )
    
    parser.add_argument(
        'pbix_file',
        help='Path to the .pbix file to extract DAX from'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='extracted_pbix_dax',
        help='Directory to save the extracted DAX expressions (default: extracted_pbix_dax)'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress console output, only save to file'
    )
    
    parser.add_argument(
        '--no-file',
        action='store_true',
        help='Do not save to file, only print to console'
    )
    
    parser.add_argument(
        '--extract-data',
        action='store_true',
        help='Extract actual table data in addition to schema and DAX'
    )
    
    parser.add_argument(
        '--data-limit',
        type=int,
        default=100,
        help='Maximum number of rows to extract per table (default: 100)'
    )
    
    parser.add_argument(
        '--data-format',
        choices=['csv', 'json', 'excel', 'sqlite'],
        default='csv',
        help='Format for extracted data files (default: csv)'
    )
    
    parser.add_argument(
        '--no-ui',
        action='store_true',
        help='Skip UI layer extraction (pages, visualizations, bookmarks)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.pbix_file):
        print(f"Error: File '{args.pbix_file}' not found.", file=sys.stderr)
        sys.exit(1)
    
    if not args.pbix_file.lower().endswith('.pbix'):
        print(f"Warning: '{args.pbix_file}' does not have a .pbix extension.", file=sys.stderr)
    
    # Extract DAX expressions
    try:
        extract_dax_from_pbix(args.pbix_file, args.output_dir, args.quiet, args.no_file, 
                             args.extract_data, args.data_limit, args.data_format, not args.no_ui)
        if not args.quiet:
            if not args.no_file:
                print(f"\nDAX expressions saved to: {os.path.join(args.output_dir, 'dax_expressions.txt')}")
                if args.extract_data:
                    print(f"Data files saved to: {args.output_dir}")
            print("Extraction completed successfully!")
    except Exception as e:
        print(f"Error extracting DAX from '{args.pbix_file}': {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()