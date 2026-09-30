"""
Database module untuk Finance Tracker Bot.
Menggunakan aiosqlite dengan SQLite lokal, WAL mode, dan foreign keys.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
import aiosqlite

DB_PATH = os.getenv("DB_PATH", "data/finance_bot.db")


# ──────────────────────────────────────
# Default categories
# ──────────────────────────────────────

DEFAULT_CATEGORIES = {
    "expense": [
        "Makanan",
        "Transportasi",
        "Belanja",
        "Tagihan",
        "Hiburan",
        "Kesehatan",
        "Lainnya",
    ],
    "income": [
        "Gaji",
        "Freelance",
        "Investasi",
        "Bonus",
        "Pendapatan Lainnya",
    ],
}


# ──────────────────────────────────────
# Schema
# ──────────────────────────────────────

CREATE_CATEGORIES_TABLE = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    is_default INTEGER DEFAULT 0
)
"""

CREATE_TRANSACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    amount REAL NOT NULL,
    category_id INTEGER NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id)
)
"""

CREATE_INDEX_TRANSACTIONS_CHAT_ID = """
CREATE INDEX IF NOT EXISTS idx_transactions_chat_id ON transactions(chat_id)
"""

CREATE_INDEX_TRANSACTIONS_CREATED_AT = """
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)
"""


# ──────────────────────────────────────
# Connection Helper
# ──────────────────────────────────────

@asynccontextmanager
async def get_db():
    """Async context manager untuk koneksi SQLite yang terkonfigurasi."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA busy_timeout = 5000;")
        yield db


# ──────────────────────────────────────
# Init DB
# ──────────────────────────────────────

async def init_db() -> None:
    """Buat tabel dan default categories kalau belum ada."""
    os.makedirs(os.path.dirname(DB_PATH) or "data", exist_ok=True)

    async with get_db() as db:
        await db.execute("PRAGMA journal_mode = WAL;")
        await db.execute(CREATE_CATEGORIES_TABLE)
        await db.execute(CREATE_TRANSACTIONS_TABLE)
        await db.execute(CREATE_INDEX_TRANSACTIONS_CHAT_ID)
        await db.execute(CREATE_INDEX_TRANSACTIONS_CREATED_AT)

        cursor = await db.execute("SELECT COUNT(*) FROM categories")
        count = (await cursor.fetchone())[0]

        if count == 0:
            rows = [
                (name, cat_type, 1)
                for cat_type, names in DEFAULT_CATEGORIES.items()
                for name in names
            ]
            await db.executemany(
                "INSERT INTO categories (name, type, is_default) VALUES (?, ?, ?)",
                rows,
            )

        await db.commit()


# ──────────────────────────────────────
# Categories
# ──────────────────────────────────────

async def get_categories(chat_id: int = 0, cat_type: Optional[str] = None) -> list[dict]:
    """Ambil semua kategori (opsional filter tipe income/expense)."""
    async with get_db() as db:
        if cat_type:
            cursor = await db.execute(
                "SELECT id, name, type, is_default FROM categories WHERE type = ? ORDER BY name",
                (cat_type,),
            )
        else:
            cursor = await db.execute(
                "SELECT id, name, type, is_default FROM categories ORDER BY type, name"
            )
        rows = await cursor.fetchall()
        return [
            {"id": r[0], "name": r[1], "type": r[2], "is_default": bool(r[3])}
            for r in rows
        ]


async def get_category_by_id(category_id: int) -> Optional[dict]:
    """Ambil satu kategori berdasarkan ID."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, name, type, is_default FROM categories WHERE id = ?",
            (category_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {"id": row[0], "name": row[1], "type": row[2], "is_default": bool(row[3])}


async def add_category(name: str, cat_type: str, is_default: int = 0) -> Optional[int]:
    """Tambah kategori baru. Mengembalikan category_id atau None jika duplikat."""
    cleaned_name = name.strip()
    try:
        async with get_db() as db:
            cursor = await db.execute(
                "INSERT INTO categories (name, type, is_default) VALUES (?, ?, ?)",
                (cleaned_name, cat_type, is_default),
            )
            await db.commit()
            return cursor.lastrowid
    except aiosqlite.IntegrityError:
        return None


async def delete_category(category_id: int) -> tuple[bool, str]:
    """
    Hapus kategori jika bukan bawaan dan tidak dipakai di transaksi.
    Return (success: bool, message: str).
    """
    async with get_db() as db:
        # Cek apakah kategori ada
        cursor = await db.execute(
            "SELECT is_default FROM categories WHERE id = ?",
            (category_id,),
        )
        cat = await cursor.fetchone()
        if not cat:
            return False, "Kategori tidak ditemukan."

        if cat[0] == 1:
            return False, "Kategori bawaan sistem tidak dapat dihapus."

        # Cek apakah digunakan dalam transaksi
        cursor = await db.execute(
            "SELECT COUNT(*) FROM transactions WHERE category_id = ?",
            (category_id,),
        )
        used = (await cursor.fetchone())[0]
        if used > 0:
            return False, f"Kategori masih digunakan dalam {used} transaksi."

        await db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        await db.commit()
        return True, "Kategori berhasil dihapus."


# ──────────────────────────────────────
# Transactions
# ──────────────────────────────────────

async def add_transaction(
    chat_id: int,
    tx_type: str,
    amount: float,
    category_id: int,
    note: str = "",
) -> int:
    """Tambah transaksi baru dan kembalikan id."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO transactions
               (chat_id, type, amount, category_id, note, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (chat_id, tx_type, amount, category_id, note, now),
        )
        await db.commit()
        return cursor.lastrowid


async def delete_transaction(tx_id: int, chat_id: int) -> bool:
    """Hapus transaksi berdasarkan ID dan chat_id pemilik."""
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM transactions WHERE id = ? AND chat_id = ?",
            (tx_id, chat_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_transaction(
    tx_id: int,
    chat_id: int,
    amount: Optional[float] = None,
    category_id: Optional[int] = None,
    note: Optional[str] = None,
) -> bool:
    """
    Update data transaksi (nominal, kategori, atau catatan).
    Hanya kolom yang bukan None yang akan diupdate.
    """
    fields = []
    params = []
    if amount is not None:
        fields.append("amount = ?")
        params.append(amount)
    if category_id is not None:
        fields.append("category_id = ?")
        params.append(category_id)
    if note is not None:
        fields.append("note = ?")
        params.append(note)

    if not fields:
        return False

    params.extend([tx_id, chat_id])
    sql = f"UPDATE transactions SET {', '.join(fields)} WHERE id = ? AND chat_id = ?"

    async with get_db() as db:
        cursor = await db.execute(sql, params)
        await db.commit()
        return cursor.rowcount > 0


async def get_transaction_by_id(tx_id: int, chat_id: int) -> Optional[dict]:
    """Ambil rincian satu transaksi."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT t.id, t.type, t.amount, t.note, t.created_at, c.name AS category_name
               FROM transactions t
               JOIN categories c ON t.category_id = c.id
               WHERE t.id = ? AND t.chat_id = ?""",
            (tx_id, chat_id),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "type": row[1],
            "amount": row[2],
            "note": row[3] or "",
            "created_at": row[4],
            "category_name": row[5],
        }


async def count_transactions(
    chat_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> int:
    """Hitung total transaksi pengguna dalam rentang tanggal."""
    async with get_db() as db:
        sql = "SELECT COUNT(*) FROM transactions WHERE chat_id = ?"
        params: list = [chat_id]
        if start_date:
            sql += " AND created_at >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND created_at <= ?"
            params.append(end_date)
        cursor = await db.execute(sql, params)
        return (await cursor.fetchone())[0]


async def get_transactions(
    chat_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """Ambil daftar transaksi dengan filter tanggal dan paginasi."""
    async with get_db() as db:
        sql = """
            SELECT t.id, t.type, t.amount, t.note, t.created_at,
                   c.name AS category_name
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.chat_id = ?
        """
        params: list = [chat_id]

        if start_date:
            sql += " AND t.created_at >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND t.created_at <= ?"
            params.append(end_date)

        sql += " ORDER BY t.created_at DESC, t.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "type": r[1],
                "amount": r[2],
                "note": r[3] or "",
                "created_at": r[4],
                "category_name": r[5],
            }
            for r in rows
        ]


# ──────────────────────────────────────
# Reports
# ──────────────────────────────────────

async def get_report(
    chat_id: int,
    start_date: str,
    end_date: str,
) -> dict:
    """Hitung total pemasukan, pengeluaran, dan breakdown per kategori untuk periode tertentu."""
    async with get_db() as db:
        # Total pemasukan
        cursor = await db.execute(
            """SELECT SUM(amount) FROM transactions
               WHERE chat_id = ? AND type = 'income'
               AND created_at >= ? AND created_at <= ?""",
            (chat_id, start_date, end_date),
        )
        total_income = (await cursor.fetchone())[0] or 0.0

        # Total pengeluaran
        cursor = await db.execute(
            """SELECT SUM(amount) FROM transactions
               WHERE chat_id = ? AND type = 'expense'
               AND created_at >= ? AND created_at <= ?""",
            (chat_id, start_date, end_date),
        )
        total_expense = (await cursor.fetchone())[0] or 0.0

        # Breakdown pengeluaran per kategori
        cursor = await db.execute(
            """SELECT c.name, SUM(t.amount)
               FROM transactions t
               JOIN categories c ON t.category_id = c.id
               WHERE t.chat_id = ? AND t.type = 'expense'
               AND t.created_at >= ? AND t.created_at <= ?
               GROUP BY c.name
               ORDER BY SUM(t.amount) DESC""",
            (chat_id, start_date, end_date),
        )
        expense_breakdown = [
            {"category": r[0], "amount": r[1]}
            for r in await cursor.fetchall()
        ]

        # Breakdown pemasukan per kategori
        cursor = await db.execute(
            """SELECT c.name, SUM(t.amount)
               FROM transactions t
               JOIN categories c ON t.category_id = c.id
               WHERE t.chat_id = ? AND t.type = 'income'
               AND t.created_at >= ? AND t.created_at <= ?
               GROUP BY c.name
               ORDER BY SUM(t.amount) DESC""",
            (chat_id, start_date, end_date),
        )
        income_breakdown = [
            {"category": r[0], "amount": r[1]}
            for r in await cursor.fetchall()
        ]

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_income": total_income,
            "total_expense": total_expense,
            "net": total_income - total_expense,
            "expense_breakdown": expense_breakdown,
            "income_breakdown": income_breakdown,
        }
