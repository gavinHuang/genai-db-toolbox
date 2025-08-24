#!/usr/bin/env python3
"""
Quick utility to explore PowerBI SQLite databases created by extract_dax_pbi.py
"""
import sqlite3
import argparse
import sys
import os

def explore_database(db_path):
    """Explore and display information about the PowerBI SQLite database"""
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found.")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get database info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 PowerBI SQLite Database: {db_path}")
        print(f"🗂️  Found {len(tables)} tables:")
        print("-" * 50)
        
        for table in tables:
            if table == '_extraction_metadata':
                # Show metadata
                cursor.execute("SELECT * FROM _extraction_metadata;")
                metadata = cursor.fetchone()
                if metadata:
                    print(f"📅 Extracted: {metadata[0]}")
                    print(f"📊 Total tables: {metadata[1]}, Total rows: {metadata[2]}")
                    print(f"🔧 Tool: {metadata[4]}")
                    print("-" * 50)
                continue
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`;")
            row_count = cursor.fetchone()[0]
            
            # Get column info
            cursor.execute(f"PRAGMA table_info(`{table}`);")
            columns = cursor.fetchall()
            
            print(f"Table: {table}")
            print(f"  Rows: {row_count:,}")
            print(f"  Columns: {len(columns)}")
            for col in columns[:5]:  # Show first 5 columns
                print(f"    - {col[1]} ({col[2]})")
            if len(columns) > 5:
                print(f"    ... and {len(columns) - 5} more columns")
            
            # Show sample data
            cursor.execute(f"SELECT * FROM `{table}` LIMIT 2;")
            sample_rows = cursor.fetchall()
            if sample_rows:
                print("  Sample data:")
                for i, row in enumerate(sample_rows, 1):
                    sample_values = [str(val)[:30] + "..." if isinstance(val, str) and len(str(val)) > 30 else str(val) for val in row[:3]]
                    print(f"    Row {i}: {sample_values}")
            print()
        
        conn.close()
        
    except Exception as e:
        print(f"Error exploring database: {e}")

def main():
    parser = argparse.ArgumentParser(description='Explore PowerBI SQLite databases')
    parser.add_argument('database', help='Path to the SQLite database file')
    
    args = parser.parse_args()
    explore_database(args.database)

if __name__ == "__main__":
    main()