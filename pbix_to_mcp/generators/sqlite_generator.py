"""
SQLite Database Generator

Creates SQLite databases from extracted Power BI data and metadata.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


class SQLiteGenerator:
    """
    Generates SQLite databases from extracted Power BI data.

    This class creates:
    - Data tables from Power BI tables
    - Metadata tables for DAX expressions
    - UI structure tables
    - Helper views for common queries
    """

    def __init__(self, output_dir: Path):
        """
        Initialize the SQLite generator.

        Args:
            output_dir: Directory where database will be created
        """
        self.output_dir = Path(output_dir)
        self.data_dir = self.output_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(f"{__name__}")

    def create_database(self, extraction_results: Dict[str, Any]) -> Path:
        """
        Create complete SQLite database from extraction results.

        Args:
            extraction_results: Complete extraction results dictionary

        Returns:
            Path to created database file
        """
        db_path = self.data_dir / "powerbi_data.db"

        self.logger.info(f"Creating SQLite database: {db_path}")

        try:
            # Remove existing database
            if db_path.exists():
                db_path.unlink()

            # Create connection
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            try:
                # Create data tables
                if "data_model" in extraction_results:
                    self._create_data_tables(cursor, extraction_results["data_model"])

                    # Create comprehensive metadata tables for data model
                    self._create_comprehensive_metadata_tables(
                        cursor, extraction_results["data_model"]
                    )

                # Create DAX metadata tables
                if "dax_expressions" in extraction_results:
                    self._create_dax_tables(cursor, extraction_results["dax_expressions"])

                # Create UI structure tables
                if "ui_structure" in extraction_results:
                    self._create_ui_tables(cursor, extraction_results["ui_structure"])

                # Create metadata table
                self._create_metadata_table(cursor, extraction_results)

                # Create helpful views
                self._create_views(cursor)

                conn.commit()
                self.logger.info(f"SQLite database created successfully: {db_path}")

            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

            return db_path

        except Exception as e:
            self.logger.error(f"Failed to create SQLite database: {e}")
            raise

    def _create_data_tables(self, cursor: sqlite3.Cursor, data_model: Dict[str, Any]) -> None:
        """Create data tables from Power BI tables."""
        tables = data_model.get("tables", [])

        self.logger.info(f"Creating data tables from {len(tables)} table definitions")

        for table in tables:
            if not table.get("data_extracted") or table.get("data") is None:
                self.logger.warning(
                    f"Skipping table {table.get('name', 'Unknown')} - no data extracted"
                )
                continue

            table_name = table["name"]
            table_df = table["data"]

            # Sanitize table name for SQLite
            safe_table_name = self._sanitize_table_name(table_name)

            try:
                # Save DataFrame to SQLite
                table_df.to_sql(
                    safe_table_name, cursor.connection, index=False, if_exists="replace"
                )

                self.logger.info(
                    f"Created data table: {safe_table_name} ({len(table_df)} rows, {len(table_df.columns)} columns)"
                )

            except Exception as e:
                self.logger.error(f"Failed to create table {table_name}: {e}")
                import traceback

                self.logger.error(f"Traceback: {traceback.format_exc()}")

    def _create_comprehensive_metadata_tables(
        self, cursor: sqlite3.Cursor, data_model: Dict[str, Any]
    ) -> None:
        """Create comprehensive metadata tables from the enhanced data model."""

        # Create enhanced table metadata table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_table_metadata (
                table_name TEXT PRIMARY KEY,
                table_type TEXT,
                row_count INTEGER,
                column_count INTEGER,
                memory_size INTEGER,
                has_duplicates BOOLEAN,
                is_hidden BOOLEAN,
                description TEXT,
                data_category TEXT,
                data_extracted BOOLEAN
            )
        """
        )

        # Insert table metadata
        for table in data_model.get("tables", []):
            cursor.execute(
                """
                INSERT OR REPLACE INTO powerbi_table_metadata
                (table_name, table_type, row_count, column_count, memory_size, 
                 has_duplicates, is_hidden, description, data_category, data_extracted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    table.get("name", ""),
                    table.get("table_type", "Regular"),
                    table.get("row_count", 0),
                    table.get("column_count", 0),
                    table.get("memory_size", 0),
                    table.get("has_duplicates", False),
                    table.get("is_hidden", False),
                    table.get("description", ""),
                    table.get("data_category", ""),
                    table.get("data_extracted", False),
                ),
            )

        # Create enhanced column metadata table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_column_metadata (
                column_id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT,
                column_name TEXT,
                data_type TEXT,
                nullable BOOLEAN,
                unique_values INTEGER,
                null_count INTEGER,
                null_percentage REAL,
                is_key BOOLEAN,
                data_category TEXT,
                format_string TEXT,
                is_hidden BOOLEAN,
                sort_by_column TEXT,
                description TEXT,
                min_value REAL,
                max_value REAL,
                mean_value REAL,
                std_deviation REAL,
                min_length INTEGER,
                max_length INTEGER,
                avg_length REAL
            )
        """
        )

        # Insert column metadata
        for table in data_model.get("tables", []):
            table_name = table.get("name", "")
            for column in table.get("columns", []):
                cursor.execute(
                    """
                    INSERT INTO powerbi_column_metadata
                    (table_name, column_name, data_type, nullable, unique_values, null_count,
                     null_percentage, is_key, data_category, format_string, is_hidden, 
                     sort_by_column, description, min_value, max_value, mean_value, 
                     std_deviation, min_length, max_length, avg_length)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        table_name,
                        column.get("name", ""),
                        column.get("type", ""),
                        column.get("nullable", False),
                        column.get("unique_values", 0),
                        column.get("null_count", 0),
                        column.get("null_percentage", 0.0),
                        column.get("is_key", False),
                        column.get("data_category", ""),
                        column.get("format_string", ""),
                        column.get("is_hidden", False),
                        column.get("sort_by_column", ""),
                        column.get("description", ""),
                        column.get("min_value"),
                        column.get("max_value"),
                        column.get("mean_value"),
                        column.get("std_deviation"),
                        column.get("min_length"),
                        column.get("max_length"),
                        column.get("avg_length"),
                    ),
                )

        # Create comprehensive DAX measures table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_dax_measures (
                measure_id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT,
                measure_name TEXT,
                dax_expression TEXT,
                description TEXT,
                format_string TEXT,
                is_hidden BOOLEAN,
                display_folder TEXT,
                data_type TEXT,
                expression_length INTEGER,
                function_count INTEGER,
                complexity_score REAL,
                contains_time_intelligence BOOLEAN,
                contains_filter_functions BOOLEAN,
                referenced_tables TEXT,
                referenced_columns TEXT
            )
        """
        )

        # Insert DAX measures from the enhanced structure
        for measure in data_model.get("measures", []):
            cursor.execute(
                """
                INSERT INTO powerbi_dax_measures 
                (table_name, measure_name, dax_expression, description, format_string, 
                 is_hidden, display_folder, data_type, expression_length, function_count,
                 complexity_score, contains_time_intelligence, contains_filter_functions,
                 referenced_tables, referenced_columns)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    measure.get("table", ""),
                    measure.get("name", ""),
                    measure.get("expression", ""),
                    measure.get("description", ""),
                    measure.get("format_string", ""),
                    measure.get("is_hidden", False),
                    measure.get("display_folder", ""),
                    measure.get("data_type", ""),
                    measure.get("expression_length", 0),
                    measure.get("function_count", 0),
                    measure.get("complexity_score", 0.0),
                    measure.get("contains_time_intelligence", False),
                    measure.get("contains_filter_functions", False),
                    json.dumps(measure.get("referenced_tables", [])),
                    json.dumps(measure.get("referenced_columns", [])),
                ),
            )

        # Create calculated columns table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_calculated_columns (
                column_id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT,
                column_name TEXT,
                dax_expression TEXT,
                data_type TEXT,
                format_string TEXT,
                is_hidden BOOLEAN,
                description TEXT,
                display_folder TEXT,
                expression_length INTEGER,
                function_count INTEGER,
                complexity_score REAL,
                referenced_tables TEXT,
                referenced_columns TEXT
            )
        """
        )

        # Insert calculated columns
        for column in data_model.get("calculated_columns", []):
            cursor.execute(
                """
                INSERT INTO powerbi_calculated_columns 
                (table_name, column_name, dax_expression, data_type, format_string,
                 is_hidden, description, display_folder, expression_length, function_count,
                 complexity_score, referenced_tables, referenced_columns)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    column.get("table", ""),
                    column.get("name", ""),
                    column.get("expression", ""),
                    column.get("data_type", ""),
                    column.get("format_string", ""),
                    column.get("is_hidden", False),
                    column.get("description", ""),
                    column.get("display_folder", ""),
                    column.get("expression_length", 0),
                    column.get("function_count", 0),
                    column.get("complexity_score", 0.0),
                    json.dumps(column.get("referenced_tables", [])),
                    json.dumps(column.get("referenced_columns", [])),
                ),
            )

        # Create relationships table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_relationships (
                relationship_id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_table TEXT,
                from_column TEXT,
                to_table TEXT,
                to_column TEXT,
                cardinality TEXT,
                is_active BOOLEAN,
                cross_filter_direction TEXT,
                security_filtering_behavior TEXT
            )
        """
        )

        # Insert relationships
        for relationship in data_model.get("relationships", []):
            cursor.execute(
                """
                INSERT INTO powerbi_relationships 
                (from_table, from_column, to_table, to_column, cardinality, is_active,
                 cross_filter_direction, security_filtering_behavior)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    relationship.get("from_table", ""),
                    relationship.get("from_column", ""),
                    relationship.get("to_table", ""),
                    relationship.get("to_column", ""),
                    relationship.get("cardinality", ""),
                    relationship.get("is_active", True),
                    relationship.get("cross_filter_direction", "Single"),
                    relationship.get("security_filtering_behavior", ""),
                ),
            )

        # Create Power Query table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_power_query (
                query_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT,
                query_type TEXT,
                m_expression TEXT,
                source_type TEXT
            )
        """
        )

        # Insert Power Query sources
        power_query = data_model.get("power_query", {})
        for source_name, query_data in power_query.items():
            if isinstance(query_data, dict):
                cursor.execute(
                    """
                    INSERT INTO powerbi_power_query 
                    (source_name, query_type, m_expression, source_type)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        source_name,
                        query_data.get("type", "Query"),
                        query_data.get("expression", ""),
                        query_data.get("source_type", "Other"),
                    ),
                )

        # Create hierarchies table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_hierarchies (
                hierarchy_id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT,
                hierarchy_name TEXT,
                levels TEXT,
                is_hidden BOOLEAN,
                description TEXT
            )
        """
        )

        # Insert hierarchies
        for hierarchy in data_model.get("hierarchies", []):
            cursor.execute(
                """
                INSERT INTO powerbi_hierarchies
                (table_name, hierarchy_name, levels, is_hidden, description)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    hierarchy.get("table", ""),
                    hierarchy.get("name", ""),
                    json.dumps(hierarchy.get("levels", [])),
                    hierarchy.get("is_hidden", False),
                    hierarchy.get("description", ""),
                ),
            )

        # Create roles table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_roles (
                role_id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_name TEXT,
                description TEXT,
                table_permissions TEXT,
                members TEXT
            )
        """
        )

        # Insert roles
        for role in data_model.get("roles", []):
            cursor.execute(
                """
                INSERT INTO powerbi_roles
                (role_name, description, table_permissions, members)
                VALUES (?, ?, ?, ?)
            """,
                (
                    role.get("name", ""),
                    role.get("description", ""),
                    json.dumps(role.get("table_permissions", [])),
                    json.dumps(role.get("members", [])),
                ),
            )

    def _create_dax_tables(self, cursor: sqlite3.Cursor, dax_expressions: Dict[str, Any]) -> None:
        """Create tables for DAX expressions and metadata."""

        # Create DAX measures table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_dax_measures (
                measure_id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT,
                measure_name TEXT,
                dax_expression TEXT,
                description TEXT,
                format_string TEXT,
                is_hidden BOOLEAN,
                display_folder TEXT,
                data_type TEXT,
                expression_length INTEGER,
                function_count INTEGER,
                complexity_score REAL,
                contains_time_intelligence BOOLEAN,
                contains_filter_functions BOOLEAN,
                referenced_tables TEXT,
                referenced_columns TEXT
            )
        """
        )

        # Insert DAX measures
        for measure in dax_expressions.get("measures", []):
            cursor.execute(
                """
                INSERT INTO powerbi_dax_measures 
                (table_name, measure_name, dax_expression, description, format_string, 
                 is_hidden, display_folder, data_type, expression_length, function_count,
                 complexity_score, contains_time_intelligence, contains_filter_functions,
                 referenced_tables, referenced_columns)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    measure.get("table", ""),
                    measure.get("name", ""),
                    measure.get("expression", ""),
                    measure.get("description", ""),
                    measure.get("format_string", ""),
                    measure.get("is_hidden", False),
                    measure.get("display_folder", ""),
                    measure.get("data_type", ""),
                    measure.get("expression_length", 0),
                    measure.get("function_count", 0),
                    measure.get("complexity_score", 0.0),
                    measure.get("contains_time_intelligence", False),
                    measure.get("contains_filter_functions", False),
                    json.dumps(measure.get("referenced_tables", [])),
                    json.dumps(measure.get("referenced_columns", [])),
                ),
            )

        # Create calculated columns table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_calculated_columns (
                column_id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT,
                column_name TEXT,
                dax_expression TEXT,
                data_type TEXT,
                format_string TEXT,
                is_hidden BOOLEAN,
                description TEXT,
                display_folder TEXT,
                expression_length INTEGER,
                function_count INTEGER,
                complexity_score REAL,
                referenced_tables TEXT,
                referenced_columns TEXT
            )
        """
        )

        # Insert calculated columns
        for column in dax_expressions.get("calculated_columns", []):
            cursor.execute(
                """
                INSERT INTO powerbi_calculated_columns 
                (table_name, column_name, dax_expression, data_type, format_string,
                 is_hidden, description, display_folder, expression_length, function_count,
                 complexity_score, referenced_tables, referenced_columns)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    column.get("table", ""),
                    column.get("name", ""),
                    column.get("expression", ""),
                    column.get("data_type", ""),
                    column.get("format_string", ""),
                    column.get("is_hidden", False),
                    column.get("description", ""),
                    column.get("display_folder", ""),
                    column.get("expression_length", 0),
                    column.get("function_count", 0),
                    column.get("complexity_score", 0.0),
                    json.dumps(column.get("referenced_tables", [])),
                    json.dumps(column.get("referenced_columns", [])),
                ),
            )

        # Create calculated tables table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_calculated_tables (
                table_id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT,
                dax_expression TEXT,
                description TEXT,
                is_hidden BOOLEAN,
                expression_length INTEGER,
                function_count INTEGER,
                complexity_score REAL,
                referenced_tables TEXT
            )
        """
        )

        # Insert calculated tables
        for table in dax_expressions.get("calculated_tables", []):
            cursor.execute(
                """
                INSERT INTO powerbi_calculated_tables 
                (table_name, dax_expression, description, is_hidden, expression_length,
                 function_count, complexity_score, referenced_tables)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    table.get("name", ""),
                    table.get("expression", ""),
                    table.get("description", ""),
                    table.get("is_hidden", False),
                    table.get("expression_length", 0),
                    table.get("function_count", 0),
                    table.get("complexity_score", 0.0),
                    json.dumps(table.get("referenced_tables", [])),
                ),
            )

    def _create_ui_tables(self, cursor: sqlite3.Cursor, ui_structure: Dict[str, Any]) -> None:
        """Create tables for UI structure."""

        # Create report pages table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_pages (
                page_id TEXT PRIMARY KEY,
                page_name TEXT,
                display_name TEXT,
                ordinal INTEGER,
                width INTEGER,
                height INTEGER,
                visual_count INTEGER,
                visibility TEXT,
                background_config TEXT,
                filters_config TEXT
            )
        """
        )

        # Insert page data
        for page in ui_structure.get("pages", []):
            cursor.execute(
                """
                INSERT OR REPLACE INTO powerbi_pages 
                (page_id, page_name, display_name, ordinal, width, height, 
                 visual_count, visibility, background_config, filters_config)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    page.get("name", ""),
                    page.get("name", ""),
                    page.get("display_name", ""),
                    page.get("ordinal", 0),
                    page.get("width", 1280),
                    page.get("height", 720),
                    page.get("visual_count", 0),
                    page.get("visibility", "Visible"),
                    json.dumps(page.get("background", {})),
                    json.dumps(page.get("filters", [])),
                ),
            )

        # Create visualizations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_visualizations (
                visual_id TEXT,
                page_context TEXT,
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
                config_size INTEGER,
                path TEXT,
                PRIMARY KEY (visual_id, page_context)
            )
        """
        )

        # Insert visualization data
        for visual in ui_structure.get("visualizations", []):
            visual_id = str(visual.get("id", ""))
            page_context = visual.get("page_context", "Unknown")
            position = visual.get("position", {})

            cursor.execute(
                """
                INSERT OR REPLACE INTO powerbi_visualizations 
                (visual_id, page_context, visual_type, enhanced_type, x_position, y_position,
                 width, height, z_order, text_content, data_roles_count, bookmark_action,
                 config_size, path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    visual_id,
                    page_context,
                    visual.get("type", "unknown"),
                    visual.get("enhanced_type", "Unknown"),
                    position.get("x", 0),
                    position.get("y", 0),
                    position.get("width", 0),
                    position.get("height", 0),
                    position.get("z_order", 0),
                    visual.get("text_content"),
                    visual.get("data_roles_count", 0),
                    visual.get("bookmark_action"),
                    visual.get("config_size", 0),
                    visual.get("path", ""),
                ),
            )

        # Create custom visuals table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS powerbi_custom_visuals (
                file_path TEXT PRIMARY KEY,
                visual_name TEXT,
                visual_version TEXT,
                description TEXT,
                config_json TEXT
            )
        """
        )

        # Insert custom visual data
        for custom_visual in ui_structure.get("custom_visuals", []):
            config = custom_visual.get("config", {})
            cursor.execute(
                """
                INSERT OR REPLACE INTO powerbi_custom_visuals 
                (file_path, visual_name, visual_version, description, config_json)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    custom_visual.get("file", ""),
                    custom_visual.get("name", "Unknown"),
                    custom_visual.get("version", "Unknown"),
                    custom_visual.get("description", ""),
                    json.dumps(config),
                ),
            )

    def _create_metadata_table(
        self, cursor: sqlite3.Cursor, extraction_results: Dict[str, Any]
    ) -> None:
        """Create metadata table with extraction information."""
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS _extraction_metadata (
                extraction_date TEXT,
                total_tables INTEGER,
                total_rows INTEGER,
                source_file TEXT,
                extraction_tool TEXT,
                pbix_file_size INTEGER,
                total_dax_measures INTEGER,
                total_calculated_columns INTEGER,
                total_ui_pages INTEGER,
                total_visualizations INTEGER
            )
        """
        )

        # Calculate metadata
        data_model = extraction_results.get("data_model", {})
        dax_expressions = extraction_results.get("dax_expressions", {})
        ui_structure = extraction_results.get("ui_structure", {})

        total_tables = len(data_model.get("tables", []))
        total_rows = sum(table.get("row_count", 0) for table in data_model.get("tables", []))

        cursor.execute(
            """
            INSERT INTO _extraction_metadata 
            (extraction_date, total_tables, total_rows, source_file, extraction_tool,
             pbix_file_size, total_dax_measures, total_calculated_columns, 
             total_ui_pages, total_visualizations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                pd.Timestamp.now().isoformat(),
                total_tables,
                total_rows,
                extraction_results.get("pbix_file", ""),
                "pbix-to-mcp v0.1.0",
                data_model.get("metadata", {}).get("file_size", 0),
                len(dax_expressions.get("measures", [])),
                len(dax_expressions.get("calculated_columns", [])),
                len(ui_structure.get("pages", [])),
                len(ui_structure.get("visualizations", [])),
            ),
        )

    def _create_views(self, cursor: sqlite3.Cursor) -> None:
        """Create helpful views for common queries."""

        # View: Enhanced data model overview
        cursor.execute(
            """
            CREATE VIEW IF NOT EXISTS powerbi_data_model_overview AS
            SELECT 
                'Data Tables' as component_type,
                COUNT(DISTINCT name) as count,
                'Regular: ' || COUNT(CASE WHEN type = 'table' THEN 1 END) ||
                ', Views: ' || COUNT(CASE WHEN type = 'view' THEN 1 END) as details
            FROM sqlite_master 
            WHERE type IN ('table', 'view')
            AND name NOT LIKE 'powerbi_%' 
            AND name NOT LIKE '_extraction_%' 
            AND name NOT LIKE 'sqlite_%'
            UNION ALL
            SELECT 
                'DAX Measures' as component_type,
                COUNT(*) as count,
                'Tables: ' || COUNT(DISTINCT table_name) ||
                ', Avg Complexity: ' || ROUND(AVG(complexity_score), 1) ||
                ', Time Intel: ' || SUM(CASE WHEN contains_time_intelligence THEN 1 ELSE 0 END) as details
            FROM powerbi_dax_measures
            UNION ALL
            SELECT 
                'Calculated Columns' as component_type,
                COUNT(*) as count,
                'Tables: ' || COUNT(DISTINCT table_name) ||
                ', Avg Complexity: ' || ROUND(AVG(complexity_score), 1) as details
            FROM powerbi_calculated_columns
            UNION ALL
            SELECT 
                'Relationships' as component_type,
                COUNT(*) as count,
                'Active: ' || SUM(CASE WHEN is_active THEN 1 ELSE 0 END) ||
                ', One-to-Many: ' || COUNT(CASE WHEN cardinality LIKE '%One-to-Many%' THEN 1 END) as details
            FROM powerbi_relationships
            UNION ALL
            SELECT 
                'Power Query Sources' as component_type,
                COUNT(*) as count,
                GROUP_CONCAT(DISTINCT source_type) as details
            FROM powerbi_power_query
            UNION ALL
            SELECT 
                'UI Pages' as component_type,
                COUNT(*) as count,
                'Total Visuals: ' || SUM(visual_count) as details
            FROM powerbi_pages
        """
        )

        # View: Table analysis with enhanced metadata
        cursor.execute(
            """
            CREATE VIEW IF NOT EXISTS powerbi_table_analysis AS
            SELECT 
                tm.table_name,
                tm.table_type,
                tm.row_count,
                tm.column_count,
                ROUND(tm.memory_size / 1024.0 / 1024.0, 2) as memory_mb,
                tm.has_duplicates,
                tm.data_extracted,
                COUNT(DISTINCT cm.column_name) as metadata_columns,
                COUNT(DISTINCT m.measure_name) as measures_count,
                COUNT(DISTINCT cc.column_name) as calculated_columns_count,
                COUNT(DISTINCT r1.relationship_id) + COUNT(DISTINCT r2.relationship_id) as total_relationships
            FROM powerbi_table_metadata tm
            LEFT JOIN powerbi_column_metadata cm ON tm.table_name = cm.table_name
            LEFT JOIN powerbi_dax_measures m ON tm.table_name = m.table_name
            LEFT JOIN powerbi_calculated_columns cc ON tm.table_name = cc.table_name
            LEFT JOIN powerbi_relationships r1 ON tm.table_name = r1.from_table
            LEFT JOIN powerbi_relationships r2 ON tm.table_name = r2.to_table
            GROUP BY tm.table_name, tm.table_type, tm.row_count, tm.column_count, 
                     tm.memory_size, tm.has_duplicates, tm.data_extracted
        """
        )

        # View: Column data quality analysis
        cursor.execute(
            """
            CREATE VIEW IF NOT EXISTS powerbi_column_quality AS
            SELECT 
                table_name,
                column_name,
                data_type,
                data_category,
                null_percentage,
                CASE 
                    WHEN null_percentage = 0 THEN 'Perfect'
                    WHEN null_percentage <= 5 THEN 'Good'
                    WHEN null_percentage <= 20 THEN 'Fair'
                    ELSE 'Poor'
                END as quality_score,
                unique_values,
                CASE 
                    WHEN is_key THEN 'Primary Key'
                    WHEN unique_values = 1 THEN 'Constant'
                    WHEN CAST(unique_values AS FLOAT) / NULLIF((SELECT row_count FROM powerbi_table_metadata WHERE table_name = powerbi_column_metadata.table_name), 0) > 0.95 THEN 'High Cardinality'
                    WHEN CAST(unique_values AS FLOAT) / NULLIF((SELECT row_count FROM powerbi_table_metadata WHERE table_name = powerbi_column_metadata.table_name), 0) < 0.05 THEN 'Low Cardinality'
                    ELSE 'Medium Cardinality'
                END as cardinality_category
            FROM powerbi_column_metadata
            WHERE table_name IN (SELECT table_name FROM powerbi_table_metadata WHERE data_extracted = 1)
        """
        )

        # View: DAX complexity analysis
        cursor.execute(
            """
            CREATE VIEW IF NOT EXISTS powerbi_dax_complexity AS
            SELECT 
                'Measures' as dax_type,
                COUNT(*) as total_count,
                ROUND(AVG(complexity_score), 2) as avg_complexity,
                ROUND(MAX(complexity_score), 2) as max_complexity,
                SUM(CASE WHEN contains_time_intelligence THEN 1 ELSE 0 END) as time_intelligence_count,
                SUM(CASE WHEN contains_filter_functions THEN 1 ELSE 0 END) as filter_functions_count,
                ROUND(AVG(function_count), 1) as avg_function_count,
                ROUND(AVG(expression_length), 0) as avg_expression_length
            FROM powerbi_dax_measures
            UNION ALL
            SELECT 
                'Calculated Columns' as dax_type,
                COUNT(*) as total_count,
                ROUND(AVG(complexity_score), 2) as avg_complexity,
                ROUND(MAX(complexity_score), 2) as max_complexity,
                0 as time_intelligence_count,
                0 as filter_functions_count,
                ROUND(AVG(function_count), 1) as avg_function_count,
                ROUND(AVG(expression_length), 0) as avg_expression_length
            FROM powerbi_calculated_columns
        """
        )

        # View: Visual types summary
        cursor.execute(
            """
            CREATE VIEW IF NOT EXISTS powerbi_visual_types_summary AS
            SELECT 
                enhanced_type,
                COUNT(*) as count,
                ROUND(AVG(width * height), 0) as avg_size,
                COUNT(CASE WHEN bookmark_action IS NOT NULL AND bookmark_action != '' THEN 1 END) as with_bookmarks,
                COUNT(CASE WHEN text_content IS NOT NULL AND text_content != '' THEN 1 END) as with_text,
                COUNT(DISTINCT page_context) as pages_used
            FROM powerbi_visualizations
            GROUP BY enhanced_type
            ORDER BY count DESC
        """
        )

        # View: Data source analysis
        cursor.execute(
            """
            CREATE VIEW IF NOT EXISTS powerbi_data_sources AS
            SELECT 
                source_type,
                COUNT(*) as source_count,
                GROUP_CONCAT(DISTINCT source_name) as source_names,
                ROUND(AVG(LENGTH(m_expression)), 0) as avg_expression_length
            FROM powerbi_power_query
            GROUP BY source_type
            ORDER BY source_count DESC
        """
        )

        # View: Model health summary
        cursor.execute(
            """
            CREATE VIEW IF NOT EXISTS powerbi_model_health AS
            SELECT 
                'Tables with High Null %' as metric,
                COUNT(*) as count,
                'Columns with >20% nulls' as description
            FROM powerbi_column_quality 
            WHERE quality_score = 'Poor'
            UNION ALL
            SELECT 
                'Complex DAX Measures' as metric,
                COUNT(*) as count,
                'Complexity score >10' as description
            FROM powerbi_dax_measures 
            WHERE complexity_score > 10
            UNION ALL
            SELECT 
                'Inactive Relationships' as metric,
                COUNT(*) as count,
                'Relationships not active' as description
            FROM powerbi_relationships 
            WHERE is_active = 0
            UNION ALL
            SELECT 
                'Tables without Data' as metric,
                COUNT(*) as count,
                'Tables with no extracted data' as description
            FROM powerbi_table_metadata 
            WHERE data_extracted = 0
        """
        )

    def _sanitize_table_name(self, table_name: str) -> str:
        """Sanitize table name for SQLite compatibility."""
        # Remove special characters and spaces
        safe_name = "".join(c for c in table_name if c.isalnum() or c in ("_",))

        # Ensure it starts with a letter
        if not safe_name or not safe_name[0].isalpha():
            safe_name = f"table_{safe_name}"

        return safe_name
