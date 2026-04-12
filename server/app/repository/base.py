class BaseRepository:
	def __init__(self, conn):
		self.conn = conn

	def fetch_one(self, query: str, params: tuple = ()):
		with self.conn.cursor() as cur:
			cur.execute(query, params)
			return cur.fetchone()

	def fetch_all(self, query: str, params: tuple = ()):
		with self.conn.cursor() as cur:
			cur.execute(query, params)
			return cur.fetchall()

	def execute(self, query: str, params: tuple = ()) -> int:
		with self.conn.cursor() as cur:
			cur.execute(query, params)
			return cur.rowcount
