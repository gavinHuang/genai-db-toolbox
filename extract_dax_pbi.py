import os
import argparse
import sys
from pbixray import PBIXRay
import pandas as pd  # Optional, for nicer output

def extract_dax_from_pbix(pbix_path, output_dir, quiet=False, no_file=False):
    # Initialize pbixray
    model = PBIXRay(pbix_path)
    
    # Extract measures (DAX expressions)
    measures_df = model.dax_measures
    measures = []
    if not measures_df.empty:
        for _, row in measures_df.iterrows():
            measures.append({
                'table': row['TableName'],
                'name': row['Name'],
                'dax': row['Expression'].strip()
            })
    
    # Extract calculated columns (DAX expressions)
    columns_df = model.dax_columns
    calc_columns = []
    if not columns_df.empty:
        for _, row in columns_df.iterrows():
            calc_columns.append({
                'table': row['TableName'],
                'name': row['ColumnName'],
                'dax': row['Expression'].strip()
            })
    
    # Extract calculated tables (DAX expressions)
    tables_df = model.dax_tables
    calc_tables = []
    if not tables_df.empty:
        for _, row in tables_df.iterrows():
            calc_tables.append({
                'table': row['TableName'],
                'dax': row['Expression'].strip()
            })
    
    # Print results
    if not quiet:
        print("Measures:")
        for m in measures:
            print(f"Table: {m['table']}\nName: {m['name']}\nDAX: {m['dax']}\n---")
        
        print("\nCalculated Columns:")
        for c in calc_columns:
            print(f"Table: {c['table']}\nName: {c['name']}\nDAX: {c['dax']}\n---")
        
        print("\nCalculated Tables:")
        for t in calc_tables:
            print(f"Table: {t['table']}\nDAX: {t['dax']}\n---")
    
    # Optionally save to file
    if not no_file:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, 'dax_expressions.txt'), 'w', encoding='utf-8') as f:
            f.write("Measures:\n")
            for m in measures:
                f.write(f"Table: {m['table']}\nName: {m['name']}\nDAX: {m['dax']}\n---\n")
            f.write("\nCalculated Columns:\n")
            for c in calc_columns:
                f.write(f"Table: {c['table']}\nName: {c['name']}\nDAX: {c['dax']}\n---\n")
            f.write("\nCalculated Tables:\n")
            for t in calc_tables:
                f.write(f"Table: {t['table']}\nDAX: {t['dax']}\n---\n")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Extract DAX expressions from Power BI (.pbix) files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s report.pbix
  %(prog)s report.pbix -o output_folder
  %(prog)s report.pbix --output-dir ./dax_output --quiet
        '''
    )
    
    parser.add_argument(
        'pbix_file',
        help='Path to the .pbix file to extract DAX from'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='extracted_pbix_dax',
        help='Directory to save the extracted DAX expressions (default: extracted_pbix_dax)'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress console output, only save to file'
    )
    
    parser.add_argument(
        '--no-file',
        action='store_true',
        help='Do not save to file, only print to console'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.pbix_file):
        print(f"Error: File '{args.pbix_file}' not found.", file=sys.stderr)
        sys.exit(1)
    
    if not args.pbix_file.lower().endswith('.pbix'):
        print(f"Warning: '{args.pbix_file}' does not have a .pbix extension.", file=sys.stderr)
    
    # Extract DAX expressions
    try:
        extract_dax_from_pbix(args.pbix_file, args.output_dir, args.quiet, args.no_file)
        if not args.quiet:
            if not args.no_file:
                print(f"\nDAX expressions saved to: {os.path.join(args.output_dir, 'dax_expressions.txt')}")
            print("Extraction completed successfully!")
    except Exception as e:
        print(f"Error extracting DAX from '{args.pbix_file}': {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()