-- F1 Data Intelligence Pipeline — Database Schema
-- Schema: f1_stats_schema
-- Run this in the Supabase SQL editor to initialize all tables.
-- All raw_* tables are append-only (ON CONFLICT DO NOTHING).
-- All f1_* tables are idempotent (ON CONFLICT DO NOTHING or DO UPDATE).

CREATE SCHEMA IF NOT EXISTS f1_stats_schema;
SET search_path TO f1_stats_schema;

-- ============================================================
-- RAW LAYER — OpenF1 API payloads, never overwritten
-- raw_sessions is the parent — all other raw_* tables FK to it
-- ============================================================

CREATE TABLE IF NOT EXISTS raw_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_key         INTEGER NOT NULL,
    session_name        TEXT,
    session_type        TEXT,
    date_start          TIMESTAMPTZ,
    date_end            TIMESTAMPTZ,
    year                INTEGER,
    circuit_key         INTEGER,
    circuit_short_name  TEXT,
    country_name        TEXT,
    location            TEXT,
    payload             JSONB NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_key)
);

CREATE TABLE IF NOT EXISTS raw_drivers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_key     INTEGER NOT NULL,
    driver_number   INTEGER NOT NULL,
    payload         JSONB NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_key, driver_number),
    FOREIGN KEY (session_key) REFERENCES raw_sessions (session_key) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS raw_laps (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_key     INTEGER NOT NULL,
    driver_number   INTEGER NOT NULL,
    lap_number      INTEGER NOT NULL,
    payload         JSONB NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_key, driver_number, lap_number),
    FOREIGN KEY (session_key) REFERENCES raw_sessions (session_key) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS raw_pit (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_key     INTEGER NOT NULL,
    driver_number   INTEGER NOT NULL,
    lap_number      INTEGER NOT NULL,
    payload         JSONB NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_key, driver_number, lap_number),
    FOREIGN KEY (session_key) REFERENCES raw_sessions (session_key) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS raw_position (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_key     INTEGER NOT NULL,
    driver_number   INTEGER NOT NULL,
    recorded_at     TIMESTAMPTZ NOT NULL,
    payload         JSONB NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_key, driver_number, recorded_at),
    FOREIGN KEY (session_key) REFERENCES raw_sessions (session_key) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS raw_weather (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_key     INTEGER NOT NULL,
    recorded_at     TIMESTAMPTZ NOT NULL,
    payload         JSONB NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_key, recorded_at),
    FOREIGN KEY (session_key) REFERENCES raw_sessions (session_key) ON DELETE CASCADE
);

-- ============================================================
-- ANALYTICS LAYER — populated by SQL transforms, query-ready
-- No FK to raw_* — analytics layer is independent of raw layer
-- ============================================================

CREATE TABLE IF NOT EXISTS f1_race_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    season          INTEGER NOT NULL,
    round           INTEGER NOT NULL,
    race_name       TEXT NOT NULL,
    driver_id       TEXT NOT NULL,
    driver_name     TEXT NOT NULL,
    team_name       TEXT NOT NULL,
    position        INTEGER,
    points          NUMERIC(5,2) NOT NULL DEFAULT 0,
    status          TEXT NOT NULL,
    fastest_lap     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (season, round, driver_id)
);

CREATE TABLE IF NOT EXISTS f1_driver_standings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    season          INTEGER NOT NULL,
    round           INTEGER NOT NULL,
    driver_id       TEXT NOT NULL,
    driver_name     TEXT NOT NULL,
    team_name       TEXT NOT NULL,
    position        INTEGER NOT NULL,
    points          NUMERIC(6,2) NOT NULL DEFAULT 0,
    wins            INTEGER NOT NULL DEFAULT 0,
    podiums         INTEGER NOT NULL DEFAULT 0,
    dnf_count       INTEGER NOT NULL DEFAULT 0,
    races_entered   INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (season, round, driver_id)
);

CREATE TABLE IF NOT EXISTS f1_predictions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    season          INTEGER NOT NULL,
    round           INTEGER NOT NULL,
    mode            TEXT NOT NULL CHECK (mode IN ('rule_based', 'ai')),
    predicted_winner TEXT NOT NULL,
    confidence      TEXT CHECK (confidence IN ('high', 'medium', 'low')),
    score           NUMERIC(5,2),
    score_breakdown JSONB,
    reasoning       JSONB,
    data_recency    DATE NOT NULL,
    stale_data      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (season, round, mode)
);

-- ============================================================
-- INDEXES — speed up common query patterns
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_raw_sessions_year        ON raw_sessions (year);
CREATE INDEX IF NOT EXISTS idx_raw_drivers_session      ON raw_drivers (session_key);
CREATE INDEX IF NOT EXISTS idx_raw_laps_session         ON raw_laps (session_key, driver_number);
CREATE INDEX IF NOT EXISTS idx_raw_pit_session          ON raw_pit (session_key, driver_number);
CREATE INDEX IF NOT EXISTS idx_raw_position_session     ON raw_position (session_key, driver_number);
CREATE INDEX IF NOT EXISTS idx_raw_weather_session      ON raw_weather (session_key);

CREATE INDEX IF NOT EXISTS idx_f1_race_results_season   ON f1_race_results (season, round);
CREATE INDEX IF NOT EXISTS idx_f1_standings_season      ON f1_driver_standings (season, driver_id);
CREATE INDEX IF NOT EXISTS idx_f1_predictions_lookup    ON f1_predictions (season, round, mode);
