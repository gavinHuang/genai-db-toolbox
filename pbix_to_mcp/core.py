"""
Core PBIX to MCP Converter Class

Main orchestrator class that coordinates all extraction and generation processes.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .extractors.data_extractor import DataExtractor
from .extractors.dax_extractor import DAXExtractor
from .extractors.ui_extractor import UIExtractor
from .generators.mcp_config_generator import MCPConfigGenerator
from .generators.sqlite_generator import SQLiteGenerator
from .utils.file_manager import FileManager
from .utils.logger import setup_logger


class PBIXConverter:
    """
    Main converter class that orchestrates the conversion of PBIX files to MCP servers.

    This class coordinates all extraction processes and generates the necessary
    outputs for genai-toolbox MCP server integration.
    """

    def __init__(self, pbix_path: str, output_dir: Optional[str] = None):
        """
        Initialize the PBIX converter.

        Args:
            pbix_path: Path to the .pbix file
            output_dir: Output directory (defaults to {pbix_name}_mcp)
        """
        self.pbix_path = Path(pbix_path)
        self.pbix_name = self.pbix_path.stem

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(f"{self.pbix_name}_mcp")

        self.output_dir.mkdir(exist_ok=True)

        # Setup logging
        self.logger = setup_logger(
            name=f"pbix_converter_{self.pbix_name}", log_file=self.output_dir / "conversion.log"
        )

        # Initialize components
        self.file_manager = FileManager(self.output_dir)
        self.data_extractor = DataExtractor(self.pbix_path)
        self.ui_extractor = UIExtractor(self.pbix_path)
        self.dax_extractor = DAXExtractor(self.pbix_path)
        self.sqlite_generator = SQLiteGenerator(self.output_dir)
        self.mcp_generator = MCPConfigGenerator(self.output_dir)

        # Extraction results
        self.extraction_results: Dict[str, Any] = {}

    def extract_all(
        self,
        extract_data: bool = True,
        extract_ui: bool = True,
        extract_dax: bool = True,
        data_limit: int = 10000,
    ) -> Dict[str, Any]:
        """
        Extract all components from the PBIX file.

        Args:
            extract_data: Extract table data and schema
            extract_ui: Extract UI structure (pages, visuals)
            extract_dax: Extract DAX expressions
            data_limit: Maximum rows per table to extract

        Returns:
            Dictionary containing all extraction results
        """
        self.logger.info(f"Starting complete extraction of {self.pbix_path}")

        results = {
            "pbix_file": str(self.pbix_path),
            "output_directory": str(self.output_dir),
            "extraction_summary": {},
            "data_model": {},
            "ui_structure": {},
            "dax_expressions": {},
            "files_created": [],
        }

        try:
            # Extract data model and tables
            if extract_data:
                self.logger.info("Extracting data model...")
                data_results = self.data_extractor.extract_data_model(data_limit)
                results["data_model"] = data_results
                results["extraction_summary"]["data_model"] = "✅ Complete"

                # Generate SQLite database
                if data_results.get("tables"):
                    # Pass the complete structure to SQLite generator
                    sqlite_input = {"data_model": data_results, "pbix_file": str(self.pbix_path)}
                    db_path = self.sqlite_generator.create_database(sqlite_input)
                    results["files_created"].append(str(db_path))
                    self.logger.info(f"SQLite database created: {db_path}")
            else:
                results["extraction_summary"]["data_model"] = "⏭️ Skipped"

            # Extract UI structure
            if extract_ui:
                self.logger.info("Extracting UI structure...")
                ui_results = self.ui_extractor.extract_ui_structure()
                results["ui_structure"] = ui_results
                results["extraction_summary"]["ui_structure"] = "✅ Complete"
            else:
                results["extraction_summary"]["ui_structure"] = "⏭️ Skipped"

            # Extract DAX expressions
            if extract_dax:
                self.logger.info("Extracting DAX expressions...")
                dax_results = self.dax_extractor.extract_all_dax()
                results["dax_expressions"] = dax_results
                results["extraction_summary"]["dax_expressions"] = "✅ Complete"
            else:
                results["extraction_summary"]["dax_expressions"] = "⏭️ Skipped"

            # Save combined results
            results_file = self.file_manager.save_json(results, "extraction_results.json")
            results["files_created"].append(str(results_file))

            # Store results for MCP generation
            self.extraction_results = results

            self.logger.info("Extraction completed successfully")
            return results

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            results["extraction_summary"]["error"] = str(e)
            raise

    def generate_mcp_config(
        self, config_name: Optional[str] = None, toolsets: Optional[List[str]] = None
    ) -> str:
        """
        Generate MCP configuration YAML file for genai-toolbox.

        Args:
            config_name: Name for the YAML config file
            toolsets: List of toolset names to include

        Returns:
            Path to generated config file
        """
        if not self.extraction_results:
            raise ValueError("No extraction results available. Run extract_all() first.")

        if not config_name:
            config_name = f"{self.pbix_name}_mcp_config.yaml"

        self.logger.info(f"Generating MCP configuration: {config_name}")

        config_path = self.mcp_generator.generate_config(
            extraction_results=self.extraction_results, config_name=config_name, toolsets=toolsets
        )

        # Store the config path to avoid regenerating
        self._config_path = str(config_path)

        self.logger.info(f"MCP configuration generated: {config_path}")
        return str(config_path)

    def generate_complete_package(
        self, package_name: Optional[str] = None, include_sample_data: bool = True
    ) -> Dict[str, str]:
        """
        Generate a complete MCP package ready for deployment.

        Args:
            package_name: Name for the package directory
            include_sample_data: Include sample data in outputs

        Returns:
            Dictionary of generated files and their paths
        """
        if not package_name:
            package_name = f"{self.pbix_name}_mcp_package"

        self.logger.info(f"Generating complete MCP package: {package_name}")

        # Extract everything if not done already
        if not self.extraction_results:
            self.extract_all()

        # Generate MCP config if not already generated
        if hasattr(self, "_config_path") and self._config_path:
            config_path = self._config_path
            self.logger.info(f"Using existing MCP configuration: {config_path}")
        else:
            config_path = self.generate_mcp_config()

        # Generate documentation
        docs = self._generate_documentation()

        # Create package structure
        package_dir = self.output_dir / package_name
        package_dir.mkdir(exist_ok=True)

        # Copy essential files
        package_files = {
            "config": str(config_path),
            "database": str(self.output_dir / "data" / "powerbi_data.db"),
            "documentation": str(self.file_manager.save_text(docs, "README.md")),
            "extraction_log": str(self.output_dir / "conversion.log"),
        }

        self.logger.info(f"Complete MCP package generated at: {package_dir}")
        return package_files

    def _generate_documentation(self) -> str:
        """Generate README documentation for the MCP package."""
        doc_lines = [
            f"# {self.pbix_name} MCP Server",
            "",
            f"Power BI file converted to Model Context Protocol server using pbix-to-mcp.",
            "",
            "## Quick Start",
            "",
            "1. Install Google's genai-toolbox:",
            "```bash",
            "# Download from releases page",
            "curl -O https://storage.googleapis.com/genai-toolbox/v0.12.0/linux/amd64/toolbox",
            "chmod +x toolbox",
            "```",
            "",
            "2. Start the MCP server:",
            "```bash",
            f"./toolbox --tools-file {self.pbix_name}_mcp_config.yaml",
            "```",
            "",
            "3. Connect from your MCP client using:",
            "```json",
            "{",
            '  "servers": {',
            f'    "{self.pbix_name}-mcp": {{',
            '      "url": "http://localhost:5000/mcp",',
            '      "headers": {}',
            "    }",
            "  }",
            "}",
            "```",
            "",
            "## Available Tools",
            "",
        ]

        # Add tool documentation
        if self.extraction_results.get("data_model", {}).get("tables"):
            doc_lines.extend(
                [
                    "### Data Query Tools",
                    "- `execute_sql`: Execute arbitrary SQL queries",
                    "- `list_tables`: List all available tables",
                    "- `describe_table`: Get table schema information",
                    "- `count_records`: Count records in any table",
                    "- `get_table_sample`: Get sample data from tables",
                    "",
                ]
            )

        if self.extraction_results.get("dax_expressions", {}).get("measures"):
            doc_lines.extend(
                [
                    "### DAX Analysis Tools",
                    "- `get_dax_measures`: Access DAX measure definitions",
                    "- `search_dax_expressions`: Search through DAX code",
                    "",
                ]
            )

        if self.extraction_results.get("ui_structure", {}).get("pages"):
            doc_lines.extend(
                [
                    "### UI Structure Tools",
                    "- `get_report_pages`: Access report page information",
                    "- `get_visualizations`: Query visualization metadata",
                    "",
                ]
            )

        doc_lines.extend(
            [
                "## Database Schema",
                "",
                f"The SQLite database contains {len(self.extraction_results.get('data_model', {}).get('tables', []))} tables:",
            ]
        )

        for table in self.extraction_results.get("data_model", {}).get("tables", []):
            doc_lines.append(
                f"- `{table.get('name', 'unknown')}`: {len(table.get('columns', []))} columns"
            )

        doc_lines.extend(
            [
                "",
                "## Generated Files",
                "",
                "- `powerbi_data.db`: SQLite database with extracted data",
                f"- `{self.pbix_name}_mcp_config.yaml`: MCP server configuration",
                "- `extraction_results.json`: Complete extraction metadata",
                "- `conversion.log`: Detailed processing log",
                "",
                f"Generated from: `{self.pbix_path.name}`",
                f"Conversion tool: pbix-to-mcp v{self.__class__.__module__.split('.')[0] if hasattr(self.__class__, '__module__') else '0.1.0'}",
            ]
        )

        return "\n".join(doc_lines)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversion results."""
        if not self.extraction_results:
            return {"status": "No extraction performed"}

        summary = {
            "source_file": str(self.pbix_path),
            "output_directory": str(self.output_dir),
            "extraction_status": self.extraction_results.get("extraction_summary", {}),
            "data_tables": len(self.extraction_results.get("data_model", {}).get("tables", [])),
            "dax_measures": len(
                self.extraction_results.get("dax_expressions", {}).get("measures", [])
            ),
            "ui_pages": len(self.extraction_results.get("ui_structure", {}).get("pages", [])),
            "visualizations": len(
                self.extraction_results.get("ui_structure", {}).get("visualizations", [])
            ),
            "files_created": len(self.extraction_results.get("files_created", [])),
        }

        return summary
