import os
import json
import logging
import time
import re
from typing import Literal, Optional, Any, Dict, List, Union

import asyncpg
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("postgres-mcp-async")

# --------------------
# Async Postgres Pool
# --------------------
PG_DSN = os.environ["PG_DSN"]
pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(dsn=PG_DSN, min_size=1, max_size=10)
    return pool


# --------------------
# Utility Functions
# --------------------
def redact(sql: str) -> str:
    return sql.replace("\n", " ").strip()


def parse_malformed_json(json_str: str) -> Dict[str, Any]:
    """Parse potentially malformed JSON string from LLM with fixes"""
    if not json_str or not isinstance(json_str, str):
        return {}
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            fixed = json_str.replace("'", '"')
            fixed = re.sub(
                r':\s*([a-zA-Z_][\w.-]*)\s*([,}])', r': "\1"\2', fixed)
            fixed = re.sub(r',\s*}', '}', fixed)
            fixed = re.sub(r',\s*]', ']', fixed)
            return json.loads(fixed)
        except Exception:
            # fallback: parse manually
            result = {}
            content = json_str.strip().strip('{}')
            if content:
                for pair in content.split(','):
                    if ':' in pair:
                        key, value = pair.split(':', 1)
                        result[key.strip().strip(
                            '"\'')] = value.strip().strip('"\'')
            return result


# --------------------
# Models
# --------------------
class TableIdent(BaseModel):
    schema: str = "public"
    table: str


READ_ONLY_PREFIXES = ("select", "show", "explain", "with")
ALLOWED_SCHEMAS = {"public"}


def is_read_only(sql: str) -> bool:
    head = sql.lstrip().split(None, 1)[0].lower() if sql.strip() else ""
    return head.startswith(READ_ONLY_PREFIXES) or head in READ_ONLY_PREFIXES


# --------------------
# MCP Tools
# --------------------
@mcp.tool()
async def ping() -> str:
    "Health check."
    t0 = time.time()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("SELECT 1")
    return f"ok ({(time.time()-t0)*1000:.0f} ms)"


@mcp.tool()
async def describe_table(payload: Union[TableIdent, str]) -> Dict[str, Any]:
    try:
        if isinstance(payload, str):
            payload_dict = parse_malformed_json(payload)
            if not payload_dict:
                return {"error": "Could not parse JSON payload"}
            table_ident = TableIdent(**payload_dict)
        else:
            table_ident = payload

        if table_ident.schema not in ALLOWED_SCHEMAS:
            return {"error": f"Schema '{table_ident.schema}' not allowed."}

        pool = await get_pool()
        async with pool.acquire() as conn:
            cols = await conn.fetch(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema=$1 AND table_name=$2
                ORDER BY ordinal_position
                """,
                table_ident.schema,
                table_ident.table,
            )
            pks = await conn.fetch(
                """
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name=kcu.constraint_name
                 AND tc.table_schema=kcu.table_schema
                WHERE tc.constraint_type='PRIMARY KEY'
                  AND tc.table_schema=$1 AND tc.table_name=$2
                """,
                table_ident.schema,
                table_ident.table,
            )
            return {
                "columns": [dict(r) for r in cols],
                "primary_key": [r["column_name"] for r in pks],
            }
    except ValidationError as e:
        return {"error": f"Invalid payload format: {e}"}


@mcp.tool()
async def query(
    sql: str,
    params: Optional[Union[Dict[str, Any], str]] = None,
    role: Literal["read", "write"] = "read",
    limit: Optional[int] = 2000,
) -> Dict[str, Any]:
    if isinstance(params, str):
        params = parse_malformed_json(params)
    elif params is None:
        params = {}

    if role == "read" and not is_read_only(sql):
        return {"error": "Write operation not allowed in read role"}

    if is_read_only(sql) and "limit" not in sql.lower():
        sql = f"SELECT * FROM ({sql}) as _sub LIMIT {limit}"

    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            if is_read_only(sql):
                rows = await conn.fetch(sql, *params.values() if params else [])
                return {"rows": [dict(r) for r in rows], "count": len(rows), "sql": redact(sql)}
            else:
                result = await conn.execute(sql, *params.values() if params else [])
                affected = int(result.split()[-1])
                return {"status": "ok", "affected": affected, "sql": redact(sql)}
        except Exception as e:
            return {"error": str(e), "sql": redact(sql)}


@mcp.resource("schema://public")
async def schema_public() -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema='public'
            ORDER BY table_name, ordinal_position
            """
        )
        return json.dumps([dict(r) for r in rows], indent=2)


@mcp.prompt("safe_sql")
def prompt_safe_sql() -> str:
    return (
        "PostgreSQL MCP Server - Available Tools:\n\n"
        "1. ping() - Health check\n"
        "2. describe_table(payload) - Get table structure\n"
        "3. query(sql, params, role, limit) - Unified SQL query tool\n"
        "The function automatically handles malformed JSON.\n"
    )


# --------------------
# Run Server
# --------------------
if __name__ == "__main__":
    import asyncio

    asyncio.run(mcp.run(transport="stdio"))
