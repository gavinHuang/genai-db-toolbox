#!/usr/bin/env python3
"""
Power BI to SQLite MCP Server Database Setup
Creates additional tables in the SQLite database to store UI structure, 
DAX expressions, and Power Query metadata for complete MCP server access.
"""

import sqlite3
import json
import os
from pathlib import Path


def setup_powerbi_mcp_database(sqlite_db_path, ui_structure_file, data_model_file):
    """Setup complete Power BI MCP database with UI and metadata tables."""
    
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()
    
    try:
        # Create UI structure tables
        create_ui_tables(cursor, ui_structure_file)
        
        # Create DAX and metadata tables
        create_metadata_tables(cursor, data_model_file)
        
        # Create convenient views
        create_powerbi_views(cursor)
        
        conn.commit()
        print(f"✅ Power BI MCP database setup complete: {sqlite_db_path}")
        
        # Show summary
        show_database_summary(cursor)
        
    except Exception as e:
        print(f"❌ Error setting up MCP database: {e}")
        conn.rollback()
    finally:
        conn.close()


def create_ui_tables(cursor, ui_structure_file):
    """Create tables for UI structure data."""
    
    # Load UI structure
    with open(ui_structure_file, 'r', encoding='utf-8') as f:
        ui_data = json.load(f)
    
    # Create report pages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS powerbi_pages (
            page_id TEXT PRIMARY KEY,
            page_name TEXT,
            display_name TEXT,
            ordinal INTEGER,
            width INTEGER,
            height INTEGER,
            visual_count INTEGER,
            background_config TEXT,
            filters_config TEXT
        )
    """)
    
    # Insert page data
    for page in ui_data.get('pages', []):
        raw_data = page.get('raw_data', {})
        cursor.execute("""
            INSERT OR REPLACE INTO powerbi_pages 
            (page_id, page_name, display_name, ordinal, width, height, visual_count, background_config, filters_config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            page['name'],
            page['name'],
            raw_data.get('displayName', page['name']),
            page['ordinal'],
            page['width'],
            page['height'],
            page['visual_count'],
            json.dumps(page.get('background', {})),
            raw_data.get('filters', '[]')
        ))
    
    # Create visualizations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS powerbi_visualizations (
            visual_id TEXT,
            page_id TEXT,
            visual_type TEXT,
            enhanced_type TEXT,
            x_position REAL,
            y_position REAL,
            width REAL,
            height REAL,
            z_order INTEGER,
            text_content TEXT,
            data_roles_count INTEGER,
            bookmark_action TEXT,
            config_json TEXT,
            PRIMARY KEY (visual_id, page_id)
        )
    """)
    
    # Insert visualization data
    for visual in ui_data.get('visualizations', []):
        # Find which page this visual belongs to (from path or config)
        page_id = extract_page_from_visual(visual, ui_data.get('pages', []))
        
        cursor.execute("""
            INSERT OR REPLACE INTO powerbi_visualizations 
            (visual_id, page_id, visual_type, enhanced_type, x_position, y_position, 
             width, height, z_order, text_content, data_roles_count, bookmark_action, config_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(visual.get('id', '')),
            page_id,
            visual.get('type', 'unknown'),
            visual.get('enhanced_type', 'Unknown'),
            visual.get('position', {}).get('x', 0),
            visual.get('position', {}).get('y', 0),
            visual.get('position', {}).get('width', 0),
            visual.get('position', {}).get('height', 0),
            visual.get('position', {}).get('z_order', 0),
            visual.get('text_content'),
            visual.get('data_roles_count', 0),
            visual.get('bookmark_action'),
            json.dumps(visual.get('raw_config', {}))
        ))
    
    # Create custom visuals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS powerbi_custom_visuals (
            file_path TEXT PRIMARY KEY,
            visual_name TEXT,
            visual_version TEXT,
            config_json TEXT
        )
    """)
    
    # Insert custom visual data
    for custom_visual in ui_data.get('custom_visuals', []):
        config = custom_visual.get('config', {})
        cursor.execute("""
            INSERT OR REPLACE INTO powerbi_custom_visuals 
            (file_path, visual_name, visual_version, config_json)
            VALUES (?, ?, ?, ?)
        """, (
            custom_visual.get('file', ''),
            config.get('name', 'Unknown'),
            config.get('version', 'Unknown'),
            json.dumps(config)
        ))


def extract_page_from_visual(visual, pages):
    """Extract which page a visual belongs to."""
    # Try to match by visual containers in page raw data
    visual_id = str(visual.get('id', ''))
    
    for page in pages:
        raw_data = page.get('raw_data', {})
        visual_containers = raw_data.get('visualContainers', [])
        
        for container in visual_containers:
            if str(container.get('id', '')) == visual_id:
                return page['name']
    
    # Fallback: extract from path or return first page
    path = visual.get('path', '')
    if 'sections[0]' in path:
        return pages[0]['name'] if pages else 'Unknown'
    elif 'sections[1]' in path and len(pages) > 1:
        return pages[1]['name']
    elif 'sections[2]' in path and len(pages) > 2:
        return pages[2]['name']
    elif 'sections[3]' in path and len(pages) > 3:
        return pages[3]['name']
    
    return pages[0]['name'] if pages else 'Unknown'


def create_metadata_tables(cursor, data_model_file):
    """Create tables for DAX expressions and metadata."""
    
    # Load data model
    with open(data_model_file, 'r', encoding='utf-8') as f:
        data_model = json.load(f)
    
    # Create DAX measures table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS powerbi_dax_measures (
            measure_id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT,
            measure_name TEXT,
            dax_expression TEXT,
            description TEXT
        )
    """)
    
    # Insert DAX measures
    for measure in data_model.get('measures', []):
        cursor.execute("""
            INSERT OR REPLACE INTO powerbi_dax_measures 
            (table_name, measure_name, dax_expression, description)
            VALUES (?, ?, ?, ?)
        """, (
            measure.get('table', ''),
            measure.get('name', ''),
            measure.get('expression', ''),
            measure.get('description', '')
        ))
    
    # Create calculated columns table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS powerbi_calculated_columns (
            column_id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT,
            column_name TEXT,
            dax_expression TEXT,
            data_type TEXT
        )
    """)
    
    # Insert calculated columns
    for column in data_model.get('calculated_columns', []):
        cursor.execute("""
            INSERT OR REPLACE INTO powerbi_calculated_columns 
            (table_name, column_name, dax_expression, data_type)
            VALUES (?, ?, ?, ?)
        """, (
            column.get('table', ''),
            column.get('name', ''),
            column.get('expression', ''),
            column.get('data_type', '')
        ))
    
    # Create relationships table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS powerbi_relationships (
            relationship_id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_table TEXT,
            from_column TEXT,
            to_table TEXT,
            to_column TEXT,
            cardinality TEXT,
            is_active BOOLEAN
        )
    """)
    
    # Insert relationships
    for relationship in data_model.get('relationships', []):
        cursor.execute("""
            INSERT OR REPLACE INTO powerbi_relationships 
            (from_table, from_column, to_table, to_column, cardinality, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            relationship.get('from_table', ''),
            relationship.get('from_column', ''),
            relationship.get('to_table', ''),
            relationship.get('to_column', ''),
            relationship.get('cardinality', ''),
            relationship.get('is_active', True)
        ))
    
    # Create Power Query table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS powerbi_power_query (
            query_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT,
            m_expression TEXT,
            source_type TEXT
        )
    """)
    
    # Insert Power Query sources
    power_query = data_model.get('power_query', {})
    if isinstance(power_query, dict):
        for source_name, query_data in power_query.items():
            if isinstance(query_data, dict):
                m_expression = query_data.get('Expression', str(query_data))
                source_type = extract_source_type(m_expression)
            else:
                m_expression = str(query_data)
                source_type = extract_source_type(m_expression)
            
            cursor.execute("""
                INSERT OR REPLACE INTO powerbi_power_query 
                (source_name, m_expression, source_type)
                VALUES (?, ?, ?)
            """, (source_name, m_expression, source_type))
    elif isinstance(power_query, str):
        # Handle case where power_query is a string (error message)
        cursor.execute("""
            INSERT OR REPLACE INTO powerbi_power_query 
            (source_name, m_expression, source_type)
            VALUES (?, ?, ?)
        """, ('power_query_error', power_query, 'Error'))


def extract_source_type(m_expression):
    """Extract source type from M expression."""
    if 'Excel.Workbook' in m_expression:
        return 'Excel'
    elif 'AzureStorage.BlobContents' in m_expression:
        return 'Azure Blob Storage'
    elif 'Table.FromRows' in m_expression:
        return 'Embedded Table'
    elif 'Sql.Database' in m_expression:
        return 'SQL Database'
    elif 'Web.Contents' in m_expression:
        return 'Web Source'
    else:
        return 'Other'


def create_powerbi_views(cursor):
    """Create convenient views for Power BI analysis."""
    
    # View: Page summary with visual counts by type
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS powerbi_page_summary AS
        SELECT 
            p.page_name,
            p.display_name,
            p.visual_count,
            COUNT(v.visual_id) as actual_visual_count,
            GROUP_CONCAT(DISTINCT v.enhanced_type) as visual_types
        FROM powerbi_pages p
        LEFT JOIN powerbi_visualizations v ON p.page_id = v.page_id
        GROUP BY p.page_id, p.page_name, p.display_name, p.visual_count
    """)
    
    # View: Visual types summary
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS powerbi_visual_types_summary AS
        SELECT 
            enhanced_type,
            COUNT(*) as count,
            AVG(width * height) as avg_size,
            COUNT(CASE WHEN bookmark_action IS NOT NULL THEN 1 END) as with_bookmarks,
            COUNT(CASE WHEN text_content IS NOT NULL THEN 1 END) as with_text
        FROM powerbi_visualizations
        GROUP BY enhanced_type
        ORDER BY count DESC
    """)
    
    # View: Complete data model overview
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS powerbi_data_model_overview AS
        SELECT 
            'Tables' as component_type,
            COUNT(DISTINCT name) as count,
            NULL as details
        FROM sqlite_master 
        WHERE type = 'table' AND name NOT LIKE 'powerbi_%' AND name NOT LIKE '_extraction_%' AND name NOT LIKE 'sqlite_%'
        UNION ALL
        SELECT 
            'DAX Measures' as component_type,
            COUNT(*) as count,
            GROUP_CONCAT(DISTINCT table_name) as details
        FROM powerbi_dax_measures
        UNION ALL
        SELECT 
            'Calculated Columns' as component_type,
            COUNT(*) as count,
            GROUP_CONCAT(DISTINCT table_name) as details
        FROM powerbi_calculated_columns
        UNION ALL
        SELECT 
            'Relationships' as component_type,
            COUNT(*) as count,
            COUNT(CASE WHEN is_active THEN 1 END) || ' active' as details
        FROM powerbi_relationships
        UNION ALL
        SELECT 
            'Power Query Sources' as component_type,
            COUNT(*) as count,
            GROUP_CONCAT(DISTINCT source_type) as details
        FROM powerbi_power_query
    """)


def show_database_summary(cursor):
    """Show summary of the MCP database setup."""
    print("\n📊 POWER BI MCP DATABASE SUMMARY")
    print("=" * 50)
    
    # Count tables
    cursor.execute("""
        SELECT 
            CASE 
                WHEN name LIKE 'powerbi_%' THEN 'UI/Metadata'
                WHEN name LIKE '_extraction_%' THEN 'System'
                WHEN name NOT LIKE 'sqlite_%' THEN 'Data'
                ELSE 'System'
            END as table_category,
            COUNT(*) as table_count
        FROM sqlite_master 
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        GROUP BY table_category
    """)
    
    for category, count in cursor.fetchall():
        print(f"{category} Tables: {count}")
    
    # Show data model overview
    cursor.execute("SELECT * FROM powerbi_data_model_overview")
    print("\n📈 Data Model Components:")
    for component, count, details in cursor.fetchall():
        detail_str = f" ({details})" if details else ""
        print(f"  {component}: {count}{detail_str}")
    
    # Show page summary
    cursor.execute("SELECT * FROM powerbi_page_summary")
    print("\n📄 Report Pages:")
    for page_name, display_name, visual_count, actual_count, visual_types in cursor.fetchall():
        print(f"  {display_name}: {actual_count} visuals ({visual_types})")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Power BI MCP Server Database")
    parser.add_argument("sqlite_db", help="Path to SQLite database")
    parser.add_argument("ui_structure", help="Path to ui_structure.json")
    parser.add_argument("data_model", help="Path to data_model.json")
    
    args = parser.parse_args()
    
    # Validate files exist
    for file_path in [args.sqlite_db, args.ui_structure, args.data_model]:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return
    
    setup_powerbi_mcp_database(args.sqlite_db, args.ui_structure, args.data_model)


if __name__ == "__main__":
    main()