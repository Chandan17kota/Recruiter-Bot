from psycopg import OperationalError
from psycopg.errors import QueryCanceled
from psycopg_pool import PoolTimeout


def test_pool_and_statement_timeouts_are_operational_errors():
    assert issubclass(PoolTimeout, OperationalError)
    assert issubclass(QueryCanceled, OperationalError)
