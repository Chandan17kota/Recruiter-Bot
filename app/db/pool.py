"""Connection pool. Opened and closed by the FastAPI lifespan."""
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def make_pool(database_url: str, statement_timeout_ms: int, timeout_s: float = 5.0) -> ConnectionPool:
    return ConnectionPool(
        conninfo=database_url,
        min_size=1,
        max_size=10,
        timeout=timeout_s,            # wait at most this long for a connection -> PoolTimeout
        open=False,
        kwargs={
            "row_factory": dict_row,
            # Server-side cap on every statement; exceeding it raises QueryCanceled.
            "options": f"-c statement_timeout={int(statement_timeout_ms)}",
        },
    )
