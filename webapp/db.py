from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: Path) -> None:
    connection = connect(db_path)
    connection.executescript(
        """
        create table if not exists tasks (
            id integer primary key autoincrement,
            mode text not null,
            status text not null,
            payload_json text not null,
            result_json text,
            error_text text,
            stop_requested integer not null default 0,
            created_at text not null default current_timestamp,
            started_at text,
            finished_at text
        );

        create table if not exists task_events (
            id integer primary key autoincrement,
            task_id integer not null,
            level text not null,
            message text not null,
            created_at text not null default current_timestamp
        );

        create table if not exists accounts (
            id integer primary key autoincrement,
            task_id integer not null,
            email text,
            password text,
            mode text not null,
            ott text,
            session_token text,
            trial_checkout_url text,
            pool_status text,
            created_at text not null default current_timestamp
        );

        create table if not exists account_tombstones (
            email text primary key,
            deleted_at text not null default current_timestamp
        );
        """
    )
    columns = {
        row["name"]
        for row in connection.execute("pragma table_info(accounts)").fetchall()
    }
    if "password" not in columns:
        connection.execute("alter table accounts add column password text")
    if "session_token" not in columns:
        connection.execute("alter table accounts add column session_token text")
    connection.commit()
    connection.close()
