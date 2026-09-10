# 1. Auto-resolve SQLite Migration Conflicts

Date: 2026-09-10

## Status

Accepted

## Context

The application relies on SQLite and runs Alembic migrations automatically on startup (`startup_event` in `main.py`). This allows developers to pull from GitHub and immediately run the app without manual schema steps. 

However, SQLite's `ALTER TABLE` support is limited. Alembic handles this using "batch mode" (creating a `_alembic_tmp_` table, copying data, and swapping). 

This migration process is fragile when the existing data violates new constraints (like a `UNIQUE` constraint on `user_id`). Specifically, the `user_permissions` table contained duplicate `user_id` records due to previously failed or partial migrations, which caused the migration `6b50af58c536` to crash with `UNIQUE constraint failed`, breaking the application startup.

## Decision

We will automatically scrub dirty data (such as duplicates in `user_permissions`) in the startup script right before calling `command.upgrade()`. 

Specifically, we execute:
```sql
DELETE FROM user_permissions 
WHERE id NOT IN (
    SELECT MAX(id) 
    FROM user_permissions 
    GROUP BY user_id
)
```
We chose to hardcode this fix specifically for `user_permissions` rather than building a generalized metadata reflection engine that deletes data across the entire database, as that would be overly complex and risky.

## Consequences

- **Pros:** Migrations are zero-touch and robust against minor database state corruptions. Pulling code from GitHub will "just work", even if the local database is dirty.
- **Cons:** We are implicitly hiding data integrity issues. If a bug in the application is causing duplicate permissions to be created, we won't see it crash; the startup script will just silently delete the evidence on the next run. Data loss is possible if we accidentally delete the "wrong" row during deduplication.
