"""
DAX Extractor for Power BI Files

Extracts DAX expressions including measures, calculated columns, calculated tables, and relationships.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pbixray import PBIXRay


class DAXExtractor:
    """
    Extracts DAX expressions and formulas from PBIX files.

    This class handles extraction of:
    - DAX measures with expressions
    - Calculated columns
    - Calculated tables
    - DAX-related metadata
    """

    def __init__(self, pbix_path: Path):
        """
        Initialize the DAX extractor.

        Args:
            pbix_path: Path to the PBIX file
        """
        self.pbix_path = Path(pbix_path)
        self.logger = logging.getLogger(f"{__name__}.{self.pbix_path.stem}")

    def extract_all_dax(self) -> Dict[str, Any]:
        """
        Extract all DAX expressions from PBIX file.

        Returns:
            Dictionary containing measures, calculated columns, and tables
        """
        self.logger.info("Starting DAX extraction")

        try:
            # Initialize pbixray
            pbix = PBIXRay(str(self.pbix_path))

            results = {
                "measures": self._extract_measures(pbix),
                "calculated_columns": self._extract_calculated_columns(pbix),
                "calculated_tables": self._extract_calculated_tables(pbix),
                "dax_summary": {},
                "extraction_info": {
                    "total_measures": 0,
                    "total_calculated_columns": 0,
                    "total_calculated_tables": 0,
                    "tables_with_dax": set(),
                },
            }

            # Calculate summary statistics
            self._calculate_dax_summary(results)

            self.logger.info(
                f"DAX extraction complete: {results['extraction_info']['total_measures']} measures, {results['extraction_info']['total_calculated_columns']} calculated columns"
            )
            return results

        except Exception as e:
            self.logger.error(f"DAX extraction failed: {e}")
            raise

    def _extract_measures(self, pbix: PBIXRay) -> List[Dict[str, Any]]:
        """Extract DAX measures."""
        measures = []

        try:
            measures_df = pbix.dax_measures

            if not measures_df.empty:
                for _, row in measures_df.iterrows():
                    measure = {
                        "table": row.get("TableName", ""),
                        "name": row.get("Name", ""),
                        "expression": row.get("Expression", "").strip(),
                        "description": row.get("Description", ""),
                        "format_string": row.get("FormatString", ""),
                        "is_hidden": row.get("IsHidden", False),
                        "display_folder": row.get("DisplayFolder", ""),
                        "data_type": row.get("DataType", "Variant"),
                    }

                    # Analyze DAX expression
                    measure.update(self._analyze_dax_expression(measure["expression"]))

                    measures.append(measure)

        except Exception as e:
            self.logger.warning(f"Could not extract DAX measures: {e}")

        return measures

    def _extract_calculated_columns(self, pbix: PBIXRay) -> List[Dict[str, Any]]:
        """Extract calculated columns."""
        calculated_columns = []

        try:
            columns_df = pbix.dax_columns

            if not columns_df.empty:
                for _, row in columns_df.iterrows():
                    column = {
                        "table": row.get("TableName", ""),
                        "name": row.get("ColumnName", ""),
                        "expression": row.get("Expression", "").strip(),
                        "data_type": row.get("DataType", ""),
                        "format_string": row.get("FormatString", ""),
                        "is_hidden": row.get("IsHidden", False),
                        "description": row.get("Description", ""),
                        "display_folder": row.get("DisplayFolder", ""),
                    }

                    # Analyze DAX expression
                    column.update(self._analyze_dax_expression(column["expression"]))

                    calculated_columns.append(column)

        except Exception as e:
            self.logger.warning(f"Could not extract calculated columns: {e}")

        return calculated_columns

    def _extract_calculated_tables(self, pbix: PBIXRay) -> List[Dict[str, Any]]:
        """Extract calculated tables."""
        calculated_tables = []

        try:
            tables_df = pbix.dax_tables

            if not tables_df.empty:
                for _, row in tables_df.iterrows():
                    table = {
                        "name": row.get("TableName", ""),
                        "expression": row.get("Expression", "").strip(),
                        "description": row.get("Description", ""),
                        "is_hidden": row.get("IsHidden", False),
                    }

                    # Analyze DAX expression
                    table.update(self._analyze_dax_expression(table["expression"]))

                    calculated_tables.append(table)

        except Exception as e:
            self.logger.warning(f"Could not extract calculated tables: {e}")

        return calculated_tables

    def _analyze_dax_expression(self, expression: str) -> Dict[str, Any]:
        """
        Analyze a DAX expression to extract metadata.

        Args:
            expression: The DAX expression string

        Returns:
            Dictionary with analysis results
        """
        if not expression:
            return {
                "expression_length": 0,
                "function_count": 0,
                "referenced_tables": [],
                "referenced_columns": [],
                "complexity_score": 0,
                "contains_time_intelligence": False,
                "contains_filter_functions": False,
            }

        expression_upper = expression.upper()

        # Count DAX functions (basic heuristic)
        dax_functions = [
            "SUM",
            "COUNT",
            "AVERAGE",
            "MAX",
            "MIN",
            "CALCULATE",
            "FILTER",
            "ALL",
            "ALLEXCEPT",
            "SUMX",
            "COUNTX",
            "AVERAGEX",
            "MAXX",
            "MINX",
            "IF",
            "SWITCH",
            "AND",
            "OR",
            "NOT",
            "RELATED",
            "RELATEDTABLE",
            "LOOKUPVALUE",
            "EARLIER",
            "EARLIEST",
            "VALUES",
            "DISTINCT",
            "BLANK",
            "ISBLANK",
            "ISERROR",
            "HASONEVALUE",
            "SELECTEDVALUE",
            "CONCATENATE",
            "FORMAT",
            "YEAR",
            "MONTH",
            "DAY",
            "DATE",
            "TODAY",
            "NOW",
            "DATEDIFF",
            "DATEADD",
            "TOTALYTD",
            "TOTALQTD",
            "TOTALMTD",
            "SAMEPERIODLASTYEAR",
            "PARALLELPERIOD",
            "DATESINPERIOD",
        ]

        function_count = sum(1 for func in dax_functions if func in expression_upper)

        # Time intelligence functions
        time_intelligence_functions = [
            "TOTALYTD",
            "TOTALQTD",
            "TOTALMTD",
            "SAMEPERIODLASTYEAR",
            "PARALLELPERIOD",
            "DATESINPERIOD",
            "DATESYTD",
            "DATESQTD",
            "DATESMTD",
            "PREVIOUSDAY",
            "PREVIOUSMONTH",
        ]
        contains_time_intelligence = any(
            func in expression_upper for func in time_intelligence_functions
        )

        # Filter functions
        filter_functions = ["FILTER", "ALL", "ALLEXCEPT", "CALCULATE", "CALCULATETABLE"]
        contains_filter_functions = any(func in expression_upper for func in filter_functions)

        # Extract table references (basic pattern matching)
        referenced_tables = self._extract_table_references(expression)
        referenced_columns = self._extract_column_references(expression)

        # Calculate complexity score (basic heuristic)
        complexity_score = (
            len(expression) / 100  # Length factor
            + function_count * 2  # Function complexity
            + expression.count("(")  # Nesting level
            + len(referenced_tables)  # Table dependencies
        )

        return {
            "expression_length": len(expression),
            "function_count": function_count,
            "referenced_tables": referenced_tables,
            "referenced_columns": referenced_columns,
            "complexity_score": round(complexity_score, 2),
            "contains_time_intelligence": contains_time_intelligence,
            "contains_filter_functions": contains_filter_functions,
        }

    def _extract_table_references(self, expression: str) -> List[str]:
        """Extract table references from DAX expression."""
        import re

        # Pattern to match table references like 'TableName'[Column] or TableName[Column]
        table_pattern = r"'?([A-Za-z][A-Za-z0-9\s_]*)'?\["
        matches = re.findall(table_pattern, expression)

        # Clean and deduplicate
        tables = list(set(match.strip() for match in matches if match.strip()))
        return tables

    def _extract_column_references(self, expression: str) -> List[str]:
        """Extract column references from DAX expression."""
        import re

        # Pattern to match column references like [ColumnName]
        column_pattern = r"\[([A-Za-z][A-Za-z0-9\s_]*)\]"
        matches = re.findall(column_pattern, expression)

        # Clean and deduplicate
        columns = list(set(match.strip() for match in matches if match.strip()))
        return columns

    def _calculate_dax_summary(self, results: Dict[str, Any]) -> None:
        """Calculate summary statistics for DAX extraction."""
        # Count totals
        results["extraction_info"]["total_measures"] = len(results["measures"])
        results["extraction_info"]["total_calculated_columns"] = len(results["calculated_columns"])
        results["extraction_info"]["total_calculated_tables"] = len(results["calculated_tables"])

        # Track tables with DAX
        tables_with_dax = set()

        for measure in results["measures"]:
            if measure["table"]:
                tables_with_dax.add(measure["table"])

        for column in results["calculated_columns"]:
            if column["table"]:
                tables_with_dax.add(column["table"])

        for table in results["calculated_tables"]:
            if table["name"]:
                tables_with_dax.add(table["name"])

        results["extraction_info"]["tables_with_dax"] = list(tables_with_dax)

        # Calculate complexity statistics
        all_expressions = (
            [m["expression"] for m in results["measures"]]
            + [c["expression"] for c in results["calculated_columns"]]
            + [t["expression"] for t in results["calculated_tables"]]
        )

        if all_expressions:
            complexity_scores = [
                self._analyze_dax_expression(expr)["complexity_score"]
                for expr in all_expressions
                if expr
            ]

            if complexity_scores:
                results["dax_summary"] = {
                    "avg_complexity": round(sum(complexity_scores) / len(complexity_scores), 2),
                    "max_complexity": max(complexity_scores),
                    "min_complexity": min(complexity_scores),
                    "total_expressions": len(all_expressions),
                    "expressions_with_time_intelligence": sum(
                        1
                        for expr in all_expressions
                        if self._analyze_dax_expression(expr)["contains_time_intelligence"]
                    ),
                    "expressions_with_filters": sum(
                        1
                        for expr in all_expressions
                        if self._analyze_dax_expression(expr)["contains_filter_functions"]
                    ),
                }

    def extract_measures_by_table(self) -> Dict[str, List[Dict[str, Any]]]:
        """Extract measures grouped by table."""
        try:
            all_dax = self.extract_all_dax()
            measures_by_table = {}

            for measure in all_dax["measures"]:
                table_name = measure["table"] or "Unknown"
                if table_name not in measures_by_table:
                    measures_by_table[table_name] = []
                measures_by_table[table_name].append(measure)

            return measures_by_table

        except Exception as e:
            self.logger.error(f"Could not extract measures by table: {e}")
            return {}

    def get_dax_summary(self) -> Dict[str, Any]:
        """Get a quick summary of DAX components."""
        try:
            dax_data = self.extract_all_dax()

            return {
                "total_measures": len(dax_data.get("measures", [])),
                "total_calculated_columns": len(dax_data.get("calculated_columns", [])),
                "total_calculated_tables": len(dax_data.get("calculated_tables", [])),
                "tables_with_dax": dax_data.get("extraction_info", {}).get("tables_with_dax", []),
                "complexity_summary": dax_data.get("dax_summary", {}),
            }
        except Exception as e:
            self.logger.error(f"Could not get DAX summary: {e}")
            return {"error": str(e)}
