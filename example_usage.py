#!/usr/bin/env python3
"""
Example usage of the PBIX to MCP converter.

This script demonstrates how to use the pbix-to-mcp package to convert
a Power BI file into an MCP server configuration.
"""

import os
import sys
from pathlib import Path

# Add the package to the path if running from development
sys.path.insert(0, str(Path(__file__).parent))

from pbix_to_mcp import PBIXConverter


def main():
    """Example conversion process."""
    
    # Check if we have a PBIX file to work with
    pbix_file = "samples/supply_chain_sample.pbix"
    
    if not os.path.exists(pbix_file):
        print(f"❌ PBIX file not found: {pbix_file}")
        print("This example expects the 'Supply Chain Sample.pbix' file in the current directory.")
        return 1
    
    print(f"🚀 Converting {pbix_file} to MCP server...")
    
    try:
        # Initialize the converter
        converter = PBIXConverter(pbix_file, output_dir="supply_chain_mcp")
        
        # Extract all components
        print("📊 Extracting data model...")
        print("🎨 Extracting UI structure...")  
        print("🔢 Extracting DAX expressions...")
        
        results = converter.extract_all(
            extract_data=True,
            extract_ui=True,
            extract_dax=True,
            data_limit=5000  # Limit data for example
        )
        
        # Show extraction summary
        print("\n📋 EXTRACTION SUMMARY:")
        for component, status in results["extraction_summary"].items():
            print(f"   {component}: {status}")
        
        # Generate MCP configuration
        print("\n⚙️  Generating MCP configuration...")
        config_path = converter.generate_mcp_config("supply_chain_mcp.yaml")
        print(f"   Config saved: {config_path}")
        
        # Generate complete package
        print("\n📦 Generating complete MCP package...")
        package_files = converter.generate_complete_package("supply_chain_mcp_package")
        
        print("\n📁 PACKAGE FILES CREATED:")
        for file_type, file_path in package_files.items():
            print(f"   {file_type}: {file_path}")
        
        # Show final summary
        summary = converter.get_summary()
        print(f"\n✅ CONVERSION COMPLETE!")
        print(f"=" * 50)
        print(f"📊 Data tables: {summary['data_tables']}")
        print(f"📈 DAX measures: {summary['dax_measures']}")
        print(f"📄 UI pages: {summary['ui_pages']}")
        print(f"🎨 Visualizations: {summary['visualizations']}")
        print(f"📁 Files created: {summary['files_created']}")
        
        print(f"\n🚀 NEXT STEPS:")
        print(f"1. Download Google's genai-toolbox")
        print(f"2. Run: ./toolbox --tools-file supply_chain_mcp.yaml")
        print(f"3. Connect your MCP client to http://localhost:5000/mcp")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())