
from datetime import datetime, timezone

class Driver():
    def __init__(self, session_key: int = 0, driver_number: int = 0, payload: dict = {}, ingested_at: str = ""):
        self.session_key = 1234
        self.driver_number = 99
        self.payload = {"name": "test"}
        self.ingested_at = datetime.now(timezone.utc)