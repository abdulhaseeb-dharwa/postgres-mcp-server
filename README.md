<<<<<<< HEAD
# postgres-mcp-server
MCP server for PostgreSQL: async pooling, schema describe, and safe query execution.
=======
# MCP PostgreSQL Server

A Model Context Protocol (MCP) server that provides PostgreSQL database connectivity through a standardized interface. This server allows AI assistants and other MCP clients to interact with PostgreSQL databases safely and efficiently.

## Features

- **Health Check**: Monitor database connectivity and response times
- **Table Description**: Get detailed schema information for database tables
- **SQL Query Execution**: Execute both read and write operations with safety controls
- **Connection Pooling**: Efficient database connection management using asyncpg
- **Security**: Built-in protection against unauthorized schema access and write operations
- **JSON Parsing**: Robust handling of malformed JSON from LLM responses

## Prerequisites

- Python 3.13 or higher
- PostgreSQL database
- MCP client (like Claude Desktop, etc.)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd mcp-postgres
```

2. Install dependencies using uv (recommended):
```bash
uv sync
```

Or using pip:
```bash
pip install -r requirements.txt
```

## Configuration

1. Create a `.env` file in the project root:
```env
PG_DSN=postgresql://username:password@localhost:5432/database_name
```

2. Replace the connection string with your actual PostgreSQL connection details.

## Usage

### Running the Server

Start the MCP server:

```bash
python server.py
```

The server will start and listen for MCP client connections via stdio transport.

### Available Tools

#### 1. Health Check (`ping`)
```python
# Returns connection status and response time
ping()
```

#### 2. Describe Table (`describe_table`)
```python
# Get table structure information
describe_table({
    "schema": "public",
    "table": "users"
})

# Or as a string
describe_table('{"schema": "public", "table": "users"}')
```

#### 3. Execute Query (`query`)
```python
# Read operation (default)
query(
    sql="SELECT * FROM users WHERE active = true",
    params={"active": True},
    role="read",
    limit=100
)

# Write operation
query(
    sql="INSERT INTO users (name, email) VALUES ($1, $2)",
    params={"name": "John Doe", "email": "john@example.com"},
    role="write"
)
```

### Security Features

- **Read-only by default**: Queries default to read-only mode
- **Schema restrictions**: Only the `public` schema is accessible
- **SQL injection protection**: Uses parameterized queries
- **Query limits**: Automatic LIMIT clauses for SELECT queries
- **Role-based access**: Separate read/write roles for different operations

### Supported SQL Operations

**Read Operations:**
- `SELECT` statements
- `SHOW` commands
- `EXPLAIN` queries
- `WITH` clauses (CTEs)

**Write Operations:**
- `INSERT` statements
- `UPDATE` statements
- `DELETE` statements
- `CREATE` statements
- `DROP` statements
- `ALTER` statements

## Development

### Project Structure

```
mcp-postgres/
├── server.py          # Main MCP server implementation
├── pyproject.toml    # Project configuration and dependencies
├── README.md         # This file
├── uv.lock           # Dependency lock file
├── .gitignore        # Git ignore rules
└── .env              # Environment variables (create this)
```

### Dependencies

- `asyncpg`: Async PostgreSQL driver
- `mcp[cli]`: Model Context Protocol framework
- `psycopg[binary]`: PostgreSQL adapter
- `pydantic`: Data validation
- `python-dotenv`: Environment variable management

### Adding New Tools

To add new MCP tools, use the `@mcp.tool()` decorator:

```python
@mcp.tool()
async def your_tool_name(param1: str, param2: int) -> Dict[str, Any]:
    """Tool description for the MCP client."""
    # Your implementation here
    return {"result": "success"}
```

## Error Handling

The server includes robust error handling for:
- Database connection issues
- SQL syntax errors
- Malformed JSON payloads
- Unauthorized operations
- Validation errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions, please open an issue on the project repository.
>>>>>>> 2ab2090 (Initial commit: MCP PostgreSQL Server)
