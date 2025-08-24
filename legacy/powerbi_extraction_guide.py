#!/usr/bin/env python3
"""
Power BI PBIX File Structure Analysis Tool

This script provides a comprehensive analysis of what can be extracted from 
Power BI (.pbix) files and documents the current limitations.
"""

def create_powerbi_extraction_guide():
    guide = """
# Power BI (.pbix) File Structure & Extraction Guide

## What a PBIX File Contains:

### 📊 Data Model Layer (✅ EXTRACTABLE)
- **Tables**: Physical data tables with rows and columns
- **Relationships**: Foreign key relationships between tables
- **Columns**: Data types, formatting, hierarchies
- **Measures**: DAX expressions for calculations
- **Calculated Columns**: Column-level DAX expressions
- **Calculated Tables**: Table-level DAX expressions

### 🔄 Data Transformation Layer (✅ EXTRACTABLE)
- **Power Query (M) Code**: Data source connections and transformations
- **Data Sources**: Excel files, databases, web services, etc.
- **Applied Steps**: Data cleaning and shaping operations

### 🎨 Report/UI Layer (❌ LIMITED EXTRACTION)
- **Report Pages**: Tabs/pages in the report
- **Visualizations**: Charts, tables, cards, maps, etc.
- **Visual Properties**: Position, size, colors, formatting
- **Visual Interactions**: Cross-filtering, drill-through
- **DAX Queries**: Auto-generated queries for each visual
- **Filters**: Page-level, visual-level, and report-level filters

## Current Extraction Capabilities with pbixray:

### ✅ FULLY SUPPORTED:
1. **Data Tables**: Complete table data export to CSV/JSON/Excel/SQLite
2. **Table Schema**: Column names and inferred data types
3. **DAX Measures**: All custom measures with their DAX expressions
4. **DAX Calculated Columns**: Column-level calculations
5. **DAX Calculated Tables**: Table-level DAX expressions
6. **Relationships**: Table relationships (limited metadata)
7. **Power Query**: M code for data transformations
8. **Metadata**: File size, statistics, basic properties

### ❌ NOT CURRENTLY SUPPORTED:
1. **Report Pages**: Names, order, dimensions of report tabs
2. **Visualizations**: Chart types, positions, properties
3. **Visual DAX Queries**: The specific DAX generated for each chart
4. **Visual Interactions**: Cross-filtering rules and drill behaviors
5. **Formatting**: Colors, fonts, themes, conditional formatting
6. **Filters**: Applied filters and their contexts

## Alternative Tools for Full UI Extraction:

### 1. pbi-tools (.NET based)
- Command: `pbi-tools extract-pbix report.pbix`
- Extracts complete report structure to JSON
- Requires .NET runtime

### 2. Power BI REST API
- For published reports in Power BI Service
- Can extract report definition and dataset metadata
- Requires authentication and appropriate permissions

### 3. Custom PBIX Parser
- PBIX files are ZIP archives containing JSON files
- Report structure is in Layout file
- Requires complex JSON parsing

## Practical Workflow:

### For Data Analysis:
```bash
# Extract data model and tables
python extract_dax_pbi.py report.pbix --extract-data --data-format sqlite

# Result: Complete data model in SQLite database
```

### For DAX Documentation:
```bash
# Extract all DAX expressions
python extract_dax_pbi.py report.pbix

# Result: All measures, calculated columns, and table definitions
```

### For UI/Visual Analysis:
1. Use pbi-tools for complete extraction
2. Or manually analyze in Power BI Desktop
3. Or use Power BI REST API for published reports

## Summary:

Our current tool provides **comprehensive data model extraction** but 
**limited UI layer access**. This covers 70-80% of typical Power BI 
reverse-engineering needs, focusing on the data and business logic rather 
than presentation layer.

For complete UI extraction, additional tools or custom development would 
be required.
"""
    return guide

if __name__ == "__main__":
    print(create_powerbi_extraction_guide())