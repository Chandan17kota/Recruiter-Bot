"""Database liveness check. Static, hand-written SQL."""

PING_SQL = "SELECT 1"


def ping(conn) -> bool:
    return conn.execute(PING_SQL).fetchone() is not None
