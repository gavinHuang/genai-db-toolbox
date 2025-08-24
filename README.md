# PBIX to MCP Converter

Convert Power BI (.pbix) files into Model Context Protocol (MCP) servers using Google's genai-toolbox.

## Background

The pain point of any SQL generation solutions based on text2sql, either they are agentic or RAG, remain the same: they are depends on LLM which is non-deterministic! While they create greate applications, it raise the question whether the dynamically generated queries (effectively code) are acurate therefore the results from these query can be trusted or not.

Having been working on data domain for ages, my idea is to make best use of existing powerbi reports (tested code!) rather than dynamic generate query (image using a system with code generated on the fly!).

This tool do three things:

- Extract necessary information from powerbi reports (Thanks to `pbixray`)
- Convert to a yaml file according to Google's `genai-toolbox`
- Run `genai-toolbox` to get a MCP server, which you can connect to with any MCP-supported assistant client 

`genai-toolbox` allows you to pregenerated sql queries and expose them as MCP tool. So instead have LLM do everything: generate correct query, correct parameter, it now only need to make sure call the right tool, whose result can be easily spotted and evaluated. 

## Features

- **Complete Data Extraction**: Extract data models, tables, relationships, and schema information
- **DAX Analysis**: Parse DAX measures, calculated columns, and calculated tables with complexity analysis
- **UI Structure**: Extract report pages, visualizations, bookmarks, and layout information
- **SQLite Database**: Generate SQLite databases from embedded Power BI data
- **MCP Configuration**: Create genai-toolbox compatible YAML configurations
- **Modular Architecture**: Clean, extensible codebase for custom integrations

## Quick Start

Here's an example of what this tool can extract from a Power BI report:

![Power BI Supply Chain Dashboard](images/powerbi-supplier-chain.png)

*Original Power BI dashboard with complex visualizations and data relationships*

The tool converts this into a comprehensive MCP server with dozens of specialized tools:

![MCP Tools Generated](images/mcp-tools.png)

*Generated MCP tools that provide programmatic access to all Power BI data and analytics*

Once configured, you can interact with your Power BI data through natural language in any MCP-compatible chat interface:

![MCP in Chat Usage](images/mcp-in-chat.png)

*Example of using the MCP tools in a chat interface to query Power BI data naturally*

### Installation

```bash
pip install pbix-to-mcp
```

### Basic Usage

```bash
# Convert a Power BI file to MCP server
pbix-to-mcp report.pbix

# Generate complete package
pbix-to-mcp report.pbix --complete-package

# Custom output directory and configuration
pbix-to-mcp report.pbix -o my_output --config-name my_mcp.yaml
```

### Using the MCP Server

1. **Install Google's genai-toolbox**:
   ```bash
   # Download from releases page
   export VERSION=0.12.0
   curl -O https://storage.googleapis.com/genai-toolbox/v$VERSION/linux/amd64/toolbox
   chmod +x toolbox
   ```

2. **Start the MCP server**:
   ```bash
   ./toolbox --tools-file supply_chain_mcp.yaml
   ```
   
   > **Important**: Ensure the database path in the YAML config is correct for your environment. If running from a different directory, you may need to update the database path to be absolute or correctly relative.

3. **Connect from your MCP client**:
   ```json
   {
     "servers": {
       "powerbi-mcp": {
         "url": "http://localhost:5000/mcp",
         "headers": {}
       }
     }
   }
   ```

## Library Usage

```python
from pbix_to_mcp import PBIXConverter

# Initialize converter
converter = PBIXConverter("report.pbix")

# Extract all components
results = converter.extract_all()

# Generate MCP configuration
config_path = converter.generate_mcp_config("my_config.yaml")

# Generate complete package
package_files = converter.generate_complete_package()
```

## Generated Tools

The converter creates comprehensive tool sets for interacting with your Power BI data:

### Core Database Tools
- `execute_sql`: Execute arbitrary SQL queries
- `list_powerbi_tables`: List all available tables
- `describe_powerbi_table`: Get table schema information
- `count_table_records`: Count records in any table
- `get_table_sample`: Get sample data from tables

### DAX Analysis Tools
- `get_dax_measures`: Access DAX measure definitions
- `search_dax_expressions`: Search through DAX code
- `get_dax_complexity_analysis`: Analyze DAX complexity metrics

### UI Structure Tools
- `get_report_pages`: Access report page information
- `get_visualizations_by_type`: Query visualization metadata
- `get_page_visual_layout`: Get detailed visual layouts

### Data-Specific Tools
- Table-specific analysis tools based on your data
- Aggregation queries for key metrics
- Relationship navigation helpers

## Command Line Options

```bash
pbix-to-mcp report.pbix [options]

Options:
  -o, --output-dir DIR        Output directory
  --config-name NAME          MCP config file name
  --skip-data                 Skip data model extraction
  --skip-ui                   Skip UI structure extraction
  --skip-dax                  Skip DAX expressions extraction
  --data-limit N              Maximum rows per table (default: 10000)
  --complete-package          Generate complete deployment package
  --package-name NAME         Package directory name
  -v, --verbose               Enable verbose logging
  -q, --quiet                 Suppress console output
  --log-file FILE             Save logs to file
```

## Output Structure

```
report_mcp/
├── data/
│   └── powerbi_data.db          # SQLite database with all data
├── report_mcp_config.yaml       # MCP server configuration
├── extraction_results.json      # Complete extraction metadata
├── conversion.log               # Detailed processing log
└── README.md                    # Generated documentation
```

## Advanced Usage

### Custom Extraction

```python
from pbix_to_mcp.extractors import DataExtractor, UIExtractor, DAXExtractor

# Extract specific components
data_extractor = DataExtractor("report.pbix")
data_model = data_extractor.extract_data_model(data_limit=5000)

ui_extractor = UIExtractor("report.pbix")
ui_structure = ui_extractor.extract_ui_structure()

dax_extractor = DAXExtractor("report.pbix")
dax_expressions = dax_extractor.extract_all_dax()
```

### Custom MCP Configuration

```python
from pbix_to_mcp.generators import MCPConfigGenerator

generator = MCPConfigGenerator(output_dir)
config_path = generator.generate_config(
    extraction_results,
    config_name="custom_config.yaml",
    toolsets=["basic-analysis", "dax-analysis"]
)
```

## Requirements

- Python 3.10+
- pbixray>=0.3.3
- pandas>=1.5.0
- pyyaml>=6.0
- Google's genai-toolbox (for running MCP server)

## Development

```bash
# Clone repository
git clone https://github.com/gavinHuang/pbix-to-mcp.git
cd pbix-to-mcp

# Install in development mode
pip install -e .[dev]

# Run tests
pytest

# Format code
black pbix_to_mcp/
isort pbix_to_mcp/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if needed
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](https://github.com/gavinHuang/pbix-to-mcp/wiki)
- 🐛 [Issue Tracker](https://github.com/gavinHuang/pbix-to-mcp/issues)
- 💬 [Discussions](https://github.com/gavinHuang/pbix-to-mcp/discussions)

## Acknowledgments

- Built on [pbixray](https://github.com/pbixray/pbixray) for Power BI file parsing
- Integrates with [Google's genai-toolbox](https://github.com/google/genai-toolbox) for MCP servers
- Inspired by the Model Context Protocol specification