import aiosqlite
from typing import Optional
from config import DB_PATH
from models import Module, Deadline


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS modules (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deadlines (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id   INTEGER REFERENCES modules(id) ON DELETE CASCADE,
                title       TEXT NOT NULL,
                due_date    DATE NOT NULL,
                due_time    TIME,
                notes       TEXT,
                created_by  INTEGER NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


# ── Module queries ────────────────────────────────────────────────────────────

async def add_module(name: str, description: Optional[str] = None) -> bool:
    """Returns True on success, False if name already exists."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO modules (name, description) VALUES (?, ?)",
                (name.upper(), description),
            )
            await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def get_all_modules() -> list[Module]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, name, description FROM modules ORDER BY name") as cur:
            rows = await cur.fetchall()
    return [Module(id=r["id"], name=r["name"], description=r["description"]) for r in rows]


async def get_module_by_name(name: str) -> Optional[Module]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, name, description FROM modules WHERE name = ?", (name.upper(),)
        ) as cur:
            row = await cur.fetchone()
    if row is None:
        return None
    return Module(id=row["id"], name=row["name"], description=row["description"])


async def delete_module(module_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM modules WHERE id = ?", (module_id,))
        await db.commit()
    return cur.rowcount > 0


# ── Deadline queries ──────────────────────────────────────────────────────────

async def add_deadline(
    module_id: int,
    title: str,
    due_date: str,
    due_time: Optional[str],
    notes: Optional[str],
    created_by: int,
) -> int:
    """Returns the new deadline's id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO deadlines (module_id, title, due_date, due_time, notes, created_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (module_id, title, due_date, due_time, notes, created_by),
        )
        await db.commit()
    return cur.lastrowid


async def get_all_deadlines() -> list[Deadline]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT d.id, d.module_id, m.name AS module_name, d.title,
                   d.due_date, d.due_time, d.notes, d.created_by
            FROM deadlines d
            JOIN modules m ON m.id = d.module_id
            ORDER BY d.due_date, d.due_time
        """) as cur:
            rows = await cur.fetchall()
    return [_row_to_deadline(r) for r in rows]


async def get_deadlines_due_within(days: int) -> list[Deadline]:
    """Returns deadlines due from today up to `days` days ahead (SGT date logic in SQL)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT d.id, d.module_id, m.name AS module_name, d.title,
                   d.due_date, d.due_time, d.notes, d.created_by
            FROM deadlines d
            JOIN modules m ON m.id = d.module_id
            WHERE d.due_date BETWEEN date('now', '+8 hours')
                              AND date('now', '+8 hours', ? || ' days')
            ORDER BY d.due_date, d.due_time
        """, (str(days),)) as cur:
            rows = await cur.fetchall()
    return [_row_to_deadline(r) for r in rows]


async def get_deadline_by_id(deadline_id: int) -> Optional[Deadline]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT d.id, d.module_id, m.name AS module_name, d.title,
                   d.due_date, d.due_time, d.notes, d.created_by
            FROM deadlines d
            JOIN modules m ON m.id = d.module_id
            WHERE d.id = ?
        """, (deadline_id,)) as cur:
            row = await cur.fetchone()
    return _row_to_deadline(row) if row else None


async def update_deadline(
    deadline_id: int,
    title: Optional[str] = None,
    due_date: Optional[str] = None,
    due_time: Optional[str] = None,
    notes: Optional[str] = None,
) -> bool:
    fields, values = [], []
    if title is not None:
        fields.append("title = ?"); values.append(title)
    if due_date is not None:
        fields.append("due_date = ?"); values.append(due_date)
    if due_time is not None:
        fields.append("due_time = ?"); values.append(due_time)
    if notes is not None:
        fields.append("notes = ?"); values.append(notes)
    if not fields:
        return False
    values.append(deadline_id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            f"UPDATE deadlines SET {', '.join(fields)} WHERE id = ?", values
        )
        await db.commit()
    return cur.rowcount > 0


async def delete_deadline(deadline_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM deadlines WHERE id = ?", (deadline_id,))
        await db.commit()
    return cur.rowcount > 0


def _row_to_deadline(row) -> Deadline:
    return Deadline(
        id=row["id"],
        module_id=row["module_id"],
        module_name=row["module_name"],
        title=row["title"],
        due_date=row["due_date"],
        due_time=row["due_time"],
        notes=row["notes"],
        created_by=row["created_by"],
    )
