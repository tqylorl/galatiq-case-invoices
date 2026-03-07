from __future__ import annotations

import sqlite3
from pathlib import Path


SEED_ROWS = [
    ("WidgetA", 15),
    ("WidgetB", 10),
    ("GadgetX", 5),
    ("FakeItem", 0),
]


def bootstrap_inventory_db(db_path: Path) -> None:
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS inventory (item TEXT PRIMARY KEY, stock INTEGER NOT NULL)"
        )
        cursor.executemany(
            "INSERT OR REPLACE INTO inventory (item, stock) VALUES (?, ?)",
            SEED_ROWS,
        )
        connection.commit()
    finally:
        connection.close()


def get_inventory_stock(db_path: Path, item_name: str) -> int | None:
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT stock FROM inventory WHERE item = ?", (item_name,))
        row = cursor.fetchone()
        return None if row is None else int(row[0])
    finally:
        connection.close()
