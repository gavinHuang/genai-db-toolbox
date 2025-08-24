#!/bin/bash
# Quick verification script for MCP configuration

echo "🔍 Verifying MCP Configuration..."

CONFIG_FILE="../supply_chain_sample_mcp/supply_chain_sample_mcp_config.yaml"
DB_PATH="/mnt/d/GPT/genai-toolbox/supply_chain_sample_mcp/data/powerbi_data.db"

echo "📄 Config file: $CONFIG_FILE"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config file not found!"
    exit 1
fi
echo "✅ Config file exists"

echo "🗄️ Database file: $DB_PATH"
if [ ! -f "$DB_PATH" ]; then
    echo "❌ Database file not found!"
    exit 1
fi
echo "✅ Database file exists"

DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
echo "📊 Database size: $DB_SIZE"

echo "🚀 Ready to run: ./toolbox --tools-file $CONFIG_FILE"