# DB Project 1 - Complete Task Implementation

This repository now contains a full PostgreSQL + Python implementation for the CS307 Project Part 1 tasks.

## Files

- `schema.sql` - normalized database DDL (with `ticket_order` and split ticket model)
- `import_data.py` - imports all CSV data from `Archive/`
- `cli.py` - command-line CRUD and query operations
- `requirements.txt` - Python dependency list

## 1) Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create database first (example):

```sql
CREATE DATABASE db_project_1;
```

## 2) Import data

```bash
python import_data.py \
  --host localhost --port 5432 \
  --user postgres --password postgres \
  --database db_project_1
```

## 3) Task 3.2 query support

Given region code, list all cities:

```bash
python cli.py cities-by-region --region-code CN
```

Given city name, list all airports and iata_code:

```bash
python cli.py airports-by-city --city Taipei
```

Given region code, list all airlines:

```bash
python cli.py airlines-by-region --region-code TW
```

Given source/destination iata_code, list flights:

```bash
python cli.py flights-by-iata --source FCO --destination LTN
```

## 4) Task 4 CRUD support

Generate ticket inventory by date range:

```bash
python cli.py generate --start-date 2026-04-10 --end-date 2026-04-16
```

Search tickets (required + optional fields):

```bash
python cli.py search \
  --departure-city Rome --arrival-city London --date 2026-04-10 \
  --airline Alitalia --departure-time 08:00 --arrival-time 23:00
```

Book a ticket:

```bash
python cli.py book --passenger-id 1 --ticket-id 100 --cabin-class economy
```

List orders:

```bash
python cli.py orders --passenger-id 1
```

Cancel order:

```bash
python cli.py cancel --passenger-id 1 --order-id 10
```

## Arrival-time-before-11:00 query handling

`flight.arrival_day_offset` stores day rollover (`0` same day, `1` next day), so querying arrivals before 11:00 on the same day is straightforward and efficient:

```sql
SELECT *
FROM flight
WHERE arrival_day_offset = 0
  AND arrival_time_local < '11:00:00';
```
