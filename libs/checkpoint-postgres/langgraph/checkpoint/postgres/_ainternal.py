"""Shared async utility functions for the Postgres checkpoint & storage classes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from psycopg.rows import DictRow
from psycopg_pool import AsyncConnectionPool

Conn = AsyncConnection[DictRow] | AsyncConnectionPool[AsyncConnection[DictRow]]


@asynccontextmanager
async def get_connection(
    conn: Conn,
) -> AsyncIterator[AsyncConnection[DictRow]]:
    """Yield a usable `AsyncConnection` from either an `AsyncConnection` or `AsyncConnectionPool`.

    If `conn` is already an `AsyncConnection`, it is yielded as-is (the caller retains
    ownership and is responsible for closing it). If `conn` is an `AsyncConnectionPool`,
    a connection is checked out of the pool for the duration of the `async with` block
    and automatically returned to the pool afterward.

    Args:
        conn: Either an `AsyncConnection` or an `AsyncConnectionPool` to draw a connection from.

    Yields:
        An `AsyncConnection[DictRow]` usable for the duration of the `async with` block.

    Raises:
        TypeError: If `conn` is neither an `AsyncConnection` nor an `AsyncConnectionPool`.
    """
    if isinstance(conn, AsyncConnection):
        yield conn
    elif isinstance(conn, AsyncConnectionPool):
        async with conn.connection() as conn:
            yield conn
    else:
        raise TypeError(f"Invalid connection type: {type(conn)}")
