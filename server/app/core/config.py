from dataclasses import dataclass, fields, field, MISSING
import os
import json


@dataclass(frozen=True)
class Settings:
	app_name: str = "DB Project 1 API"
	api_v1_prefix: str = "/api/v1"
	db_host: str = "localhost"
	db_port: int = 5432
	db_user: str = "postgres"
	db_password: str = "postgres"
	db_name: str = "db_project_1"
	db_min_connections: int = 1
	db_max_connections: int = 10
	cors_origins: list = field(default_factory=lambda: ["*"])

	@property
	def database_url(self) -> str:
		return (
			f"postgresql://{self.db_user}:{self.db_password}"
			f"@{self.db_host}:{self.db_port}/{self.db_name}"
		)

	@classmethod
	def from_json_then_env(cls, path: str | None = None) -> "Settings":
		data = {}
		# Always resolve config.json from this file's directory unless a custom path is provided.
		config_path = path or os.path.join(os.path.dirname(__file__), "config.json")
		if os.path.exists(config_path):
			with open(config_path, "r", encoding="utf-8") as f:
				data = json.load(f)

		final = {}
		for fdef in fields(cls):
			key = fdef.name
			env_key = key.upper()
			if key in data:
				value = data[key]
			elif env_key in os.environ:
				value = os.getenv(env_key)
				if fdef.type is list:
					try:
						value = json.loads(value)
					except Exception:
						value = [value]
			else:
				if fdef.default is not MISSING:
					value = fdef.default
				elif fdef.default_factory is not MISSING:
					value = fdef.default_factory()
				else:
					value = None

			if fdef.type is int and value is not None:
				value = int(value)
			final[key] = value
		return cls(**final)


settings = Settings.from_json_then_env()
