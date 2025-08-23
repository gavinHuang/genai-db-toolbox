# GenAI Toolbox

A Python project for working with Google's GenAI Toolbox and Model Context Protocol (MCP) servers.

## Installation

### 1. Install Google's GenAI Toolbox

```bash
# see releases page for other versions
export VERSION=0.12.0
curl -O https://storage.googleapis.com/genai-toolbox/v$VERSION/linux/amd64/toolbox
chmod +x toolbox
```

### 2. Start Server with Prepared Database and Config

Start the toolbox server with your prepared database and configuration files:

```bash
./toolbox --tools-file tools-sqlite.yaml
```

### 3. Use the MCP Server

Configure your MCP client to connect to the server using the following configuration:

```json
{
    "servers": {
        "my-mcp-server": {
            "url": "http://localhost:5000/mcp",
            "headers": {}
        }
    }
}
```

## Project Setup

This project uses UV for dependency management. The environment includes:

- `toolbox-core` - Core toolbox functionality
- Database tools for SQLite operations
- Async client for toolbox communication

### Development

```bash
# Sync dependencies
uv sync

# Run the test script
uv run verify_config.py

```

## Database Schema

The project works with a Chinook database containing 11 tables:
- Album, Artist, Customer, Employee, Genre
- Invoice, InvoiceLine, MediaType, Playlist, PlaylistTrack, Track

Run `verify_config.py` to view the complete database schema in a formatted output.

## Files

- `verify_config.py` - Main test script for database operations
- `database_schema.json` - Exported database schema (generated)
- `pyproject.toml` - Project configuration and dependencies
- `tools-sqlite.yaml` - Tool configuration files