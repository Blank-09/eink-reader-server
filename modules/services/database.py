import sqlite3

DB_NAME = "epaper.db"


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_state (
                id INTEGER PRIMARY KEY,
                mode TEXT DEFAULT 'LIBRARIES',  -- Options: LIBRARIES, SERIES, BOOKS, READER

                -- Selections (Context)
                selected_library_id INTEGER DEFAULT 0,
                selected_series_id INTEGER DEFAULT 0,
                selected_book_id INTEGER DEFAULT 0,

                -- Navigation State
                cursor_index INTEGER DEFAULT 0,
                current_page INTEGER DEFAULT 0,  -- Kavita API Page Index
                scroll_step INTEGER DEFAULT 0,   -- Vertical Scroll Index (0, 1, 2...)
                
                -- Display Settings
                orientation INTEGER DEFAULT 0,         -- 0=Landscape, 1=Portrait
                dither_mode TEXT DEFAULT 'THRESHOLD',  -- 'THRESHOLD' or 'FLOYD'

                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("INSERT OR IGNORE INTO device_state (id) VALUES (1)")
        conn.commit()


def get_state():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        return dict(conn.cursor().execute("SELECT * FROM device_state WHERE id = 1").fetchone())


def update_state(updates: dict):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        keys = list(updates.keys())
        values = list(updates.values())
        set_clause = ", ".join([f"{k} = ?" for k in keys])
        cursor.execute(f"UPDATE device_state SET {set_clause} WHERE id = 1", values)
        conn.commit()
