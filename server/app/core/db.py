from contextlib import contextmanager
from typing import Generator, Optional

from psycopg2.pool import ThreadedConnectionPool

from app.core.config import settings


connection_pool: Optional[ThreadedConnectionPool] = None


def init_connection_pool() -> None:
	global connection_pool
	if connection_pool is not None:
		return
	connection_pool = ThreadedConnectionPool(
		minconn=settings.db_min_connections,
		maxconn=settings.db_max_connections,
		host=settings.db_host,
		port=settings.db_port,
		user=settings.db_user,
		password=settings.db_password,
		dbname=settings.db_name,
	)


def close_connection_pool() -> None:
	global connection_pool
	if connection_pool is None:
		return
	connection_pool.closeall()
	connection_pool = None


def get_connection():
	if connection_pool is None:
		init_connection_pool()
	if connection_pool is None:
		raise RuntimeError("Database connection pool is not available")
	return connection_pool.getconn()


def release_connection(conn) -> None:
	if connection_pool is None:
		conn.close()
		return
	connection_pool.putconn(conn)


@contextmanager
def connection_scope():
	conn = get_connection()
	try:
		yield conn
		conn.commit()
	except Exception:
		conn.rollback()
		raise
	finally:
		release_connection(conn)


def get_db() -> Generator:
	with connection_scope() as conn:
		yield conn
