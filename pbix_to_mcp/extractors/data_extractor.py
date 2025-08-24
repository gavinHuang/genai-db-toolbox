"""
Data Extractor for Power BI Files

Extracts data models, tables, relationships, and schema information from PBIX files.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from pbixray import PBIXRay


class DataExtractor:
    """
    Extracts data model components from PBIX files.

    This class handles extraction of:
    - Table schemas and data
    - Relationships between tables
    - Column metadata and types
    - Power Query (M) expressions
    """

    def __init__(self, pbix_path: Path):
        """
        Initialize the data extractor.

        Args:
            pbix_path: Path to the PBIX file
        """
        self.pbix_path = Path(pbix_path)
        self.logger = logging.getLogger(f"{__name__}.{self.pbix_path.stem}")

    def extract_data_model(self, data_limit: int = 10000) -> Dict[str, Any]:
        """
        Extract complete data model from PBIX file.

        Args:
            data_limit: Maximum rows to extract per table

        Returns:
            Dictionary containing tables, relationships, and metadata
        """
        self.logger.info("Starting data model extraction")

        try:
            # Initialize pbixray
            pbix = PBIXRay(str(self.pbix_path))

            results = {
                "metadata": self._extract_metadata(pbix),
                "tables": self._extract_tables(pbix, data_limit),
                "relationships": self._extract_relationships(pbix),
                "measures": self._extract_measures(pbix),
                "calculated_columns": self._extract_calculated_columns(pbix),
                "calculated_tables": self._extract_calculated_tables(pbix),
                "hierarchies": self._extract_hierarchies(pbix),
                "perspectives": self._extract_perspectives(pbix),
                "roles": self._extract_roles(pbix),
                "power_query": self._extract_power_query(pbix),
                "extraction_info": {
                    "data_limit": data_limit,
                    "total_tables": 0,
                    "total_rows": 0,
                    "total_measures": 0,
                    "total_calculated_columns": 0,
                    "total_relationships": 0,
                },
            }

            # Calculate totals
            results["extraction_info"]["total_tables"] = len(results["tables"])
            results["extraction_info"]["total_rows"] = sum(
                table.get("row_count", 0) for table in results["tables"]
            )
            results["extraction_info"]["total_measures"] = len(results["measures"])
            results["extraction_info"]["total_calculated_columns"] = len(
                results["calculated_columns"]
            )
            results["extraction_info"]["total_relationships"] = len(results["relationships"])

            self.logger.info(
                f"Data model extraction complete: {results['extraction_info']['total_tables']} tables, "
                f"{results['extraction_info']['total_measures']} measures, "
                f"{results['extraction_info']['total_relationships']} relationships"
            )
            return results

        except Exception as e:
            self.logger.error(f"Data model extraction failed: {e}")
            raise

    def _extract_metadata(self, pbix: PBIXRay) -> Dict[str, Any]:
        """Extract Power BI file metadata."""
        metadata = {
            "file_size": pbix.size if hasattr(pbix, "size") else 0,
            "version": "Unknown",
            "creation_date": None,
            "last_modified": None,
        }

        try:
            if hasattr(pbix, "metadata") and pbix.metadata is not None:
                metadata_df = pbix.metadata
                if hasattr(metadata_df, "iterrows"):
                    for _, row in metadata_df.iterrows():
                        name = row.get("Name", "").lower()
                        value = row.get("Value", "")

                        if "version" in name:
                            metadata["version"] = value
                        elif "created" in name or "date" in name:
                            metadata["creation_date"] = value
        except Exception as e:
            self.logger.warning(f"Could not extract metadata: {e}")

        return metadata

    def _extract_tables(self, pbix: PBIXRay, data_limit: int) -> List[Dict[str, Any]]:
        """Extract all tables with comprehensive schema and data."""
        tables = []

        try:
            # Get table names
            table_names = pbix.tables if hasattr(pbix, "tables") else []

            for table_name in table_names:
                table_info = {
                    "name": table_name,
                    "columns": [],
                    "row_count": 0,
                    "data_extracted": False,
                    "data": None,
                    "column_count": 0,
                    "table_type": "Regular",  # Regular, Calculated, etc.
                    "is_hidden": False,
                    "description": "",
                    "data_category": "",
                }

                try:
                    # Get table data
                    table_df = pbix.get_table(table_name)

                    if table_df is not None and not table_df.empty:
                        # Extract comprehensive column information
                        for col_name in table_df.columns:
                            col_data = table_df[col_name].dropna()

                            # Comprehensive column analysis
                            col_info = self._analyze_column(col_name, col_data, table_df[col_name])
                            table_info["columns"].append(col_info)

                        # Store data (limited)
                        table_info["row_count"] = len(table_df)
                        table_info["column_count"] = len(table_df.columns)
                        table_info["data"] = table_df.head(data_limit).copy()
                        table_info["data_extracted"] = True

                        # Additional table metadata
                        table_info["memory_size"] = table_df.memory_usage(deep=True).sum()
                        table_info["has_duplicates"] = table_df.duplicated().any()

                        self.logger.debug(
                            f"Extracted table '{table_name}': {table_info['row_count']} rows, {table_info['column_count']} columns"
                        )
                    else:
                        self.logger.warning(f"Table '{table_name}' is empty or could not be read")
                        table_info["error"] = "Table is empty or could not be read"

                except Exception as e:
                    self.logger.error(f"Could not extract data for table '{table_name}': {e}")
                    table_info["error"] = str(e)

                tables.append(table_info)

        except Exception as e:
            self.logger.error(f"Table extraction failed: {e}")
            # Return empty list rather than failing completely

        return tables

    def _analyze_column(self, col_name: str, col_data, full_col_data) -> Dict[str, Any]:
        """Perform comprehensive column analysis."""
        # Infer column type with better logic
        if len(col_data) > 0:
            first_val = col_data.iloc[0]
            if isinstance(first_val, (int, float)):
                if isinstance(first_val, int):
                    col_type = "Integer"
                else:
                    col_type = "Decimal"
            elif isinstance(first_val, str):
                col_type = "Text"
            elif hasattr(first_val, "date") or "date" in str(type(first_val)).lower():
                col_type = "DateTime"
            elif isinstance(first_val, bool):
                col_type = "Boolean"
            else:
                col_type = str(type(first_val).__name__)
        else:
            col_type = "Unknown"

        # Calculate statistics
        unique_count = len(col_data.unique()) if len(col_data) > 0 else 0
        null_count = full_col_data.isnull().sum()

        col_info = {
            "name": col_name,
            "type": col_type,
            "nullable": null_count > 0,
            "unique_values": unique_count,
            "null_count": int(null_count),
            "null_percentage": (
                float(null_count / len(full_col_data) * 100) if len(full_col_data) > 0 else 0
            ),
            "is_key": unique_count == len(col_data) and len(col_data) > 0,  # Potential key column
            "data_category": self._detect_data_category(col_name, col_data),
            "format_string": "",
            "is_hidden": False,
            "sort_by_column": "",
            "description": "",
        }

        # Add type-specific statistics
        if col_type in ["Integer", "Decimal"]:
            try:
                numeric_data = pd.to_numeric(col_data, errors="coerce").dropna()
                if len(numeric_data) > 0:
                    col_info["min_value"] = float(numeric_data.min())
                    col_info["max_value"] = float(numeric_data.max())
                    col_info["mean_value"] = float(numeric_data.mean())
                    col_info["std_deviation"] = float(numeric_data.std())
            except Exception:
                pass
        elif col_type == "Text":
            try:
                text_data = col_data.astype(str)
                col_info["min_length"] = int(text_data.str.len().min())
                col_info["max_length"] = int(text_data.str.len().max())
                col_info["avg_length"] = float(text_data.str.len().mean())
            except Exception:
                pass

        return col_info

    def _detect_data_category(self, col_name: str, col_data) -> str:
        """Detect the data category/semantic type of a column."""
        col_name_lower = col_name.lower()

        # Common patterns
        if any(pattern in col_name_lower for pattern in ["id", "key", "code"]):
            return "Identifier"
        elif any(pattern in col_name_lower for pattern in ["date", "time", "year", "month"]):
            return "Date/Time"
        elif any(
            pattern in col_name_lower for pattern in ["amount", "price", "cost", "value", "revenue"]
        ):
            return "Currency"
        elif any(pattern in col_name_lower for pattern in ["percent", "rate", "ratio"]):
            return "Percentage"
        elif any(pattern in col_name_lower for pattern in ["count", "qty", "quantity", "number"]):
            return "Count"
        elif any(pattern in col_name_lower for pattern in ["name", "title", "description"]):
            return "Name"
        elif any(pattern in col_name_lower for pattern in ["email", "phone", "address"]):
            return "Contact"
        elif any(pattern in col_name_lower for pattern in ["url", "link", "path"]):
            return "Web URL"
        else:
            return "General"

    def _extract_relationships(self, pbix: PBIXRay) -> List[Dict[str, Any]]:
        """Extract table relationships."""
        relationships = []

        try:
            if hasattr(pbix, "relationships") and pbix.relationships is not None:
                rel_data = pbix.relationships

                if hasattr(rel_data, "iterrows"):
                    columns = rel_data.columns.tolist()

                    for _, row in rel_data.iterrows():
                        relationship = {
                            "from_table": row.get(
                                columns[0] if columns else "FromTable", "Unknown"
                            ),
                            "from_column": row.get(
                                columns[1] if len(columns) > 1 else "FromColumn", "Unknown"
                            ),
                            "to_table": row.get(
                                columns[2] if len(columns) > 2 else "ToTable", "Unknown"
                            ),
                            "to_column": row.get(
                                columns[3] if len(columns) > 3 else "ToColumn", "Unknown"
                            ),
                            "cardinality": row.get(
                                columns[4] if len(columns) > 4 else "Type", "One-to-Many"
                            ),
                            "is_active": row.get(
                                columns[5] if len(columns) > 5 else "IsActive", True
                            ),
                            "cross_filter_direction": "Single",  # Default
                        }
                        relationships.append(relationship)

        except Exception as e:
            self.logger.warning(f"Could not extract relationships: {e}")

        return relationships

    def _extract_power_query(self, pbix: PBIXRay) -> Dict[str, Any]:
        """Extract Power Query (M) expressions."""
        power_query = {}

        try:
            if hasattr(pbix, "power_query") and pbix.power_query is not None:
                pq_data = pbix.power_query

                if hasattr(pq_data, "iterrows"):
                    columns = pq_data.columns.tolist()

                    for _, row in pq_data.iterrows():
                        query_name = row.get(columns[0] if columns else "Name", "Unknown")
                        query_expression = row.get(
                            columns[2] if len(columns) > 2 else "Expression", ""
                        )
                        query_type = row.get(columns[1] if len(columns) > 1 else "Type", "Query")

                        power_query[query_name] = {
                            "expression": query_expression,
                            "type": query_type,
                            "source_type": self._detect_source_type(query_expression),
                        }

                elif isinstance(pq_data, dict):
                    power_query = pq_data

        except Exception as e:
            self.logger.warning(f"Could not extract Power Query: {e}")
            power_query["error"] = str(e)

        return power_query

    def _extract_measures(self, pbix: PBIXRay) -> List[Dict[str, Any]]:
        """Extract DAX measures with comprehensive analysis."""
        measures = []

        try:
            # Try different approaches to get measures
            if hasattr(pbix, "dax_measures") and pbix.dax_measures is not None:
                # Check if it's a DataFrame or dict
                if hasattr(pbix.dax_measures, "empty"):  # It's a DataFrame
                    if not pbix.dax_measures.empty:
                        # Convert DataFrame to dict format
                        for _, row in pbix.dax_measures.iterrows():
                            measure_info = self._analyze_dax_measure_from_row(row)
                            measures.append(measure_info)
                elif isinstance(pbix.dax_measures, dict):
                    for table_name, table_measures in pbix.dax_measures.items():
                        if isinstance(table_measures, list):
                            for measure in table_measures:
                                measure_info = self._analyze_dax_measure(measure, table_name)
                                measures.append(measure_info)
                        elif isinstance(table_measures, dict):
                            measure_info = self._analyze_dax_measure(table_measures, table_name)
                            measures.append(measure_info)

            # Alternative approach for measures
            if hasattr(pbix, "measures") and pbix.measures is not None:
                if hasattr(pbix.measures, "empty"):  # DataFrame
                    if not pbix.measures.empty:
                        for _, row in pbix.measures.iterrows():
                            measure_info = self._analyze_dax_measure_from_row(row)
                            measures.append(measure_info)
                elif isinstance(pbix.measures, (list, dict)):
                    for measure in pbix.measures:
                        measure_info = self._analyze_dax_measure(measure, measure.get("table", ""))
                        measures.append(measure_info)

        except Exception as e:
            self.logger.warning(f"Could not extract DAX measures: {e}")
            measures.append({"error": str(e), "component": "measures"})

        return measures

    def _analyze_dax_measure_from_row(self, row) -> Dict[str, Any]:
        """Analyze a DAX measure from DataFrame row."""
        # Handle pandas Series row
        row_dict = row.to_dict() if hasattr(row, "to_dict") else row

        expression = row_dict.get("expression", row_dict.get("Expression", ""))
        table_name = row_dict.get("table", row_dict.get("Table", ""))

        return {
            "table": table_name,
            "name": row_dict.get("name", row_dict.get("Name", "")),
            "expression": expression,
            "description": row_dict.get("description", row_dict.get("Description", "")),
            "format_string": row_dict.get("formatString", row_dict.get("FormatString", "")),
            "is_hidden": row_dict.get("isHidden", row_dict.get("IsHidden", False)),
            "display_folder": row_dict.get("displayFolder", row_dict.get("DisplayFolder", "")),
            "data_type": row_dict.get("dataType", row_dict.get("DataType", "Variant")),
            "expression_length": len(str(expression)),
            "function_count": self._count_dax_functions(str(expression)),
            "complexity_score": self._calculate_dax_complexity(str(expression)),
            "contains_time_intelligence": self._contains_time_intelligence(str(expression)),
            "contains_filter_functions": self._contains_filter_functions(str(expression)),
            "referenced_tables": self._extract_referenced_tables(str(expression)),
            "referenced_columns": self._extract_referenced_columns(str(expression)),
        }

    def _analyze_dax_measure(self, measure: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """Analyze a DAX measure with detailed metadata."""
        expression = measure.get("expression", measure.get("Expression", ""))

        return {
            "table": table_name,
            "name": measure.get("name", measure.get("Name", "")),
            "expression": expression,
            "description": measure.get("description", measure.get("Description", "")),
            "format_string": measure.get("formatString", measure.get("FormatString", "")),
            "is_hidden": measure.get("isHidden", measure.get("IsHidden", False)),
            "display_folder": measure.get("displayFolder", measure.get("DisplayFolder", "")),
            "data_type": measure.get("dataType", measure.get("DataType", "Variant")),
            "expression_length": len(expression),
            "function_count": self._count_dax_functions(expression),
            "complexity_score": self._calculate_dax_complexity(expression),
            "contains_time_intelligence": self._contains_time_intelligence(expression),
            "contains_filter_functions": self._contains_filter_functions(expression),
            "referenced_tables": self._extract_referenced_tables(expression),
            "referenced_columns": self._extract_referenced_columns(expression),
        }

    def _extract_calculated_columns(self, pbix: PBIXRay) -> List[Dict[str, Any]]:
        """Extract calculated columns with comprehensive analysis."""
        calculated_columns = []

        try:
            if hasattr(pbix, "dax_columns") and pbix.dax_columns is not None:
                # Check if it's a DataFrame or dict
                if hasattr(pbix.dax_columns, "empty"):  # It's a DataFrame
                    if not pbix.dax_columns.empty:
                        for _, row in pbix.dax_columns.iterrows():
                            column_info = self._analyze_calculated_column_from_row(row)
                            calculated_columns.append(column_info)
                elif isinstance(pbix.dax_columns, dict):
                    for table_name, table_columns in pbix.dax_columns.items():
                        if isinstance(table_columns, list):
                            for column in table_columns:
                                column_info = self._analyze_calculated_column(column, table_name)
                                calculated_columns.append(column_info)
                        elif isinstance(table_columns, dict):
                            column_info = self._analyze_calculated_column(table_columns, table_name)
                            calculated_columns.append(column_info)

        except Exception as e:
            self.logger.warning(f"Could not extract calculated columns: {e}")
            calculated_columns.append({"error": str(e), "component": "calculated_columns"})

        return calculated_columns

    def _analyze_calculated_column_from_row(self, row) -> Dict[str, Any]:
        """Analyze a calculated column from DataFrame row."""
        row_dict = row.to_dict() if hasattr(row, "to_dict") else row

        expression = row_dict.get("expression", row_dict.get("Expression", ""))
        table_name = row_dict.get("table", row_dict.get("Table", ""))

        return {
            "table": table_name,
            "name": row_dict.get("name", row_dict.get("Name", "")),
            "expression": expression,
            "data_type": row_dict.get("dataType", row_dict.get("DataType", "Variant")),
            "format_string": row_dict.get("formatString", row_dict.get("FormatString", "")),
            "is_hidden": row_dict.get("isHidden", row_dict.get("IsHidden", False)),
            "description": row_dict.get("description", row_dict.get("Description", "")),
            "display_folder": row_dict.get("displayFolder", row_dict.get("DisplayFolder", "")),
            "expression_length": len(str(expression)),
            "function_count": self._count_dax_functions(str(expression)),
            "complexity_score": self._calculate_dax_complexity(str(expression)),
            "referenced_tables": self._extract_referenced_tables(str(expression)),
            "referenced_columns": self._extract_referenced_columns(str(expression)),
        }

    def _analyze_calculated_column(self, column: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """Analyze a calculated column with detailed metadata."""
        expression = column.get("expression", column.get("Expression", ""))

        return {
            "table": table_name,
            "name": column.get("name", column.get("Name", "")),
            "expression": expression,
            "data_type": column.get("dataType", column.get("DataType", "Variant")),
            "format_string": column.get("formatString", column.get("FormatString", "")),
            "is_hidden": column.get("isHidden", column.get("IsHidden", False)),
            "description": column.get("description", column.get("Description", "")),
            "display_folder": column.get("displayFolder", column.get("DisplayFolder", "")),
            "expression_length": len(expression),
            "function_count": self._count_dax_functions(expression),
            "complexity_score": self._calculate_dax_complexity(expression),
            "referenced_tables": self._extract_referenced_tables(expression),
            "referenced_columns": self._extract_referenced_columns(expression),
        }

    def _extract_calculated_tables(self, pbix: PBIXRay) -> List[Dict[str, Any]]:
        """Extract calculated tables."""
        calculated_tables = []

        try:
            if hasattr(pbix, "dax_tables") and pbix.dax_tables is not None:
                # Check if it's a DataFrame or dict
                if hasattr(pbix.dax_tables, "empty"):  # It's a DataFrame
                    if not pbix.dax_tables.empty:
                        for _, row in pbix.dax_tables.iterrows():
                            table_info = self._analyze_calculated_table_from_row(row)
                            calculated_tables.append(table_info)
                elif isinstance(pbix.dax_tables, dict):
                    for table_name, table_info in pbix.dax_tables.items():
                        if isinstance(table_info, dict):
                            expression = table_info.get(
                                "expression", table_info.get("Expression", "")
                            )
                            calculated_tables.append(
                                {
                                    "name": table_name,
                                    "expression": expression,
                                    "description": table_info.get(
                                        "description", table_info.get("Description", "")
                                    ),
                                    "is_hidden": table_info.get(
                                        "isHidden", table_info.get("IsHidden", False)
                                    ),
                                    "expression_length": len(str(expression)),
                                    "function_count": self._count_dax_functions(str(expression)),
                                    "complexity_score": self._calculate_dax_complexity(
                                        str(expression)
                                    ),
                                    "referenced_tables": self._extract_referenced_tables(
                                        str(expression)
                                    ),
                                }
                            )

        except Exception as e:
            self.logger.warning(f"Could not extract calculated tables: {e}")
            calculated_tables.append({"error": str(e), "component": "calculated_tables"})

        return calculated_tables

    def _analyze_calculated_table_from_row(self, row) -> Dict[str, Any]:
        """Analyze a calculated table from DataFrame row."""
        row_dict = row.to_dict() if hasattr(row, "to_dict") else row

        expression = row_dict.get("expression", row_dict.get("Expression", ""))
        table_name = row_dict.get("name", row_dict.get("Name", ""))

        return {
            "name": table_name,
            "expression": expression,
            "description": row_dict.get("description", row_dict.get("Description", "")),
            "is_hidden": row_dict.get("isHidden", row_dict.get("IsHidden", False)),
            "expression_length": len(str(expression)),
            "function_count": self._count_dax_functions(str(expression)),
            "complexity_score": self._calculate_dax_complexity(str(expression)),
            "referenced_tables": self._extract_referenced_tables(str(expression)),
        }

    def _extract_hierarchies(self, pbix: PBIXRay) -> List[Dict[str, Any]]:
        """Extract table hierarchies."""
        hierarchies = []

        try:
            if hasattr(pbix, "hierarchies") and pbix.hierarchies:
                for hierarchy in pbix.hierarchies:
                    hierarchies.append(
                        {
                            "table": hierarchy.get("table", ""),
                            "name": hierarchy.get("name", ""),
                            "levels": hierarchy.get("levels", []),
                            "is_hidden": hierarchy.get("isHidden", False),
                            "description": hierarchy.get("description", ""),
                        }
                    )

        except Exception as e:
            self.logger.warning(f"Could not extract hierarchies: {e}")

        return hierarchies

    def _extract_perspectives(self, pbix: PBIXRay) -> List[Dict[str, Any]]:
        """Extract perspectives/views."""
        perspectives = []

        try:
            if hasattr(pbix, "perspectives") and pbix.perspectives:
                for perspective in pbix.perspectives:
                    perspectives.append(
                        {
                            "name": perspective.get("name", ""),
                            "description": perspective.get("description", ""),
                            "tables": perspective.get("tables", []),
                            "columns": perspective.get("columns", []),
                            "measures": perspective.get("measures", []),
                        }
                    )

        except Exception as e:
            self.logger.warning(f"Could not extract perspectives: {e}")

        return perspectives

    def _extract_roles(self, pbix: PBIXRay) -> List[Dict[str, Any]]:
        """Extract security roles."""
        roles = []

        try:
            if hasattr(pbix, "roles") and pbix.roles:
                for role in pbix.roles:
                    roles.append(
                        {
                            "name": role.get("name", ""),
                            "description": role.get("description", ""),
                            "table_permissions": role.get("tablePermissions", []),
                            "members": role.get("members", []),
                        }
                    )

        except Exception as e:
            self.logger.warning(f"Could not extract roles: {e}")

        return roles

    def _count_dax_functions(self, expression: str) -> int:
        """Count DAX functions in an expression."""
        if not expression:
            return 0

        # Common DAX functions - this is a basic implementation
        dax_functions = [
            "SUM",
            "AVERAGE",
            "COUNT",
            "COUNTA",
            "MIN",
            "MAX",
            "CALCULATE",
            "FILTER",
            "ALL",
            "ALLEXCEPT",
            "VALUES",
            "SUMX",
            "AVERAGEX",
            "COUNTX",
            "MINX",
            "MAXX",
            "DATEADD",
            "DATEDIFF",
            "TOTALYTD",
            "TOTALQTD",
            "TOTALMTD",
            "RELATED",
            "RELATEDTABLE",
            "LOOKUPVALUE",
            "IF",
            "SWITCH",
            "AND",
            "OR",
            "NOT",
            "FORMAT",
            "CONCATENATE",
            "SUBSTITUTE",
        ]

        count = 0
        expression_upper = expression.upper()
        for func in dax_functions:
            count += expression_upper.count(func + "(")

        return count

    def _calculate_dax_complexity(self, expression: str) -> float:
        """Calculate a complexity score for DAX expression."""
        if not expression:
            return 0.0

        complexity = 0.0

        # Length factor
        complexity += len(expression) / 100

        # Nesting level (count parentheses)
        max_nesting = 0
        current_nesting = 0
        for char in expression:
            if char == "(":
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)
            elif char == ")":
                current_nesting -= 1
        complexity += max_nesting * 2

        # Function count
        complexity += self._count_dax_functions(expression) * 1.5

        # Advanced patterns
        if "CALCULATE(" in expression.upper():
            complexity += 2
        if any(pattern in expression.upper() for pattern in ["FILTER(", "SUMX(", "AVERAGEX("]):
            complexity += 3
        if any(pattern in expression.upper() for pattern in ["TOTALYTD", "TOTALQTD", "DATEADD"]):
            complexity += 4

        return round(complexity, 2)

    def _contains_time_intelligence(self, expression: str) -> bool:
        """Check if expression contains time intelligence functions."""
        time_functions = [
            "TOTALYTD",
            "TOTALQTD",
            "TOTALMTD",
            "DATEADD",
            "DATEDIFF",
            "PARALLELPERIOD",
            "SAMEPERIODLASTYEAR",
            "PREVIOUSMONTH",
            "NEXTMONTH",
            "STARTOFYEAR",
            "ENDOFYEAR",
            "STARTOFMONTH",
            "ENDOFMONTH",
        ]

        expression_upper = expression.upper()
        return any(func in expression_upper for func in time_functions)

    def _contains_filter_functions(self, expression: str) -> bool:
        """Check if expression contains filter functions."""
        filter_functions = [
            "FILTER",
            "ALL",
            "ALLEXCEPT",
            "ALLSELECTED",
            "KEEPFILTERS",
            "REMOVEFILTERS",
            "USERELATIONSHIP",
        ]

        expression_upper = expression.upper()
        return any(func in expression_upper for func in filter_functions)

    def _extract_referenced_tables(self, expression: str) -> List[str]:
        """Extract table references from DAX expression."""
        import re

        # Basic pattern matching for table references
        # This is a simplified approach - real DAX parsing would be more complex
        table_pattern = r"'([^']+)'\[|([A-Za-z_][A-Za-z0-9_\s]*)\["

        matches = re.findall(table_pattern, expression)
        tables = []

        for match in matches:
            table_name = match[0] if match[0] else match[1]
            if table_name and table_name not in tables:
                tables.append(table_name.strip())

        return tables

    def _extract_referenced_columns(self, expression: str) -> List[str]:
        """Extract column references from DAX expression."""
        import re

        # Pattern for column references: [Column Name] or Table[Column Name]
        column_pattern = r"\[([^\]]+)\]"

        matches = re.findall(column_pattern, expression)
        columns = []

        for match in matches:
            if match and match not in columns:
                columns.append(match.strip())

        return columns

    def _detect_source_type(self, expression: str) -> str:
        """Detect the source type from M expression."""
        if not expression:
            return "Unknown"

        expression_lower = expression.lower()

        if "excel.workbook" in expression_lower:
            return "Excel"
        elif "sql.database" in expression_lower:
            return "SQL Database"
        elif "azurestorage" in expression_lower:
            return "Azure Storage"
        elif "web.contents" in expression_lower:
            return "Web Source"
        elif "table.fromrows" in expression_lower:
            return "Embedded Table"
        elif "sharepoint" in expression_lower:
            return "SharePoint"
        elif "odata" in expression_lower:
            return "OData"
        else:
            return "Other"

    def get_table_summary(self) -> Dict[str, Any]:
        """Get a quick summary of extractable tables."""
        try:
            pbix = PBIXRay(str(self.pbix_path))
            table_names = pbix.tables if hasattr(pbix, "tables") else []

            return {
                "total_tables": len(table_names),
                "table_names": list(table_names),
                "file_size": pbix.size if hasattr(pbix, "size") else 0,
            }
        except Exception as e:
            self.logger.error(f"Could not get table summary: {e}")
            return {"error": str(e)}
