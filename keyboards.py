"""
Keyboard definitions untuk Finance Tracker Bot.
Menggunakan aiogram 3.x InlineKeyboardBuilder.
"""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ──────────────────────────────────────
# Main menu
# ──────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Tambah Transaksi", callback_data="menu_add")
    builder.button(text="📋 Riwayat", callback_data="menu_history")
    builder.button(text="📊 Laporan", callback_data="menu_report")
    builder.button(text="🏷 Kategori", callback_data="menu_categories")
    builder.button(text="📤 Export CSV", callback_data="menu_export")
    builder.adjust(2)
    return builder.as_markup()


# ──────────────────────────────────────
# Tipe transaksi
# ──────────────────────────────────────

def type_selection_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Pemasukan", callback_data="tx_income")
    builder.button(text="💸 Pengeluaran", callback_data="tx_expense")
    builder.button(text="🔙 Batal / Menu", callback_data="menu_main")
    builder.adjust(2, 1)
    return builder.as_markup()


# ──────────────────────────────────────
# Kategori (dengan opsi tambah baru)
# ──────────────────────────────────────

def category_kb(categories: list[dict], tx_type: str) -> InlineKeyboardMarkup:
    """
    Bangun keyboard kategori untuk tipe tertentu (income/expense).
    Tambah tombol '➕ Tambah kategori baru' dan 'Kembali'.
    """
    builder = InlineKeyboardBuilder()

    for cat in categories:
        if cat["type"] == tx_type:
            builder.button(
                text=f"{cat['name']}",
                callback_data=f"cat_{cat['id']}",
            )

    builder.button(text="➕ Kategori Baru", callback_data="cat_new")
    builder.button(text="🔙 Batal", callback_data="confirm_no")
    builder.adjust(2)
    return builder.as_markup()


# ──────────────────────────────────────
# Input Catatan (Skip Option)
# ──────────────────────────────────────

def skip_note_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⏩ Lewati Catatan", callback_data="skip_note")
    builder.button(text="❌ Batal", callback_data="confirm_no")
    builder.adjust(1, 1)
    return builder.as_markup()


# ──────────────────────────────────────
# Konfirmasi transaksi
# ──────────────────────────────────────

def confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ya, Simpan", callback_data="confirm_yes")
    builder.button(text="❌ Batal", callback_data="confirm_no")
    builder.adjust(2)
    return builder.as_markup()


# ──────────────────────────────────────
# Pasca Simpan (Undo, Edit & Navigasi)
# ──────────────────────────────────────

def post_save_kb(tx_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Edit", callback_data=f"tx_edit_{tx_id}")
    builder.button(text="↩ Batalkan", callback_data=f"tx_undo_{tx_id}")
    builder.button(text="➕ Tambah Lagi", callback_data="menu_add")
    builder.button(text="🔙 Menu Utama", callback_data="menu_main")
    builder.adjust(2, 2)
    return builder.as_markup()


# ──────────────────────────────────────
# Menu Edit Transaksi
# ──────────────────────────────────────

def edit_tx_menu_kb(tx_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 Ubah Nominal", callback_data=f"tx_edamt_{tx_id}")
    builder.button(text="🏷 Ubah Kategori", callback_data=f"tx_edcat_{tx_id}")
    builder.button(text="📝 Ubah Catatan", callback_data=f"tx_ednote_{tx_id}")
    builder.button(text="🗑 Hapus Transaksi", callback_data=f"tx_undo_{tx_id}")
    builder.button(text="🔙 Selesai / Menu", callback_data="menu_main")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def edit_category_kb(categories: list[dict], tx_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat["name"], callback_data=f"tx_setcat_{tx_id}_{cat['id']}")
    builder.button(text="🔙 Batal", callback_data=f"tx_edit_{tx_id}")
    builder.adjust(2)
    return builder.as_markup()


def clear_note_kb(tx_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Kosongkan Catatan", callback_data=f"tx_clearnote_{tx_id}")
    builder.button(text="🔙 Batal", callback_data=f"tx_edit_{tx_id}")
    builder.adjust(1, 1)
    return builder.as_markup()


def cancel_edit_kb(tx_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Batal", callback_data=f"tx_edit_{tx_id}")
    return builder.as_markup()


def select_tx_to_edit_kb(transactions: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for tx in transactions:
        icon = "💰" if tx["type"] == "income" else "💸"
        note_display = f" • {tx['note'][:15]}" if tx.get("note") else ""
        date_short = tx["created_at"][5:10]
        builder.button(
            text=f"#{tx['id']} ({date_short}) {icon} {tx['category_name']}{note_display}",
            callback_data=f"tx_edit_{tx['id']}",
        )
    builder.button(text="🔙 Batal / Menu", callback_data="menu_main")
    builder.adjust(1)
    return builder.as_markup()


# ──────────────────────────────────────
# Riwayat: pagination & back
# ──────────────────────────────────────

def history_nav_kb(page: int, total_pages: int, period_arg: str = "") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    safe_period = period_arg if period_arg else "cur"

    if page > 1:
        builder.button(text="◀ Sebelumnya", callback_data=f"hist_p_{page - 1}_{safe_period}")

    builder.button(text=f"📄 {page}/{max(1, total_pages)}", callback_data="noop")

    if page < total_pages:
        builder.button(text="Selanjutnya ▶", callback_data=f"hist_p_{page + 1}_{safe_period}")

    builder.button(text="✏️ Edit Salah Satu Transaksi", callback_data="menu_select_edit")
    builder.button(text="🔙 Kembali ke Menu", callback_data="menu_main")
    builder.adjust(3 if (page > 1 and page < total_pages) else (2 if total_pages > 1 else 1), 1, 1)
    return builder.as_markup()


# ──────────────────────────────────────
# Laporan: pilih periode
# ──────────────────────────────────────

def report_period_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Bulan ini", callback_data="report_month_current")
    builder.button(text="📅 Minggu ini", callback_data="report_week_current")
    builder.button(text="🔙 Kembali ke Menu", callback_data="menu_main")
    builder.adjust(2, 1)
    return builder.as_markup()


# ──────────────────────────────────────
# Kategori: list dengan navigasi detail
# ──────────────────────────────────────

def categories_list_kb(categories: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        type_icon = "💰" if cat["type"] == "income" else "💸"
        builder.button(
            text=f"{type_icon} {cat['name']}",
            callback_data=f"cat_view_{cat['id']}",
        )
    builder.button(text="➕ Tambah Kategori", callback_data="cat_add_new")
    builder.button(text="🔙 Kembali", callback_data="menu_main")
    builder.adjust(2)
    return builder.as_markup()


def category_detail_kb(cat_id: int, is_default: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_default:
        builder.button(text="🗑 Hapus Kategori Ini", callback_data=f"cat_del_ask_{cat_id}")
    builder.button(text="🔙 Kembali ke Daftar", callback_data="menu_categories")
    builder.adjust(1)
    return builder.as_markup()


# ──────────────────────────────────────
# Hapus kategori konfirmasi
# ──────────────────────────────────────

def delete_cat_confirm_kb(cat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ya, Hapus", callback_data=f"cat_del_do_{cat_id}")
    builder.button(text="❌ Batal", callback_data=f"cat_view_{cat_id}")
    builder.adjust(2)
    return builder.as_markup()
