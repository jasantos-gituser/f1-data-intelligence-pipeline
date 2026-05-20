import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

class Config:
    def __init__(self) -> None:
        # NewsAPI configuration
        self.openf1_api_key = os.getenv("API_KEY")
        self.openf1_base_url = os.getenv("API_BASE_URL")

        # Supabase configuration
        self.database_url = os.getenv("DATABASE_URL")

        # Scheduler configuration
        self.ingest_interval_hours = os.getenv("INGEST_INTERVAL_HOURS")
        self.openf1_timeout_seconds = os.getenv("OPENF1_TIMEOUT_SECONDS")
        self.prediction_cache_enabled = os.getenv("PREDICTION_CACHE_ENABLED")
        self.environment = os.getenv("ENVIRONMENT")

        self._validate()

    def _validate(self) -> None:
        missing = []

        if not self.openf1_api_key:
            missing.append("API_KEY")
        if not self.openf1_base_url:
            missing.append("API_BASE_URL")
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.openf1_timeout_seconds:
            missing.append("OPENF1_TIMEOUT_SECONDS")
        if not self.prediction_cache_enabled:
            missing.append("PREDICTION_CACHE_ENABLED")
        if not self.environment:
            missing.append("ENVIRONMENT")

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    def get_supabase_connection(self) -> psycopg2.extensions.connection:
        return psycopg2.connect(self.database_url)
