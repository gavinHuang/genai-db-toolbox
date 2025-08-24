"""
Command-line interface for PBIX to MCP converter.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from pbix_to_mcp import PBIXConverter


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert Power BI (.pbix) files to MCP servers using Google's genai-toolbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s report.pbix
  %(prog)s report.pbix -o output_folder
  %(prog)s report.pbix --config-name my_mcp_config.yaml
  %(prog)s report.pbix --data-limit 1000 --skip-ui
  %(prog)s report.pbix --complete-package
        """,
    )

    # Required arguments
    parser.add_argument("pbix_file", help="Path to the .pbix file to convert")

    # Output options
    parser.add_argument("-o", "--output-dir", help="Output directory (default: {pbix_name}_mcp)")

    parser.add_argument(
        "--config-name", help="Name for the MCP config file (default: {pbix_name}_mcp_config.yaml)"
    )

    # Extraction options
    parser.add_argument("--skip-data", action="store_true", help="Skip data model extraction")

    parser.add_argument("--skip-ui", action="store_true", help="Skip UI structure extraction")

    parser.add_argument("--skip-dax", action="store_true", help="Skip DAX expressions extraction")

    parser.add_argument(
        "--data-limit",
        type=int,
        default=10000,
        help="Maximum rows to extract per table (default: 10000)",
    )

    # Package options
    parser.add_argument(
        "--complete-package",
        action="store_true",
        help="Generate a complete MCP package ready for deployment",
    )

    parser.add_argument(
        "--package-name", help="Name for the complete package (default: {pbix_name}_mcp_package)"
    )

    # Logging options
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress console output")

    parser.add_argument("--log-file", help="Save logs to file")

    # Parse arguments
    args = parser.parse_args()

    # Validate input file
    pbix_path = Path(args.pbix_file)
    if not pbix_path.exists():
        print(f"Error: File '{args.pbix_file}' not found.", file=sys.stderr)
        sys.exit(1)

    if not args.pbix_file.lower().endswith(".pbix"):
        print(f"Warning: '{args.pbix_file}' does not have a .pbix extension.", file=sys.stderr)

    # Set up logging
    log_level = logging.WARNING if args.quiet else (logging.DEBUG if args.verbose else logging.INFO)
    log_file = Path(args.log_file) if args.log_file else None

    # Initialize converter
    try:
        converter = PBIXConverter(args.pbix_file, args.output_dir)

        if not args.quiet:
            print(f"🚀 Starting conversion of: {pbix_path}")
            print(f"📁 Output directory: {converter.output_dir}")

        # Extract all components
        extract_data = not args.skip_data
        extract_ui = not args.skip_ui
        extract_dax = not args.skip_dax

        extraction_results = converter.extract_all(
            extract_data=extract_data,
            extract_ui=extract_ui,
            extract_dax=extract_dax,
            data_limit=args.data_limit,
        )

        # Generate MCP configuration
        config_path = converter.generate_mcp_config(config_name=args.config_name)

        if not args.quiet:
            print(f"✅ MCP configuration generated: {config_path}")

        # Generate complete package if requested
        if args.complete_package:
            package_files = converter.generate_complete_package(package_name=args.package_name)

            if not args.quiet:
                print(f"📦 Complete package generated:")
                for file_type, file_path in package_files.items():
                    print(f"   {file_type}: {file_path}")

        # Show summary
        if not args.quiet:
            summary = converter.get_summary()
            print(f"\n📊 CONVERSION SUMMARY")
            print(f"=" * 50)
            print(f"Source file: {summary['source_file']}")
            print(f"Data tables: {summary['data_tables']}")
            print(f"DAX measures: {summary['dax_measures']}")
            print(f"UI pages: {summary['ui_pages']}")
            print(f"Visualizations: {summary['visualizations']}")
            print(f"Files created: {summary['files_created']}")

            print(f"\n🚀 QUICK START")
            print(f"1. Download genai-toolbox from Google")
            print(f"2. Run: ./toolbox --tools-file {Path(config_path).name}")
            print(f"3. Connect your MCP client to http://localhost:5000/mcp")

        return 0

    except Exception as e:
        if args.verbose:
            import traceback

            traceback.print_exc()
        else:
            print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
