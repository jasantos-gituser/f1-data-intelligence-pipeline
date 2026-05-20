import os
import pytest
from f1_pipeline.config import Config

# -- Supabase connection testing function only --
@pytest.mark.skipif(os.getenv("CI") == "true", reason="Skipped in CI")
def test_supabase_connection():
    config = Config()
    conn = config.get_supabase_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT session_key, session_name, payload FROM f1_stats_schema.raw_sessions LIMIT 3;"
    )
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    assert len(rows) > 0, "No rows returned from Supabase"

    for row in rows:
        session_key, session_name, payload = row
        print(f"session_key={session_key} | session_name={session_name} | payload={payload}")
        assert session_key is not None
        assert session_name is not None
        assert payload is not None

# -- Supabase Insert and Get testing function --
@pytest.mark.skipif(os.getenv("CI") == "true", reason="Skipped in CI")
def test_insert_and_get_raw_drivers():
    #from f1_pipeline.db import insert_raw_drivers, get_drivers
    from f1_pipeline.db import insert_raw_session_test, insert_raw_drivers, get_drivers
    from f1_pipeline.models import Driver

    config = Config()
    conn = config.get_supabase_connection()

    insert_raw_session_test(conn)
    driver = Driver()
    insert_raw_drivers(conn, driver)

    rows = get_drivers(conn)
    conn.close()

    assert any(row["session_key"] == 1234 for row in rows), "Inserted driver not found"
    print(f"Total drivers fetched: {len(rows)}")
    for row in rows:
        print(row)

