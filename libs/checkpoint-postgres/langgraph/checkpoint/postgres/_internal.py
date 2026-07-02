"""Shared utility functions for the Postgres checkpoint & storage classes."""

from collections.abc import Iterator
from contextlib import contextmanager

from psycopg import Connection
from psycopg.rows import DictRow
from psycopg_pool import ConnectionPool

Conn = Connection[DictRow] | ConnectionPool[Connection[DictRow]]


@contextmanager
def get_connection(conn: Conn) -> Iterator[Connection[DictRow]]:
    """Yield a usable `Connection` from either a `Connection` or a `ConnectionPool`.

    If `conn` is already a `Connection`, it is yielded as-is (the caller retains
    ownership and is responsible for closing it). If `conn` is a `ConnectionPool`,
    a connection is checked out of the pool for the duration of the `with` block
    and automatically returned to the pool afterward.

    Args:
        conn: Either a `Connection` or a `ConnectionPool` to draw a connection from.

    Yields:
        A `Connection[DictRow]` usable for the duration of the `with` block.

    Raises:
        TypeError: If `conn` is neither a `Connection` nor a `ConnectionPool`.
    """
    if isinstance(conn, Connection):
        yield conn
    elif isinstance(conn, ConnectionPool):
        with conn.connection() as conn:
            yield conn
    else:
        raise TypeError(f"Invalid connection type: {type(conn)}")
