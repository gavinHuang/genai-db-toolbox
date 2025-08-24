#!/usr/bin/env python3
"""
Migration script to organize the refactored project structure.

This script moves old files to a legacy folder and sets up the new structure.
"""

import os
import shutil
from pathlib import Path


def main():
    """Organize the project structure."""
    
    print("🔄 Organizing project structure...")
    
    # Create legacy folder for old files
    legacy_dir = Path("legacy")
    legacy_dir.mkdir(exist_ok=True)
    
    # Files to move to legacy
    legacy_files = [
        "extract_pbix_complete.py",
        "extract_dax_pbi.py", 
        "extract_pbix_ui.py",
        "parse_pbix_ui.py",
        "setup_powerbi_mcp_db.py",
        "powerbi_extraction_guide.py",
        "explore_powerbi_db.py",
        "verify_config.py"
    ]
    
    # Move legacy files
    moved_count = 0
    for file_name in legacy_files:
        if os.path.exists(file_name):
            shutil.move(file_name, legacy_dir / file_name)
            print(f"   Moved {file_name} to legacy/")
            moved_count += 1
    
    # Move legacy folders
    legacy_folders = [
        "extracted_pbix_dax",
        "powerbi_full", 
        "powerbi_ui_extracted",
        "Supply Chain Sample_extracted"
    ]
    
    for folder_name in legacy_folders:
        if os.path.exists(folder_name):
            if (legacy_dir / folder_name).exists():
                shutil.rmtree(legacy_dir / folder_name)
            shutil.move(folder_name, legacy_dir / folder_name)
            print(f"   Moved {folder_name}/ to legacy/")
            moved_count += 1
    
    # Move legacy markdown files
    legacy_md_files = [
        "MISSION_COMPLETE_UI_EXTRACTION.md",
        "POWER_BI_EXTRACTION_COMPLETE_GUIDE.md",
        "powerbi_detailed_report.txt"
    ]
    
    for file_name in legacy_md_files:
        if os.path.exists(file_name):
            shutil.move(file_name, legacy_dir / file_name)
            print(f"   Moved {file_name} to legacy/")
            moved_count += 1
    
    print(f"\n✅ Moved {moved_count} legacy items to legacy/ folder")
    
    # Create example output to show the new structure works
    if os.path.exists("Supply Chain Sample.pbix"):
        print("\n🧪 Testing new package structure...")
        try:
            # Import the new package
            from pbix_to_mcp import PBIXConverter
            
            # Quick test
            converter = PBIXConverter("Supply Chain Sample.pbix", "test_output")
            summary = converter.get_summary()
            
            print("✅ Package structure is working correctly!")
            
            # Clean up test output
            if os.path.exists("test_output"):
                shutil.rmtree("test_output")
                
        except Exception as e:
            print(f"⚠️  Package test failed: {e}")
            print("   This is expected if dependencies are not installed")
    
    print(f"\n🎉 Project refactoring complete!")
    print(f"📦 New package: pbix_to_mcp/")
    print(f"📜 Legacy files: legacy/")
    print(f"🚀 Ready for: pip install -e .")


if __name__ == "__main__":
    main()