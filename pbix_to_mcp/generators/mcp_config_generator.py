"""
MCP Configuration Generator

Generates YAML configuration files for Google's genai-toolbox MCP server.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class YAMLMultilineStr(str):
    """Custom string class to force YAML multiline format with |"""

    pass


def yaml_multiline_representer(dumper, data):
    """Custom YAML representer for multiline strings"""
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


# Register the custom representer
yaml.add_representer(YAMLMultilineStr, yaml_multiline_representer)


class MCPConfigGenerator:
    """
    Generates MCP configuration YAML files for genai-toolbox.

    This class creates complete YAML configurations with:
    - SQLite data source definitions
    - Tool definitions for data access
    - Specialized tools for Power BI components
    - Toolsets for different use cases
    """

    def __init__(self, output_dir: Path):
        """
        Initialize the MCP config generator.

        Args:
            output_dir: Directory where config will be created
        """
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(f"{__name__}")

    def generate_config(
        self,
        extraction_results: Dict[str, Any],
        config_name: str,
        toolsets: Optional[List[str]] = None,
    ) -> Path:
        """
        Generate complete MCP configuration YAML.

        Args:
            extraction_results: Complete extraction results
            config_name: Name for the config file
            toolsets: List of toolset names to include

        Returns:
            Path to generated config file
        """
        config_path = self.output_dir / config_name

        self.logger.info(f"Generating MCP configuration: {config_name}")

        # Build configuration structure
        config = {
            "sources": self._generate_sources(extraction_results),
            "tools": self._generate_tools(extraction_results),
            "toolsets": self._generate_toolsets(extraction_results, toolsets),
        }

        # Write YAML file manually for better control
        self._write_yaml_config(config, config_path)

        self.logger.info(f"MCP configuration generated: {config_path}")
        return config_path

    def _generate_sources(self, extraction_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data source definitions."""
        # Use the absolute path to the database for better reliability
        db_path = str(self.output_dir / "data" / "powerbi_data.db")

        # Convert Windows paths to Unix-style for better cross-platform compatibility
        if "\\" in db_path:
            db_path = db_path.replace("\\", "/")

        source_name = self._get_source_name(extraction_results)

        return {source_name: {"kind": "sqlite", "database": db_path}}

    def _generate_tools(self, extraction_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate tool definitions."""
        source_name = self._get_source_name(extraction_results)
        tools = {}

        # Core database tools
        tools.update(self._generate_core_tools(source_name))

        # Data-specific tools
        if extraction_results.get("data_model", {}).get("tables"):
            tools.update(self._generate_data_tools(source_name, extraction_results["data_model"]))

        # DAX-specific tools
        if extraction_results.get("dax_expressions", {}).get("measures"):
            tools.update(self._generate_dax_tools(source_name))

        # UI-specific tools
        if extraction_results.get("ui_structure", {}).get("pages"):
            tools.update(self._generate_ui_tools(source_name))

        return tools

    def _generate_core_tools(self, source_name: str) -> Dict[str, Any]:
        """Generate core database operation tools."""
        return {
            "execute_sql": {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Execute arbitrary SQL statements against the Power BI database. Use this for complex queries, analysis, and data exploration.",
                "statement": YAMLMultilineStr(
                    "-- Replace this with your SQL statement\nSELECT 'Replace this statement with your SQL';"
                ),
            },
            "list_powerbi_tables": {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "List all Power BI tables with their schema information and row counts",
                "statement": YAMLMultilineStr(
                    """SELECT 
                name as table_name,
                type as object_type,
                sql as create_statement
            FROM sqlite_master 
            WHERE type = 'table' 
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name;"""
                ),
            },
            "powerbi_database_info": {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Get Power BI database information, extraction metadata, and statistics",
                "statement": YAMLMultilineStr(
                    """SELECT 
                'database_version' as info_type,
                sqlite_version() as value
            UNION ALL
            SELECT 
                'database_size_pages' as info_type,
                CAST(page_count as TEXT) as value
            FROM pragma_page_count()
            UNION ALL
            SELECT 
                'extraction_date' as info_type,
                extraction_date as value
            FROM _extraction_metadata
            UNION ALL
            SELECT 
                'source_pbix_file' as info_type,
                source_file as value
            FROM _extraction_metadata
            UNION ALL
            SELECT 
                'total_tables_extracted' as info_type,
                CAST(total_tables as TEXT) as value
            FROM _extraction_metadata;"""
                ),
            },
            "describe_powerbi_table": {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Get detailed column information for a specific Power BI table",
                "statement": "PRAGMA table_info(?);",
                "parameters": [
                    {
                        "name": "table_name",
                        "type": "string",
                        "description": "Name of the Power BI table to describe",
                    }
                ],
            },
        }

    def _generate_data_tools(self, source_name: str, data_model: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data-specific tools based on available tables."""
        tools = {}

        # Generic table tools
        tools.update(
            {
                "count_table_records": {
                    "kind": "sqlite-sql",
                    "source": source_name,
                    "description": "Count records in any Power BI table",
                    "statement": "SELECT COUNT(*) as record_count FROM {{.tableName}};",
                    "templateParameters": [
                        {
                            "name": "tableName",
                            "type": "string",
                            "description": "Name of the Power BI table to count records from",
                        }
                    ],
                },
                "get_table_sample": {
                    "kind": "sqlite-sql",
                    "source": source_name,
                    "description": "Get a sample of records from any Power BI table",
                    "statement": "SELECT * FROM {{.tableName}} LIMIT ?;",
                    "templateParameters": [
                        {
                            "name": "tableName",
                            "type": "string",
                            "description": "Name of the Power BI table to sample",
                        }
                    ],
                    "parameters": [
                        {
                            "name": "sample_size",
                            "type": "integer",
                            "description": "Number of sample records to return",
                            "default": 10,
                        }
                    ],
                },
                "query_table_with_filter": {
                    "kind": "sqlite-sql",
                    "source": source_name,
                    "description": "Query any Power BI table with dynamic column filtering",
                    "statement": YAMLMultilineStr(
                        """SELECT * FROM {{.tableName}} 
            WHERE {{.columnName}} = ?
            ORDER BY {{.orderBy}} 
            LIMIT ?;"""
                    ),
                    "templateParameters": [
                        {
                            "name": "tableName",
                            "type": "string",
                            "description": "Name of the Power BI table to query",
                        },
                        {
                            "name": "columnName",
                            "type": "string",
                            "description": "Column name for filtering",
                        },
                        {
                            "name": "orderBy",
                            "type": "string",
                            "description": "Column name for ordering results",
                        },
                    ],
                    "parameters": [
                        {
                            "name": "filter_value",
                            "type": "string",
                            "description": "Value to filter by",
                        },
                        {
                            "name": "limit",
                            "type": "integer",
                            "description": "Maximum number of records to return",
                            "default": 100,
                        },
                    ],
                },
            }
        )

        # Add supply chain specific tools if relevant tables exist
        tables = data_model.get("tables", [])
        table_names = [t.get("name", "").lower() for t in tables]

        # Supply chain specific tools
        if any("backorder" in name for name in table_names):
            tools["get_backorder_analysis"] = {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Analyze backorder percentages by region, product type, and other dimensions",
                "statement": YAMLMultilineStr(
                    """SELECT 
                Region,
                "Product Type",
                "Forecast Bias",
                AVG("Backorder %") as avg_backorder_pct,
                COUNT(*) as record_count,
                MIN("Backorder %") as min_backorder,
                MAX("Backorder %") as max_backorder
            FROM BackorderPercentage 
            WHERE Region = COALESCE(?, Region)
            AND "Product Type" = COALESCE(?, "Product Type")
            GROUP BY Region, "Product Type", "Forecast Bias"
            ORDER BY avg_backorder_pct DESC
            LIMIT ?;"""
                ),
                "parameters": [
                    {
                        "name": "region_filter",
                        "type": "string",
                        "description": "Filter by specific region (optional, use NULL for all regions)",
                        "required": False,
                    },
                    {
                        "name": "product_type_filter",
                        "type": "string",
                        "description": "Filter by specific product type (optional, use NULL for all types)",
                        "required": False,
                    },
                    {
                        "name": "limit",
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 100,
                    },
                ],
            }

        if any("risk" in name for name in table_names):
            tools["get_risk_assessment"] = {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Analyze risk scores and backorder risk by location and product",
                "statement": YAMLMultilineStr(
                    """SELECT 
                Location,
                "Risk Score",
                AVG("Backorder Risk") as avg_backorder_risk,
                COUNT(*) as product_count,
                COUNT(DISTINCT "Product ID") as unique_products
            FROM Risk 
            WHERE Location LIKE ?
            AND "Backorder Risk" >= ?
            GROUP BY Location, "Risk Score"
            ORDER BY avg_backorder_risk DESC
            LIMIT ?;"""
                ),
                "parameters": [
                    {
                        "name": "location_pattern",
                        "type": "string",
                        "description": "Location pattern to search for (use % for wildcards)",
                        "default": "%",
                    },
                    {
                        "name": "min_risk",
                        "type": "integer",
                        "description": "Minimum backorder risk threshold",
                        "default": 0,
                    },
                    {
                        "name": "limit",
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 50,
                    },
                ],
            }

        if any("supply" in name for name in table_names):
            tools["get_supply_analytics"] = {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Analyze supply chain metrics including manufactured goods percentages and forecast accuracy",
                "statement": YAMLMultilineStr(
                    """SELECT 
                "Forecast Accuracy",
                "Forecast Bias",
                "Demand Type",
                Plant,
                AVG("Manufactured Goods %") as avg_manufactured_pct,
                COUNT(*) as record_count
            FROM SupplyAnalytics 
            WHERE "Forecast Accuracy" = COALESCE(?, "Forecast Accuracy")
            AND Plant = COALESCE(?, Plant)
            GROUP BY "Forecast Accuracy", "Forecast Bias", "Demand Type", Plant
            ORDER BY avg_manufactured_pct DESC
            LIMIT ?;"""
                ),
                "parameters": [
                    {
                        "name": "forecast_accuracy_filter",
                        "type": "string",
                        "description": "Filter by forecast accuracy level (optional)",
                        "required": False,
                    },
                    {
                        "name": "plant_filter",
                        "type": "string",
                        "description": "Filter by specific plant (optional)",
                        "required": False,
                    },
                    {
                        "name": "limit",
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 100,
                    },
                ],
            }

        if any("explanation" in name for name in table_names):
            tools["get_explanations_by_risk"] = {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Get explanatory factors for risk levels by product and location",
                "statement": YAMLMultilineStr(
                    """SELECT 
                e.Location,
                e.Factor,
                e.Risk,
                COUNT(*) as factor_count,
                GROUP_CONCAT(DISTINCT e."Product ID") as affected_products
            FROM Explanations e
            WHERE e.Risk >= ?
            AND e.Location LIKE ?
            GROUP BY e.Location, e.Factor, e.Risk
            ORDER BY e.Risk DESC, factor_count DESC
            LIMIT ?;"""
                ),
                "parameters": [
                    {
                        "name": "min_risk_level",
                        "type": "integer",
                        "description": "Minimum risk level to include",
                        "default": 50,
                    },
                    {
                        "name": "location_pattern",
                        "type": "string",
                        "description": "Location pattern to search for (use % for wildcards)",
                        "default": "%",
                    },
                    {
                        "name": "limit",
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 50,
                    },
                ],
            }

        # Integrated analysis if multiple relevant tables exist
        if any("backorder" in name for name in table_names) and any(
            "risk" in name for name in table_names
        ):
            tools["get_integrated_risk_backorder_analysis"] = {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Comprehensive analysis combining risk data with backorder percentages",
                "statement": YAMLMultilineStr(
                    """SELECT 
                bp.Region,
                bp."Product Type",
                r.Location,
                r."Risk Score",
                AVG(bp."Backorder %") as avg_backorder_pct,
                AVG(r."Backorder Risk") as avg_backorder_risk,
                COUNT(*) as matching_records
            FROM BackorderPercentage bp
            JOIN Risk r ON bp."Product ID" = r."Product ID"
            WHERE bp.Region LIKE ?
            AND r."Risk Score" = COALESCE(?, r."Risk Score")
            GROUP BY bp.Region, bp."Product Type", r.Location, r."Risk Score"
            HAVING avg_backorder_pct > ?
            ORDER BY avg_backorder_pct DESC, avg_backorder_risk DESC
            LIMIT ?;"""
                ),
                "parameters": [
                    {
                        "name": "region_pattern",
                        "type": "string",
                        "description": "Region pattern to search for (use % for wildcards)",
                        "default": "%",
                    },
                    {
                        "name": "risk_score_filter",
                        "type": "string",
                        "description": "Filter by specific risk score (optional)",
                        "required": False,
                    },
                    {
                        "name": "min_backorder_threshold",
                        "type": "string",
                        "description": "Minimum backorder percentage threshold",
                        "default": "0.0",
                    },
                    {
                        "name": "limit",
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 50,
                    },
                ],
            }

        # Monthly trends if Month table exists
        if any("month" in name for name in table_names):
            tools["get_monthly_trends"] = {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Analyze trends by month using the Month dimension table",
                "statement": YAMLMultilineStr(
                    """SELECT 
                m.Month,
                m.ID as month_id,
                COUNT(bp."Product ID") as products_tracked,
                AVG(bp."Backorder %") as avg_backorder_pct
            FROM Month m
            LEFT JOIN BackorderPercentage bp ON m.Month = bp.Month
            GROUP BY m.Month, m.ID
            ORDER BY m.ID;"""
                ),
            }

        # Metadata tools
        if any("logo" in name for name in table_names):
            tools["get_powerbi_metadata"] = {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Get Power BI report metadata including logos and configuration",
                "statement": YAMLMultilineStr(
                    """SELECT 
                'extraction_info' as metadata_type,
                extraction_date,
                total_tables,
                total_rows,
                source_file,
                extraction_tool
            FROM _extraction_metadata
            UNION ALL
            SELECT 
                'logo_info' as metadata_type,
                URL as extraction_date,
                NULL as total_tables,
                NULL as total_rows,
                'Logo URL' as source_file,
                NULL as extraction_tool
            FROM Logo;"""
                ),
            }

        return tools

    def _generate_dax_tools(self, source_name: str) -> Dict[str, Any]:
        """Generate DAX-specific analysis tools."""
        return {
            "get_dax_measures": {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Get DAX measures with optional filtering by table or complexity",
                "statement": YAMLMultilineStr(
                    """SELECT 
                table_name,
                measure_name,
                dax_expression,
                description,
                complexity_score,
                contains_time_intelligence,
                contains_filter_functions
            FROM powerbi_dax_measures
            WHERE table_name = COALESCE(?, table_name)
            AND complexity_score >= ?
            ORDER BY complexity_score DESC
            LIMIT ?;"""
                ),
                "parameters": [
                    {
                        "name": "table_filter",
                        "type": "string",
                        "description": "Filter by specific table (optional, use NULL for all tables)",
                        "required": False,
                    },
                    {
                        "name": "min_complexity",
                        "type": "float",
                        "description": "Minimum complexity score",
                        "default": 0.0,
                    },
                    {
                        "name": "limit",
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 50,
                    },
                ],
            },
            "search_dax_expressions": {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Search DAX expressions by keyword or function",
                "statement": YAMLMultilineStr(
                    """SELECT 
                'Measure' as dax_type,
                table_name,
                measure_name as name,
                dax_expression,
                complexity_score
            FROM powerbi_dax_measures
            WHERE dax_expression LIKE ?
            UNION ALL
            SELECT 
                'Calculated Column' as dax_type,
                table_name,
                column_name as name,
                dax_expression,
                complexity_score
            FROM powerbi_calculated_columns
            WHERE dax_expression LIKE ?
            ORDER BY complexity_score DESC
            LIMIT ?;"""
                ),
                "parameters": [
                    {
                        "name": "search_pattern",
                        "type": "string",
                        "description": "Search pattern for DAX expressions (use % for wildcards)",
                    },
                    {
                        "name": "search_pattern2",
                        "type": "string",
                        "description": "Search pattern for calculated columns (same as first parameter)",
                    },
                    {
                        "name": "limit",
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 25,
                    },
                ],
            },
            "get_dax_complexity_analysis": {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Analyze DAX complexity across all expressions",
                "statement": "SELECT * FROM powerbi_dax_complexity ORDER BY avg_complexity DESC;",
            },
        }

    def _generate_ui_tools(self, source_name: str) -> Dict[str, Any]:
        """Generate UI structure analysis tools - only high-level summary, not detailed layout."""
        return {
            "get_report_pages": {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Get report pages with visual counts and basic information",
                "statement": YAMLMultilineStr(
                    """SELECT 
                page_name,
                display_name,
                ordinal,
                visual_count,
                visibility
            FROM powerbi_pages
            ORDER BY ordinal;"""
                ),
            },
            "get_visualizations_by_type": {
                "kind": "sqlite-sql",
                "source": source_name,
                "description": "Analyze visualizations by type with summary statistics",
                "statement": YAMLMultilineStr(
                    """SELECT 
                enhanced_type,
                COUNT(*) as count,
                COUNT(CASE WHEN text_content IS NOT NULL THEN 1 END) as with_text,
                COUNT(CASE WHEN bookmark_action IS NOT NULL THEN 1 END) as with_bookmarks
            FROM powerbi_visualizations
            WHERE enhanced_type = COALESCE(?, enhanced_type)
            GROUP BY enhanced_type
            ORDER BY count DESC
            LIMIT ?;"""
                ),
                "parameters": [
                    {
                        "name": "visual_type_filter",
                        "type": "string",
                        "description": "Filter by specific visual type (optional)",
                        "required": False,
                    },
                    {
                        "name": "limit",
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 20,
                    },
                ],
            },
        }

    def _generate_toolsets(
        self, extraction_results: Dict[str, Any], custom_toolsets: Optional[List[str]] = None
    ) -> Dict[str, List[str]]:
        """Generate toolsets for different use cases."""
        toolsets = {}

        # Basic analysis toolset
        basic_tools = [
            "list_powerbi_tables",
            "powerbi_database_info",
            "describe_powerbi_table",
            "get_table_sample",
            "count_table_records",
        ]
        toolsets["powerbi-basic-analysis"] = basic_tools

        # Supply chain insights (domain-specific tools)
        supply_chain_tools = []
        tables = extraction_results.get("data_model", {}).get("tables", [])
        table_names = [t.get("name", "").lower() for t in tables]

        if any("backorder" in name for name in table_names):
            supply_chain_tools.append("get_backorder_analysis")
        if any("risk" in name for name in table_names):
            supply_chain_tools.append("get_risk_assessment")
        if any("supply" in name for name in table_names):
            supply_chain_tools.append("get_supply_analytics")
        if any("explanation" in name for name in table_names):
            supply_chain_tools.append("get_explanations_by_risk")
        if any("backorder" in name for name in table_names) and any(
            "risk" in name for name in table_names
        ):
            supply_chain_tools.append("get_integrated_risk_backorder_analysis")

        if supply_chain_tools:
            toolsets["supply-chain-insights"] = supply_chain_tools

        # Advanced queries toolset
        advanced_tools = ["query_table_with_filter"]
        if any("month" in name for name in table_names):
            advanced_tools.append("get_monthly_trends")
        if any("logo" in name for name in table_names):
            advanced_tools.append("get_powerbi_metadata")
        advanced_tools.append("execute_sql")

        toolsets["powerbi-advanced-queries"] = advanced_tools

        # DAX analysis toolset
        if extraction_results.get("dax_expressions", {}).get("measures"):
            dax_tools = [
                "get_dax_measures",
                "search_dax_expressions",
                "get_dax_complexity_analysis",
            ]
            toolsets["powerbi-dax-analysis"] = dax_tools

        # UI analysis toolset (simplified)
        if extraction_results.get("ui_structure", {}).get("pages"):
            ui_tools = ["get_report_pages", "get_visualizations_by_type"]
            toolsets["powerbi-ui-analysis"] = ui_tools

        # Complete toolkit - includes all available tools
        all_tools = ["execute_sql"] + basic_tools

        # Add all other tools from other toolsets
        for toolset in toolsets.values():
            for tool in toolset:
                if tool not in all_tools:
                    all_tools.append(tool)

        toolsets["powerbi-complete-toolkit"] = all_tools

        return toolsets

    def _get_source_name(self, extraction_results: Dict[str, Any]) -> str:
        """Generate a source name from the PBIX file."""
        pbix_file = extraction_results.get("pbix_file", "")
        if pbix_file:
            pbix_name = Path(pbix_file).stem
            return f"{pbix_name.lower().replace(' ', '-')}-powerbi"
        return "powerbi-data"

    def _sanitize_tool_name(self, name: str) -> str:
        """Sanitize name for use in tool names."""
        return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")

    def _sanitize_table_name(self, table_name: str) -> str:
        """Sanitize table name for SQL."""
        return "".join(c for c in table_name if c.isalnum() or c in ("_",))

    def _write_yaml_config(self, config: Dict[str, Any], config_path: Path) -> None:
        """Write YAML config with proper multiline formatting."""
        with open(config_path, "w", encoding="utf-8") as f:
            # Write sources section
            f.write("sources:\n")
            for source_name, source_config in config["sources"].items():
                f.write(f"  {source_name}:\n")
                f.write(f"    kind: {source_config['kind']}\n")
                f.write(f"    database: {source_config['database']}\n")

            f.write("\ntools:\n")

            # Write tools section with proper multiline formatting
            for tool_name, tool_config in config["tools"].items():
                f.write(f"  {tool_name}:\n")
                f.write(f"    kind: {tool_config['kind']}\n")
                f.write(f"    source: {tool_config['source']}\n")
                f.write(f"    description: {tool_config['description']}\n")

                # Handle statement with multiline formatting
                statement = tool_config["statement"]
                if isinstance(statement, YAMLMultilineStr) or "\n" in str(statement):
                    f.write("    statement: |\n")
                    for line in str(statement).split("\n"):
                        if line.strip():
                            f.write(f"      {line.strip()}\n")
                else:
                    f.write(f"    statement: {statement}\n")

                # Handle template parameters
                if "templateParameters" in tool_config:
                    f.write("    templateParameters:\n")
                    for param in tool_config["templateParameters"]:
                        f.write(f"    - name: {param['name']}\n")
                        f.write(f"      type: {param['type']}\n")
                        f.write(f"      description: {param['description']}\n")

                # Handle parameters
                if "parameters" in tool_config:
                    f.write("    parameters:\n")
                    for param in tool_config["parameters"]:
                        f.write(f"    - name: {param['name']}\n")
                        f.write(f"      type: {param['type']}\n")
                        f.write(f"      description: {param['description']}\n")
                        if "required" in param:
                            f.write(f"      required: {str(param['required']).lower()}\n")
                        if "default" in param:
                            default_val = param["default"]
                            if isinstance(default_val, str):
                                f.write(f'      default: "{default_val}"\n')
                            else:
                                f.write(f"      default: {default_val}\n")

            # Write toolsets section
            f.write("\ntoolsets:\n")
            for toolset_name, tools in config["toolsets"].items():
                f.write(f"  {toolset_name}:\n")
                for tool in tools:
                    f.write(f"  - {tool}\n")
