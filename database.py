import asyncpg
from datetime import date
from typing import Optional
from config import DATABASE_URL
from models import Module, Deadline


async def _conn() -> asyncpg.Connection:
    return await asyncpg.connect(DATABASE_URL)


async def init_db() -> None:
    conn = await _conn()
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS modules (
                id          SERIAL PRIMARY KEY,
                name        TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS deadlines (
                id          SERIAL PRIMARY KEY,
                module_id   INTEGER REFERENCES modules(id) ON DELETE CASCADE,
                title       TEXT NOT NULL,
                due_date    DATE NOT NULL,
                due_time    TEXT,
                notes       TEXT,
                created_by  BIGINT NOT NULL,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    finally:
        await conn.close()


# ── Module queries ────────────────────────────────────────────────────────────

async def add_module(name: str, description: Optional[str] = None) -> bool:
    """Returns True on success, False if name already exists."""
    conn = await _conn()
    try:
        await conn.execute(
            "INSERT INTO modules (name, description) VALUES ($1, $2)",
            name.upper(), description,
        )
        return True
    except asyncpg.UniqueViolationError:
        return False
    finally:
        await conn.close()


async def get_all_modules() -> list[Module]:
    conn = await _conn()
    try:
        rows = await conn.fetch("SELECT id, name, description FROM modules ORDER BY name")
    finally:
        await conn.close()
    return [Module(id=r["id"], name=r["name"], description=r["description"]) for r in rows]


async def get_module_by_name(name: str) -> Optional[Module]:
    conn = await _conn()
    try:
        row = await conn.fetchrow(
            "SELECT id, name, description FROM modules WHERE name = $1", name.upper()
        )
    finally:
        await conn.close()
    if row is None:
        return None
    return Module(id=row["id"], name=row["name"], description=row["description"])


async def delete_module(module_id: int) -> bool:
    conn = await _conn()
    try:
        result = await conn.execute("DELETE FROM modules WHERE id = $1", module_id)
    finally:
        await conn.close()
    return result != "DELETE 0"


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
    conn = await _conn()
    try:
        row = await conn.fetchrow(
            """INSERT INTO deadlines (module_id, title, due_date, due_time, notes, created_by)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            module_id, title, date.fromisoformat(due_date), due_time, notes, created_by,
        )
    finally:
        await conn.close()
    return row["id"]


async def get_all_deadlines() -> list[Deadline]:
    conn = await _conn()
    try:
        rows = await conn.fetch("""
            SELECT d.id, d.module_id, m.name AS module_name, d.title,
                   d.due_date, d.due_time, d.notes, d.created_by
            FROM deadlines d
            JOIN modules m ON m.id = d.module_id
            ORDER BY d.due_date, d.due_time
        """)
    finally:
        await conn.close()
    return [_row_to_deadline(r) for r in rows]


async def get_deadlines_due_within(days: int) -> list[Deadline]:
    """Returns deadlines due from today up to `days` days ahead (SGT date logic)."""
    conn = await _conn()
    try:
        rows = await conn.fetch("""
            SELECT d.id, d.module_id, m.name AS module_name, d.title,
                   d.due_date, d.due_time, d.notes, d.created_by
            FROM deadlines d
            JOIN modules m ON m.id = d.module_id
            WHERE d.due_date >= (NOW() AT TIME ZONE 'Asia/Singapore')::DATE
              AND d.due_date <= (NOW() AT TIME ZONE 'Asia/Singapore')::DATE + $1
            ORDER BY d.due_date, d.due_time
        """, days)
    finally:
        await conn.close()
    return [_row_to_deadline(r) for r in rows]


async def get_deadline_by_id(deadline_id: int) -> Optional[Deadline]:
    conn = await _conn()
    try:
        row = await conn.fetchrow("""
            SELECT d.id, d.module_id, m.name AS module_name, d.title,
                   d.due_date, d.due_time, d.notes, d.created_by
            FROM deadlines d
            JOIN modules m ON m.id = d.module_id
            WHERE d.id = $1
        """, deadline_id)
    finally:
        await conn.close()
    return _row_to_deadline(row) if row else None


async def update_deadline(
    deadline_id: int,
    title: Optional[str] = None,
    due_date: Optional[str] = None,
    due_time: Optional[str] = None,
    notes: Optional[str] = None,
) -> bool:
    fields, values = [], []
    idx = 1
    if title is not None:
        fields.append(f"title = ${idx}"); values.append(title); idx += 1
    if due_date is not None:
        fields.append(f"due_date = ${idx}"); values.append(date.fromisoformat(due_date)); idx += 1
    if due_time is not None:
        fields.append(f"due_time = ${idx}"); values.append(due_time or None); idx += 1
    if notes is not None:
        fields.append(f"notes = ${idx}"); values.append(notes or None); idx += 1
    if not fields:
        return False
    values.append(deadline_id)
    conn = await _conn()
    try:
        result = await conn.execute(
            f"UPDATE deadlines SET {', '.join(fields)} WHERE id = ${idx}",
            *values,
        )
    finally:
        await conn.close()
    return result != "UPDATE 0"


async def delete_deadline(deadline_id: int) -> bool:
    conn = await _conn()
    try:
        result = await conn.execute("DELETE FROM deadlines WHERE id = $1", deadline_id)
    finally:
        await conn.close()
    return result != "DELETE 0"


def _row_to_deadline(row) -> Deadline:
    return Deadline(
        id=row["id"],
        module_id=row["module_id"],
        module_name=row["module_name"],
        title=row["title"],
        due_date=row["due_date"].isoformat(),
        due_time=row["due_time"],
        notes=row["notes"],
        created_by=row["created_by"],
    )
