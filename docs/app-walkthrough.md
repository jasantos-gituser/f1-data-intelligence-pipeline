# F1 Pipeline — End-to-End Walkthrough

How data moves from the OpenF1 API all the way to a race winner prediction.
Uses 2024 Season, Round 5 (Chinese GP) as the completed race, and Round 6 (Miami GP) as the race being predicted.

> **Session scope:** The pipeline ingests a rolling 3-year window — from `max(2023, current_year - 3)` through the current year. In 2026 this means 2023–2026; in 2027 it becomes 2024–2027, and so on. This ensures the latest race (even from last week) is always included without manual config changes. Only `session_type=Race` sessions are fetched — practice and qualifying sessions are excluded.

---

## Big Picture: What the Two Endpoints Do

```
Client
  │
  ├─ POST /ingest  ──────────────────────────────────────────────────────►
  │                  pipeline.py calls loaders + transforms
  │                  Raw API data → raw_* tables → f1_* analytics tables
  │
  └─ GET /predict_next_race?mode=rule_based  (or mode=ai)  ────────────►
                     predictors read from f1_driver_standings
                     + f1_race_results, score every driver, return winner
```

---

## Step 1 — POST /ingest

**Request:**
```
POST /ingest
X-API-Key: your-api-key
```

**What happens inside:**

```
POST /ingest
     │
     ▼
pipeline.py
     │
     ├─ openf1_loader.py
     │    Calls OpenF1 API for each endpoint:
     │    GET /sessions?year=2023&session_type=Race  ┐
     │    GET /sessions?year=2024&session_type=Race  │ rolling 3-year window
     │    GET /sessions?year=2025&session_type=Race  │ (years computed at runtime,
     │    GET /sessions?year=2026&session_type=Race  ┘  floor = 2023)
     │    GET /drivers?session_key=<key>
     │    GET /laps?session_key=<key>
     │    GET /pit?session_key=<key>
     │    GET /position?session_key=<key>
     │    GET /weather?session_key=<key>
     │    (sleep 0.25s between each call)
     │
     ├─ csv_loader.py
     │    Scans /data/manual/ for .csv files
     │    Validates required columns, loads if present
     │
     └─ sql_transforms.py
          Runs SQL to populate:
          f1_race_results  ◄── reads raw_laps + raw_drivers + raw_sessions
          f1_driver_standings  ◄── aggregates f1_race_results
```

**Response:**
```json
{
  "sessions_ingested": 1,
  "rows_loaded": 847,
  "duration_seconds": 12.4
}
```

---

## Step 2 — What the Raw Tables Look Like After Ingest

### raw_sessions — 1 row per race session

```
┌─────────┬─────────────┬──────────────┬──────────────┬───────────┬──────────────────────────────────────────────────────┬─────────────────────────┐
│ id      │ session_key │ session_name │ session_type │ year      │ payload                                              │ ingested_at             │
├─────────┼─────────────┼──────────────┼──────────────┼───────────┼──────────────────────────────────────────────────────┼─────────────────────────┤
│ uuid... │ 9158        │ Race         │ Race         │ 2024      │ { "meeting_key": 1219,                               │ 2024-04-22 08:00:00 UTC │
│         │             │              │              │           │   "circuit_key": 58,                                 │                         │
│         │             │              │              │           │   "circuit_short_name": "Shanghai",                  │                         │
│         │             │              │              │           │   "country_name": "China",                           │                         │
│         │             │              │              │           │   "date_start": "2024-04-21T07:00:00+00:00",         │                         │
│         │             │              │              │           │   "date_end": "2024-04-21T09:30:00+00:00" }          │                         │
└─────────┴─────────────┴──────────────┴──────────────┴───────────┴──────────────────────────────────────────────────────┴─────────────────────────┘
```

### raw_drivers — 1 row per driver per session

The two columns pulled out (`session_key`, `driver_number`) are the UNIQUE constraint and FK.
Everything else from the API response goes into `payload` as-is.

```
┌─────────┬─────────────┬───────────────┬──────────────────────────────────────────────────────────────────────────────┬─────────────────────────┐
│ id      │ session_key │ driver_number │ payload                                                                      │ ingested_at             │
├─────────┼─────────────┼───────────────┼──────────────────────────────────────────────────────────────────────────────┼─────────────────────────┤
│ uuid... │ 9158        │ 1             │ {                                                                            │ 2024-04-22 08:00:00 UTC │
│         │             │               │   "meeting_key": 1219,                                                       │                         │
│         │             │               │   "session_key": 9158,                                                       │                         │
│         │             │               │   "driver_number": 1,                                                        │                         │
│         │             │               │   "broadcast_name": "M VERSTAPPEN",                                          │                         │
│         │             │               │   "full_name": "Max VERSTAPPEN",                                             │                         │
│         │             │               │   "name_acronym": "VER",                                                     │                         │
│         │             │               │   "team_name": "Red Bull Racing",                                            │                         │
│         │             │               │   "team_colour": "3671C6",                                                   │                         │
│         │             │               │   "first_name": "Max",                                                       │                         │
│         │             │               │   "last_name": "Verstappen",                                                 │                         │
│         │             │               │   "headshot_url": "https://www.formula1.com/.../maxver01.png",               │                         │
│         │             │               │   "country_code": "NED"                                                      │                         │
│         │             │               │ }                                                                            │                         │
├─────────┼─────────────┼───────────────┼──────────────────────────────────────────────────────────────────────────────┼─────────────────────────┤
│ uuid... │ 9158        │ 4             │ { "name_acronym": "NOR", "full_name": "Lando NORRIS", ... }                  │ 2024-04-22 08:00:00 UTC │
│ uuid... │ 9158        │ 16            │ { "name_acronym": "LEC", "full_name": "Charles LECLERC", ... }               │ 2024-04-22 08:00:00 UTC │
│  ...    │  ...        │  ...          │  ...                                                                         │ ...                     │
└─────────┴─────────────┴───────────────┴──────────────────────────────────────────────────────────────────────────────┴─────────────────────────┘
```

> The raw layer never transforms or filters. Even `session_key` and `driver_number` are kept inside `payload` — they were in the original API response. The dedicated columns are just for indexing and constraints.

---

## Step 3 — SQL Transform: raw_* → Analytics Layer

After loading raw data, `sql_transforms.py` runs SQL that reads from the raw tables and writes structured rows into `f1_race_results` and `f1_driver_standings`. It uses Postgres JSONB operators to extract fields from `payload`.

```
raw_sessions ──┐
raw_drivers  ──┼──► SQL transform ──► f1_race_results  ──► f1_driver_standings
raw_laps     ──┘                      (1 row per driver     (1 row per driver
                                       per race round)       per season round,
                                                             cumulative totals)
```

### f1_race_results — after Round 5 (Chinese GP)

```
┌──────────┬───────┬─────────────┬───────────┬──────────────────┬───────────────────┬──────────┬────────┬──────────┬─────────────┐
│ season   │ round │ race_name   │ driver_id │ driver_name      │ team_name         │ position │ points │ status   │ fastest_lap │
├──────────┼───────┼─────────────┼───────────┼──────────────────┼───────────────────┼──────────┼────────┼──────────┼─────────────┤
│ 2024     │ 5     │ Chinese GP  │ VER       │ Max Verstappen   │ Red Bull Racing   │ 1        │ 25.00  │ Finished │ false       │
│ 2024     │ 5     │ Chinese GP  │ NOR       │ Lando Norris     │ McLaren           │ 2        │ 18.00  │ Finished │ true        │
│ 2024     │ 5     │ Chinese GP  │ SAI       │ Carlos Sainz     │ Ferrari           │ 3        │ 15.00  │ Finished │ false       │
│ 2024     │ 5     │ Chinese GP  │ PER       │ Sergio Perez     │ Red Bull Racing   │ 4        │ 12.00  │ Finished │ false       │
│ 2024     │ 5     │ Chinese GP  │ RUS       │ George Russell   │ Mercedes          │ 5        │ 10.00  │ Finished │ false       │
│ 2024     │ 5     │ Chinese GP  │ LEC       │ Charles Leclerc  │ Ferrari           │ 6        │ 8.00   │ Finished │ false       │
│ 2024     │ 5     │ Chinese GP  │ HAM       │ Lewis Hamilton   │ Mercedes          │ 7        │ 6.00   │ Finished │ false       │
│  ...     │  ...  │  ...        │  ...      │  ...             │  ...              │  ...     │  ...   │  ...     │  ...        │
│ 2024     │ 5     │ Chinese GP  │ ALO       │ Fernando Alonso  │ Aston Martin      │ 15       │ 0.00   │ DNF      │ false       │
└──────────┴───────┴─────────────┴───────────┴──────────────────┴───────────────────┴──────────┴────────┴──────────┴─────────────┘
```

### f1_driver_standings — after Round 5 (cumulative season totals)

```
┌────────┬───────┬───────────┬──────────────────┬───────────────────┬──────────┬────────┬──────┬─────────┬───────────┬───────────────┐
│ season │ round │ driver_id │ driver_name      │ team_name         │ position │ points │ wins │ podiums │ dnf_count │ races_entered │
├────────┼───────┼───────────┼──────────────────┼───────────────────┼──────────┼────────┼──────┼─────────┼───────────┼───────────────┤
│ 2024   │ 5     │ VER       │ Max Verstappen   │ Red Bull Racing   │ 1        │ 136.00 │ 4    │ 5       │ 0         │ 5             │
│ 2024   │ 5     │ PER       │ Sergio Perez     │ Red Bull Racing   │ 2        │ 87.00  │ 0    │ 3       │ 0         │ 5             │
│ 2024   │ 5     │ SAI       │ Carlos Sainz     │ Ferrari           │ 3        │ 83.00  │ 1    │ 3       │ 0         │ 5             │
│ 2024   │ 5     │ NOR       │ Lando Norris     │ McLaren           │ 4        │ 69.00  │ 0    │ 2       │ 0         │ 5             │
│ 2024   │ 5     │ LEC       │ Charles Leclerc  │ Ferrari           │ 5        │ 65.00  │ 0    │ 2       │ 1         │ 5             │
│ 2024   │ 5     │ RUS       │ George Russell   │ Mercedes          │ 6        │ 37.00  │ 0    │ 1       │ 0         │ 5             │
│ 2024   │ 5     │ HAM       │ Lewis Hamilton   │ Mercedes          │ 7        │ 36.00  │ 0    │ 1       │ 0         │ 5             │
│  ...   │  ...  │  ...      │  ...             │  ...              │  ...     │  ...   │  ... │  ...    │  ...      │  ...          │
└────────┴───────┴───────────┴──────────────────┴───────────────────┴──────────┴────────┴──────┴─────────┴───────────┴───────────────┘
```

---

## Step 4 — GET /predict_next_race (Round 6 — Miami GP)

**Request:**
```
GET /predict_next_race?mode=rule_based
X-API-Key: your-api-key
```

### Mode: rule_based

The predictor reads from `f1_driver_standings` and `f1_race_results`, then scores every driver across 5 factors. The highest score wins.

```
f1_driver_standings  ──┐
                        ├──► rule_based.py scores each driver ──► top score = predicted_winner
f1_race_results      ──┘
```

#### Scoring each driver (max 100 points total)

```
Factor                   Max   How calculated                              VER example
─────────────────────────────────────────────────────────────────────────────────────
championship_position     40   Inverse-scaled: P1=40, P2=36, P3=33...     P1  → 40.0
recent_wins               25   5 pts per win in last 5 races               4 wins → 20.0 (capped at 5)
podium_rate               20   (podiums ÷ races) × 20                      (5÷5) × 20 → 20.0
circuit_history           10   Inverse-scaled 3yr avg finish at Miami      avg P1.5 → 9.2
constructor_reliability    5   (1 − dnf_rate) × 5                          (1 − 0/5) × 5 → 5.0
─────────────────────────────────────────────────────────────────────────────────────
TOTAL                    100                                                94.2
```

#### Score table for all drivers

```
Driver      P.Pos  Rec.Wins  Podium%  Circuit  Reliability  TOTAL
──────────────────────────────────────────────────────────────────
VER         40.0    20.0      20.0     9.2       5.0         94.2  ← winner
SAI         33.0    10.0      12.0     7.1       5.0         67.1
PER         36.0     0.0      12.0     6.8       5.0         59.8
NOR         30.0     0.0       8.0     5.5       5.0         48.5
LEC         27.0     0.0       8.0     6.2       4.0         45.2
...
```

**Response (rule_based):**
```json
{
  "season": 2024,
  "round": 6,
  "race_name": "Miami Grand Prix",
  "mode": "rule_based",
  "predicted_winner": "Max Verstappen",
  "score": 94.2,
  "score_breakdown": {
    "championship_position": 40.0,
    "recent_wins": 20.0,
    "podium_rate": 20.0,
    "circuit_history": 9.2,
    "constructor_reliability": 5.0
  },
  "data_recency": "2024-04-21",
  "stale_data": false
}
```

---

### Mode: ai

**Request:**
```
GET /predict_next_race?mode=ai
X-API-Key: your-api-key
```

```
                ┌─────────────────────────────────┐
                │   f1_predictions cache?          │
                │   WHERE season=2024              │
                │     AND round=6                  │
                │     AND mode='ai'                │
                └──────────────┬──────────────────┘
                               │
               ┌───────────────┴───────────────┐
            HIT │                               │ MISS
               ▼                               ▼
        return cached row           build context payload
        no API call                 from f1_driver_standings
        cached: true                + f1_race_results
                                           │
                                           ▼
                                    call Claude API
                                    (claude-sonnet-4-20250514)
                                           │
                                           ▼
                                    parse JSON response
                                           │
                                           ▼
                                    INSERT into f1_predictions
                                           │
                                           ▼
                                    return result
                                    cached: false
```

The context payload sent to Claude looks like this (built from the DB):

```
You are an F1 race analyst. Predict the winner of Round 6 (Miami GP) of the 2024 season.
Respond only in JSON with keys: predicted_winner, confidence, reasoning, data_recency.

Current standings after Round 5:
1. Max Verstappen (Red Bull) — 136 pts, 4 wins, 5 podiums, 0 DNFs
2. Sergio Perez (Red Bull) — 87 pts, 0 wins, 3 podiums, 0 DNFs
3. Carlos Sainz (Ferrari) — 83 pts, 1 win, 3 podiums, 0 DNFs
...

Last 5 race results: [array of f1_race_results rows]
```

**Response (ai — cache MISS, first call):**
```json
{
  "season": 2024,
  "round": 6,
  "race_name": "Miami Grand Prix",
  "mode": "ai",
  "predicted_winner": "Max Verstappen",
  "confidence": "high",
  "reasoning": [
    "Leads the championship by 49 points after 5 rounds",
    "Won 4 of 5 races — dominant pace across all circuit types",
    "Red Bull shown strongest race pace and pit strategy this season",
    "No DNFs — exceptional reliability advantage over rivals"
  ],
  "data_recency": "2024-04-21",
  "stale_data": false,
  "cached": false
}
```

**Response (ai — cache HIT, any subsequent call for same round):**
```json
{
  "season": 2024,
  "round": 6,
  "race_name": "Miami Grand Prix",
  "mode": "ai",
  "predicted_winner": "Max Verstappen",
  "confidence": "high",
  "reasoning": [
    "Leads the championship by 49 points after 5 rounds",
    "Won 4 of 5 races — dominant pace across all circuit types",
    "Red Bull shown strongest race pace and pit strategy this season",
    "No DNFs — exceptional reliability advantage over rivals"
  ],
  "data_recency": "2024-04-21",
  "stale_data": false,
  "cached": true
}
```

> The only difference on a cache hit is `"cached": true`. The Claude API is not called again.

---

### What f1_predictions looks like after both modes run

```
┌────────┬───────┬────────────┬──────────────────┬────────────┬───────┬───────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────┬──────────────┬────────────┐
│ season │ round │ mode       │ predicted_winner │ confidence │ score │ score_breakdown                                       │ reasoning                                                                                              │ data_recency │ stale_data │
├────────┼───────┼────────────┼──────────────────┼────────────┼───────┼───────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────┼────────────┤
│ 2024   │ 6     │ rule_based │ Max Verstappen   │ null       │ 94.2  │ {"championship_position": 40.0, "recent_wins": 20.0,  │ null                                                                                                   │ 2024-04-21   │ false      │
│        │       │            │                  │            │       │  "podium_rate": 20.0, "circuit_history": 9.2,         │                                                                                                        │              │            │
│        │       │            │                  │            │       │  "constructor_reliability": 5.0}                      │                                                                                                        │              │            │
├────────┼───────┼────────────┼──────────────────┼────────────┼───────┼───────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────┼────────────┤
│ 2024   │ 6     │ ai         │ Max Verstappen   │ high       │ null  │ null                                                  │ ["Leads the championship by 49 points after 5 rounds",                                                 │ 2024-04-21   │ false      │
│        │       │            │                  │            │       │                                                       │  "Won 4 of 5 races — dominant pace across all circuit types",                                          │              │            │
│        │       │            │                  │            │       │                                                       │  "Red Bull shown strongest race pace and pit strategy this season",                                    │              │            │
│        │       │            │                  │            │       │                                                       │  "No DNFs — exceptional reliability advantage over rivals"]                                            │              │            │
└────────┴───────┴────────────┴──────────────────┴────────────┴───────┴───────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────┴──────────────┴────────────┘
```

> `rule_based` rows have `score` + `score_breakdown`, no `confidence` or `reasoning`.
> `ai` rows have `confidence` + `reasoning`, no `score` or `score_breakdown`.

---

## stale_data Flag

Both modes attach `stale_data` to every response.

```
Latest round in DB = Round 5 (Chinese GP, April 21)
Most recently completed real-world race = Round 5 ✓

stale_data: false  →  prediction is based on current data
```

If the pipeline hasn't run yet after Round 6 completes:

```
Latest round in DB = Round 5
Most recently completed real-world race = Round 6 (Miami, May 5) ✓

stale_data: true   →  prediction is based on data that is one race behind
```

The client receives this flag and must decide what to show the user — the API never silently serves outdated data.

---

## Full Data Flow Summary

```
OpenF1 API
    │
    │  raw JSON responses
    ▼
raw_sessions ─────────────────────────────────────────────────────────────────────┐
raw_drivers  ──┐                                                                  │
raw_laps     ──┤  (one row per entity,                                            │
raw_pit      ──┤   payload = full API response as JSONB,                          │
raw_position ──┤   never modified after insert)                                   │
raw_weather  ──┘                                                                  │
    │                                                                             │
    │  sql_transforms.py                                                          │
    │  (reads payload JSONB fields, writes structured rows)                       │
    ▼                                                                             │
f1_race_results  ──────────────────────────────────────────────────────────────►─┤
    │                                                                             │
    │  aggregated                                                                 │
    ▼                                                                             │
f1_driver_standings  ──────────────────────────────────────────────────────────►─┤
    │                                                                             │
    │  read by predictors                                                         │
    ├──────────────────────────┐                                                  │
    ▼                          ▼                                                  │
rule_based.py             ai_predictor.py                                         │
(pure Python scoring)     (check cache first,                                     │
                           call Claude if miss)                                   │
    │                          │                                                  │
    └──────────────┬───────────┘                                                  │
                   ▼                                                              │
            f1_predictions  ◄─────────────────────────────────────────────────────┘
                   │          (cache: UNIQUE on season + round + mode)
                   ▼
            API response  →  client
```
