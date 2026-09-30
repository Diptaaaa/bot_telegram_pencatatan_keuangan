"""
Test script untuk verifikasi modul db, utils, dan alur data finance-bot.
"""

import asyncio
import os
import shutil
import tempfile
import unittest

# Gunakan temp DB agar tidak mengotori database utama saat testing
import db
from utils import (
    format_period_label,
    format_rp,
    generate_csv,
    generate_progress_bar,
    month_end,
    month_start,
    parse_amount,
    parse_quick_add,
)


class TestUtils(unittest.TestCase):
    def test_format_rp(self):
        self.assertEqual(format_rp(1200000), "Rp 1.200.000")
        self.assertEqual(format_rp(50000), "Rp 50.000")
        self.assertEqual(format_rp(0), "Rp 0")

    def test_parse_amount(self):
        # Format ribuan & teks Indonesia
        self.assertEqual(parse_amount("50k"), 50000.0)
        self.assertEqual(parse_amount("50rb"), 50000.0)
        self.assertEqual(parse_amount("1.5jt"), 1500000.0)
        self.assertEqual(parse_amount("1,5jt"), 1500000.0)
        self.assertEqual(parse_amount("50000"), 50000.0)
        self.assertEqual(parse_amount("50.000"), 50000.0)
        self.assertEqual(parse_amount("Rp 25.000"), 25000.0)
        self.assertEqual(parse_amount("rp 100k"), 100000.0)
        # Invalid cases
        self.assertIsNone(parse_amount("0"))
        self.assertIsNone(parse_amount("-5000"))
        self.assertIsNone(parse_amount("abc"))

    def test_parse_quick_add(self):
        exp = parse_quick_add("- 25k makan siang")
        self.assertIsNotNone(exp)
        self.assertEqual(exp["type"], "expense")
        self.assertEqual(exp["amount"], 25000.0)
        self.assertEqual(exp["note"], "makan siang")

        inc = parse_quick_add("+ 5jt gaji bulanan")
        self.assertIsNotNone(inc)
        self.assertEqual(inc["type"], "income")
        self.assertEqual(inc["amount"], 5000000.0)
        self.assertEqual(inc["note"], "gaji bulanan")

        self.assertIsNone(parse_quick_add("halo apa kabar"))

    def test_generate_progress_bar(self):
        self.assertEqual(generate_progress_bar(50, length=10), "█████░░░░░")
        self.assertEqual(generate_progress_bar(100, length=10), "██████████")
        self.assertEqual(generate_progress_bar(0, length=10), "░░░░░░░░░░")


class TestDatabaseAsync(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db_path = os.path.join(self.temp_dir, "test_finance.db")
        db.DB_PATH = self.temp_db_path
        await db.init_db()

    async def asyncTearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_categories_and_protection(self):
        cats = await db.get_categories()
        self.assertGreater(len(cats), 5)

        # Coba hapus kategori default -> HARUS DITOLAK
        makanan_cat = next(c for c in cats if c["name"] == "Makanan")
        success, msg = await db.delete_category(makanan_cat["id"])
        self.assertFalse(success)
        self.assertIn("bawaan", msg)

        # Tambah custom category
        new_id = await db.add_category("Langganan Gym", "expense")
        self.assertIsNotNone(new_id)

        # Hapus custom category yang belum dipakai -> HARUS BERHASIL
        success_del, _ = await db.delete_category(new_id)
        self.assertTrue(success_del)

    async def test_transaction_crud_and_report(self):
        chat_id = 999
        cats = await db.get_categories()
        makanan_id = next(c for c in cats if c["name"] == "Makanan")["id"]
        gaji_id = next(c for c in cats if c["name"] == "Gaji")["id"]

        # Tambah transaksi
        tx1 = await db.add_transaction(chat_id, "expense", 25000.0, makanan_id, "nasi padang")
        tx2 = await db.add_transaction(chat_id, "income", 1000000.0, gaji_id, "gaji part-time")

        # Cek count & get
        count = await db.count_transactions(chat_id)
        self.assertEqual(count, 2)

        txs = await db.get_transactions(chat_id, limit=10)
        self.assertEqual(len(txs), 2)

        # Cek laporan
        start = month_start()
        end = month_end()
        report = await db.get_report(chat_id, start, end)
        self.assertEqual(report["total_income"], 1000000.0)
        self.assertEqual(report["total_expense"], 25000.0)
        self.assertEqual(report["net"], 975000.0)

        # Cek fitur hapus / undo
        deleted = await db.delete_transaction(tx1, chat_id)
        self.assertTrue(deleted)
        self.assertEqual(await db.count_transactions(chat_id), 1)

    async def test_update_transaction(self):
        chat_id = 999
        cats = await db.get_categories()
        makanan_id = next(c for c in cats if c["name"] == "Makanan")["id"]
        transport_id = next(c for c in cats if c["name"] == "Transportasi")["id"]

        tx_id = await db.add_transaction(chat_id, "expense", 50000.0, makanan_id, "makan siang")

        # 1. Update nominal saja
        ok = await db.update_transaction(tx_id, chat_id, amount=75000.0)
        self.assertTrue(ok)
        tx = await db.get_transaction_by_id(tx_id, chat_id)
        self.assertEqual(tx["amount"], 75000.0)
        self.assertEqual(tx["category_name"], "Makanan")

        # 2. Update kategori saja
        ok = await db.update_transaction(tx_id, chat_id, category_id=transport_id)
        self.assertTrue(ok)
        tx = await db.get_transaction_by_id(tx_id, chat_id)
        self.assertEqual(tx["category_name"], "Transportasi")

        # 3. Update catatan saja
        ok = await db.update_transaction(tx_id, chat_id, note="bensin motor")
        self.assertTrue(ok)
        tx = await db.get_transaction_by_id(tx_id, chat_id)
        self.assertEqual(tx["note"], "bensin motor")

        # 4. Keamanan: User lain coba ubah transaksi orang lain -> HARUS DITOLAK
        other_user = 888
        ok = await db.update_transaction(tx_id, other_user, amount=10000.0)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
