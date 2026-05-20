from typing import Any, Dict, List, Optional
import psycopg2.extras
import psycopg2

from f1_pipeline.models import Driver

def get_drivers(
    conn: psycopg2.extensions.connection,
) -> List[Dict[str, Any]]:
    columns = ["session_key", "driver_number", "payload", "ingested_at"]

    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {', '.join(columns)} FROM f1_stats_schema.raw_drivers ORDER BY ingested_at DESC"
        )

        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]

def insert_raw_drivers(conn: psycopg2.extensions.connection, driver: Driver) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO f1_stats_schema.raw_drivers (session_key, driver_number, payload, ingested_at)
            VALUES (%(session_key)s, %(driver_number)s, %(payload)s, %(ingested_at)s)
            ON CONFLICT (session_key, driver_number) DO NOTHING
            """,
            {
                "session_key": driver.session_key,
                "driver_number": driver.driver_number,
                "payload": psycopg2.extras.Json(driver.payload),
                "ingested_at": driver.ingested_at,
            },
        )
    conn.commit()


def insert_raw_session_test(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO f1_stats_schema.raw_sessions (session_key, session_name, payload)
            VALUES (%(session_key)s, %(session_name)s, %(payload)s)
            ON CONFLICT (session_key) DO NOTHING
            """,
            {
                "session_key": 1234,
                "session_name": "test_session",
                "payload": psycopg2.extras.Json({"test": True}),
            },
        )
    conn.commit()