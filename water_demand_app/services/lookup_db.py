"""Client and location lookup tables for autocomplete."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from services.database import DB_PATH, init_db


def _conn(db_path: str = DB_PATH):
    init_db(db_path)
    return sqlite3.connect(db_path)


def init_lookup_tables(db_path: str = DB_PATH) -> None:
    init_db(db_path)
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            client_key TEXT PRIMARY KEY,
            client_name TEXT,
            address TEXT,
            engineer_name TEXT,
            contact TEXT,
            email TEXT,
            gst TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS locations (
            location_key TEXT PRIMARY KEY,
            city TEXT,
            state TEXT,
            rainfall_zone TEXT,
            climate TEXT,
            full_label TEXT
        )
        """
    )
    # Seed Pune if empty
    cur.execute("SELECT COUNT(*) FROM locations")
    if cur.fetchone()[0] == 0:
        cur.execute(
            """
            INSERT OR IGNORE INTO locations
            (location_key, city, state, rainfall_zone, climate, full_label)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("pune", "Pune", "Maharashtra", "Moderate", "Tropical Wet-Dry", "Pune, Maharashtra"),
        )
    conn.commit()
    conn.close()


def search_clients(prefix: str, limit: int = 8, db_path: str = DB_PATH) -> List[Dict[str, str]]:
    init_lookup_tables(db_path)
    key = (prefix or "").strip().lower()
    if not key:
        return []
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT client_key, client_name, address, engineer_name, contact, email, gst
        FROM clients
        WHERE client_key LIKE ? OR client_name LIKE ?
        ORDER BY client_name LIMIT ?
        """,
        (f"%{key}%", f"%{key}%", limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "client_key": r[0],
            "client_name": r[1] or "",
            "address": r[2] or "",
            "engineer_name": r[3] or "",
            "contact": r[4] or "",
            "email": r[5] or "",
            "gst": r[6] or "",
        }
        for r in rows
    ]


def upsert_client(record: Dict[str, str], db_path: str = DB_PATH) -> None:
    init_lookup_tables(db_path)
    name = record.get("client_name", "").strip()
    if not name:
        return
    key = name.lower().replace(" ", "_")[:40]
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO clients
        (client_key, client_name, address, engineer_name, contact, email, gst)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            key,
            name,
            record.get("address", ""),
            record.get("engineer_name", ""),
            record.get("contact", ""),
            record.get("email", ""),
            record.get("gst", ""),
        ),
    )
    conn.commit()
    conn.close()


def search_locations(prefix: str, limit: int = 8, db_path: str = DB_PATH) -> List[Dict[str, str]]:
    init_lookup_tables(db_path)
    key = (prefix or "").strip().lower()
    if not key:
        return []
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT location_key, city, state, rainfall_zone, climate, full_label
        FROM locations
        WHERE location_key LIKE ? OR city LIKE ? OR full_label LIKE ?
        ORDER BY city LIMIT ?
        """,
        (f"%{key}%", f"%{key}%", f"%{key}%", limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "location_key": r[0],
            "city": r[1] or "",
            "state": r[2] or "",
            "rainfall_zone": r[3] or "",
            "climate": r[4] or "",
            "full_label": r[5] or "",
        }
        for r in rows
    ]


def upsert_location(record: Dict[str, str], db_path: str = DB_PATH) -> None:
    init_lookup_tables(db_path)
    city = record.get("city", "").strip()
    if not city:
        return
    key = city.lower().replace(" ", "_")[:40]
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO locations
        (location_key, city, state, rainfall_zone, climate, full_label)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            key,
            city,
            record.get("state", ""),
            record.get("rainfall_zone", ""),
            record.get("climate", ""),
            record.get("full_label", city),
        ),
    )
    conn.commit()
    conn.close()


def next_project_number(db_path: str = DB_PATH) -> str:
    init_db(db_path)
    from datetime import datetime

    year = datetime.now().year
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT project_no FROM projects WHERE project_no LIKE ? ORDER BY project_no DESC LIMIT 1",
        (f"AE-{year}-%",),
    )
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        try:
            seq = int(str(row[0]).split("-")[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"AE-{year}-{seq:03d}"
