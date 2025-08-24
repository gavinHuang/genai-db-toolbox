import asyncio
import json
from toolbox_core import ToolboxClient

def print_table_info(tables):
    """Pretty print table information"""
    print("=" * 80)
    print(f"📊 DATABASE SCHEMA - Found {len(tables)} tables")
    print("=" * 80)
    
    for i, table in enumerate(tables, 1):
        print(f"\n🗂️  TABLE {i}: {table['table_name'].upper()}")
        print("-" * 60)
        print(f"Object Type: {table['object_type']}")
        print(f"Table Name: {table['table_name']}")
        print("\n📝 CREATE STATEMENT:")
        print(table['create_statement'])
        print("-" * 60)
    
    print(f"\n✅ Total tables processed: {len(tables)}")
    print("=" * 80)

def save_schema_to_file(tables, filename="database_schema.json"):
    """Save the schema to a JSON file for reference"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tables, f, indent=2, ensure_ascii=False)
    print(f"💾 Schema saved to {filename}")

async def main():
    # update the url to point to your server
    async with ToolboxClient("http://127.0.0.1:5000") as client:

        # these tools can be passed to your application!
        tools = await client.load_toolset("sqlite-basic-tools")

        for tool in tools:
            if tool._name == "list_tables":
                results = await tool()
                
                # Debug: Check the structure of results
                print(f"🔍 Results type: {type(results)}")
                
                # Parse the JSON string
                try:
                    if isinstance(results, str):
                        parsed_results = json.loads(results)
                        print(f"✅ Successfully parsed JSON. Found {len(parsed_results)} tables")
                        
                        # Pretty print the results
                        print_table_info(parsed_results)
                        
                        # Save to file for reference
                        save_schema_to_file(parsed_results)
                    else:
                        print("❌ Results is not a string, using as-is")
                        print_table_info(results)
                        save_schema_to_file(results)
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse JSON: {e}")
                    print(f"Raw results preview: {str(results)[:500]}...")
                
                # Also print raw JSON if needed (commented out by default)
                # print("\n🔍 RAW JSON OUTPUT:")
                # print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())