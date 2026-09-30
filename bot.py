"""
Finance Tracker Telegram Bot - Entry point dengan FSM wizard, Quick-Add, dan Visual Report.
Menggunakan aiogram 3.x + aiosqlite.
"""

import asyncio
import datetime
import logging
import math
import os
import re
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from dotenv import load_dotenv

from db import (
    add_category,
    add_transaction,
    count_transactions,
    delete_category,
    delete_transaction,
    get_categories,
    get_category_by_id,
    get_report,
    get_transaction_by_id,
    get_transactions,
    init_db,
    update_transaction,
)
from keyboards import (
    cancel_edit_kb,
    categories_list_kb,
    category_detail_kb,
    category_kb,
    clear_note_kb,
    confirm_kb,
    delete_cat_confirm_kb,
    edit_category_kb,
    edit_tx_menu_kb,
    history_nav_kb,
    main_menu_kb,
    post_save_kb,
    report_period_kb,
    select_tx_to_edit_kb,
    skip_note_kb,
    type_selection_kb,
)
from utils import (
    format_period_label,
    format_rp,
    generate_csv,
    generate_progress_bar,
    month_end,
    month_start,
    parse_amount,
    parse_period_date,
    parse_quick_add,
    week_end_iso,
    week_start_iso,
)

# ──────────────────────────────────────
# Config & Setup
# ──────────────────────────────────────

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN tidak ditemukan di .env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)


def check_auth(chat_id: int) -> bool:
    """Cek apakah user diizinkan jika ADMIN_CHAT_ID disetel."""
    if not ADMIN_CHAT_ID:
        return True
    return str(chat_id) == ADMIN_CHAT_ID


async def reject_unauthorized(event: Message | CallbackQuery):
    msg = "⛔ *Akses Ditolak*\nBot ini disetel dalam mode pribadi untuk pemilik."
    if isinstance(event, CallbackQuery):
        await event.answer("Akses ditolak: Bot pribadi.", show_alert=True)
    else:
        await event.answer(msg, parse_mode="Markdown")


# ──────────────────────────────────────
# FSM States
# ──────────────────────────────────────

class AddTransaction(StatesGroup):
    type = State()
    category = State()
    amount = State()
    note = State()
    confirm = State()


class AddCategoryWizard(StatesGroup):
    name = State()
    type = State()


class EditTransaction(StatesGroup):
    amount = State()
    note = State()


# ──────────────────────────────────────
# Helper: Show Main Menu
# ──────────────────────────────────────

async def show_main_menu(event: Message | CallbackQuery):
    text = (
        "💰 *Finance Tracker Bot*\n\n"
        "Pencatat keuangan pribadi Anda.\n\n"
        "⚡ *Quick-Add (Cepat):*\n"
        "Ketik langsung di chat:\n"
        "• `- 25k makan siang` *(Pengeluaran)*\n"
        "• `+ 5jt gaji bulanan` *(Pemasukan)*\n\n"
        "Atau gunakan menu tombol di bawah:"
    )
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(
                text,
                reply_markup=main_menu_kb(),
                parse_mode="Markdown",
            )
        except Exception:
            await event.message.answer(
                text,
                reply_markup=main_menu_kb(),
                parse_mode="Markdown",
            )
        await event.answer()
    else:
        await event.answer(
            text,
            reply_markup=main_menu_kb(),
            parse_mode="Markdown",
        )


# ──────────────────────────────────────
# Commands: /start, /help, /cancel
# ──────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    if not check_auth(message.chat.id):
        await reject_unauthorized(message)
        return

    await state.clear()
    logger.info(f"User {message.chat.id} started bot")
    await show_main_menu(message)


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    if not check_auth(message.chat.id):
        await reject_unauthorized(message)
        return

    await state.clear()
    help_text = (
        "📋 *Bantuan Perintah:*\n\n"
        "/start: Tampilkan menu utama\n"
        "/add: Tambah transaksi dengan wizard panduan\n"
        "/history: Riwayat transaksi (opsional: `/history 2026-09`)\n"
        "/edit: Edit transaksi tersimpan (opsional: `/edit ID`)\n"
        "/report: Laporan keuangan bulanan/mingguan\n"
        "/categories: Kelola kategori pemasukan & pengeluaran\n"
        "/export: Unduh data transaksi dalam file CSV\n"
        "/cancel: Batalkan wizard yang sedang aktif\n\n"
        "💡 *Tips Cepat:* Anda bisa mencatat langsung tanpa menu:\n"
        "`- 15k kopi tubruk`\n"
        "`+ 500k freelance desain`"
    )
    await message.answer(help_text, reply_markup=main_menu_kb(), parse_mode="Markdown")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer(
            "❌ *Proses dibatalkan.*\nKembali ke menu utama:",
            reply_markup=main_menu_kb(),
            parse_mode="Markdown",
        )
    else:
        await message.answer(
            "Tidak ada proses yang sedang berjalan.",
            reply_markup=main_menu_kb(),
        )


# ──────────────────────────────────────
# Wizard /add: Step 1 (Pilih Tipe)
# ──────────────────────────────────────

@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    if not check_auth(message.chat.id):
        await reject_unauthorized(message)
        return

    await state.set_state(AddTransaction.type)
    await message.answer(
        "Pilih tipe transaksi:",
        reply_markup=type_selection_kb(),
    )


@router.callback_query(F.data.in_(["tx_income", "tx_expense"]), StateFilter(AddTransaction.type))
async def cb_select_type(callback: CallbackQuery, state: FSMContext):
    tx_type = "income" if callback.data == "tx_income" else "expense"
    await state.update_data(tx_type=tx_type)
    await state.set_state(AddTransaction.category)

    categories = await get_categories(callback.message.chat.id, tx_type)
    label = "Pemasukan 💰" if tx_type == "income" else "Pengeluaran 💸"

    await callback.message.edit_text(
        f"Pilih kategori *{label}*:",
        reply_markup=category_kb(categories, tx_type),
        parse_mode="Markdown",
    )
    await callback.answer()


# ──────────────────────────────────────
# Wizard: Step 2 (Pilih atau Tambah Kategori)
# ──────────────────────────────────────

@router.callback_query(F.data == "cat_new", StateFilter(AddTransaction.category))
async def cb_cat_new_in_wizard(callback: CallbackQuery):
    await callback.message.edit_text(
        "Ketik nama kategori baru yang Anda inginkan:\n"
        "_(Contoh: `Skincare`, `Langganan`, `Pendidikan`)_",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_"), StateFilter(AddTransaction.category))
async def cb_select_category(callback: CallbackQuery, state: FSMContext):
    try:
        cat_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("Kategori tidak valid.", show_alert=True)
        return

    cat = await get_category_by_id(cat_id)
    if not cat:
        await callback.answer("Kategori tidak ditemukan.", show_alert=True)
        return

    await state.update_data(category_id=cat_id, category_name=cat["name"])
    await state.set_state(AddTransaction.amount)

    await callback.message.edit_text(
        f"Kategori terpilih: *{cat['name']}*\n\n"
        f"Sekarang masukkan *nominal jumlah*:\n"
        f"_(Mendukung `50k`, `50rb`, `1.5jt`, `50.000`, `50000`)_",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(StateFilter(AddTransaction.category), F.text)
async def txt_new_category_in_wizard(message: Message, state: FSMContext):
    cat_name = message.text.strip()
    if not cat_name:
        await message.answer("Nama kategori tidak boleh kosong. Silakan ketik nama kategori:")
        return

    state_data = await state.get_data()
    tx_type = state_data.get("tx_type", "expense")

    existing = await get_categories(message.chat.id, tx_type)
    matched = next((c for c in existing if c["name"].lower() == cat_name.lower()), None)

    if matched:
        cat_id = matched["id"]
        cat_name = matched["name"]
    else:
        cat_id = await add_category(cat_name, tx_type)
        if not cat_id:
            # Jika nama sama ada di tipe lain dan terbentur constraint
            await message.answer("Nama kategori sudah digunakan. Silakan gunakan nama lain:")
            return

    await state.update_data(category_id=cat_id, category_name=cat_name)
    await state.set_state(AddTransaction.amount)

    await message.answer(
        f"✅ Kategori *{cat_name}* dipilih.\n\n"
        f"Sekarang masukkan *nominal jumlah*:\n"
        f"_(Mendukung `50k`, `50rb`, `1.5jt`, `50.000`)_",
        parse_mode="Markdown",
    )


# ──────────────────────────────────────
# Wizard: Step 3 (Input Nominal)
# ──────────────────────────────────────

@router.message(StateFilter(AddTransaction.amount), F.text)
async def txt_amount(message: Message, state: FSMContext):
    amount = parse_amount(message.text)
    if not amount or amount <= 0:
        await message.answer(
            "⚠️ Nominal tidak valid. Coba lagi, contoh:\n"
            "`50000`, `50.000`, `50k`, `50rb`, atau `1.5jt`",
            parse_mode="Markdown",
        )
        return

    await state.update_data(amount=amount)
    await state.set_state(AddTransaction.note)

    await message.answer(
        f"Nominal: *{format_rp(amount)}*\n\n"
        f"Ketik *catatan transaksi* (atau tekan tombol Lewati di bawah):",
        reply_markup=skip_note_kb(),
        parse_mode="Markdown",
    )


# ──────────────────────────────────────
# Wizard: Step 4 (Catatan & Konfirmasi)
# ──────────────────────────────────────

@router.callback_query(F.data == "skip_note", StateFilter(AddTransaction.note))
async def cb_skip_note(callback: CallbackQuery, state: FSMContext):
    await state.update_data(note="")
    await show_confirmation(callback.message, state, is_edit=True)
    await callback.answer()


@router.message(StateFilter(AddTransaction.note), F.text)
async def txt_note(message: Message, state: FSMContext):
    note = message.text.strip()
    if note == "-":
        note = ""
    await state.update_data(note=note)
    await show_confirmation(message, state, is_edit=False)


async def show_confirmation(message: Message, state: FSMContext, is_edit: bool = False):
    await state.set_state(AddTransaction.confirm)
    data = await state.get_data()

    tx_label = "Pemasukan 💰" if data["tx_type"] == "income" else "Pengeluaran 💸"
    text = (
        "📋 *Konfirmasi Transaksi:*\n\n"
        f"• Tipe      : *{tx_label}*\n"
        f"• Kategori  : *{data['category_name']}*\n"
        f"• Jumlah    : *{format_rp(data['amount'])}*\n"
        f"• Catatan   : {data['note'] or '-'}\n\n"
        "Apakah data transaksi sudah benar?"
    )
    if is_edit:
        await message.edit_text(text, reply_markup=confirm_kb(), parse_mode="Markdown")
    else:
        await message.answer(text, reply_markup=confirm_kb(), parse_mode="Markdown")


# ──────────────────────────────────────
# Wizard: Step 5 (Simpan / Batal)
# ──────────────────────────────────────

@router.callback_query(F.data == "confirm_yes", StateFilter(AddTransaction.confirm))
async def cb_confirm_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chat_id = callback.message.chat.id

    tx_id = await add_transaction(
        chat_id=chat_id,
        tx_type=data["tx_type"],
        amount=data["amount"],
        category_id=data["category_id"],
        note=data.get("note", ""),
    )

    type_icon = "💰 Pemasukan" if data["tx_type"] == "income" else "💸 Pengeluaran"
    note_str = f" ({data['note']})" if data.get("note") else ""

    await state.clear()
    await callback.message.edit_text(
        f"✅ *Transaksi Berhasil Disimpan!*\n\n"
        f"• ID: `#{tx_id}`\n"
        f"• {type_icon}: *{format_rp(data['amount'])}*\n"
        f"• Kategori: *{data['category_name']}*{note_str}",
        reply_markup=post_save_kb(tx_id),
        parse_mode="Markdown",
    )
    await callback.answer("Tersimpan!")


@router.callback_query(F.data == "confirm_no", StateFilter(AddTransaction))
async def cb_confirm_no(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Transaksi dibatalkan.")
    await callback.answer()
    await show_main_menu(callback)


# ──────────────────────────────────────
# Fitur Undo / Batalkan Transaksi
# ──────────────────────────────────────

@router.callback_query(F.data.startswith("tx_undo_"))
async def cb_undo_transaction(callback: CallbackQuery):
    try:
        tx_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("ID Transaksi tidak valid.", show_alert=True)
        return

    chat_id = callback.message.chat.id
    tx = await get_transaction_by_id(tx_id, chat_id)
    if not tx:
        await callback.answer("Transaksi tidak ditemukan atau sudah dihapus.", show_alert=True)
        return

    success = await delete_transaction(tx_id, chat_id)
    if success:
        await callback.message.edit_text(
            f"↩ *Transaksi #{tx_id} Dibatalkan!*\n"
            f"Data {tx['category_name']} senilai {format_rp(tx['amount'])} telah dihapus.",
            reply_markup=main_menu_kb(),
            parse_mode="Markdown",
        )
        await callback.answer("Berhasil dibatalkan.")
    else:
        await callback.answer("Gagal membatalkan transaksi.", show_alert=True)


# ──────────────────────────────────────
# Fitur Edit Transaksi (Mengatasi Human Error)
# ──────────────────────────────────────

async def show_edit_card(event_msg: Message, tx_id: int, chat_id: int, is_edit_msg: bool = True):
    tx = await get_transaction_by_id(tx_id, chat_id)
    if not tx:
        text = f"⚠️ Transaksi `#{tx_id}` tidak ditemukan atau sudah dihapus."
        if is_edit_msg:
            await event_msg.edit_text(text, reply_markup=main_menu_kb(), parse_mode="Markdown")
        else:
            await event_msg.answer(text, reply_markup=main_menu_kb(), parse_mode="Markdown")
        return

    type_label = "Pemasukan 💰" if tx["type"] == "income" else "Pengeluaran 💸"
    card_text = (
        f"✏️ *Edit Transaksi #{tx['id']}*\n\n"
        f"• Tipe      : *{type_label}*\n"
        f"• Kategori  : *{tx['category_name']}*\n"
        f"• Nominal   : *{format_rp(tx['amount'])}*\n"
        f"• Catatan   : {tx['note'] or '-'}\n"
        f"• Waktu     : `{tx['created_at']}`\n\n"
        "_Pilih bagian yang ingin diubah:_"
    )
    if is_edit_msg:
        try:
            await event_msg.edit_text(card_text, reply_markup=edit_tx_menu_kb(tx_id), parse_mode="Markdown")
        except Exception:
            await event_msg.answer(card_text, reply_markup=edit_tx_menu_kb(tx_id), parse_mode="Markdown")
    else:
        await event_msg.answer(card_text, reply_markup=edit_tx_menu_kb(tx_id), parse_mode="Markdown")


@router.message(Command("edit"))
async def cmd_edit(message: Message, state: FSMContext):
    if not check_auth(message.chat.id):
        await reject_unauthorized(message)
        return

    await state.clear()
    args = message.text.split()
    if len(args) > 1:
        try:
            tx_id = int(args[1].replace("#", ""))
            await show_edit_card(message, tx_id, message.chat.id, is_edit_msg=False)
            return
        except ValueError:
            pass

    # Ambil 6 transaksi terbaru untuk dipilih langsung oleh pengguna
    transactions = await get_transactions(message.chat.id, limit=6, offset=0)
    if not transactions:
        await message.answer("Belum ada transaksi untuk diedit.", reply_markup=main_menu_kb())
        return

    await message.answer(
        "✏️ *Pilih Transaksi yang Ingin Diedit:*",
        reply_markup=select_tx_to_edit_kb(transactions),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "menu_select_edit")
async def cb_menu_select_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    transactions = await get_transactions(callback.message.chat.id, limit=8, offset=0)
    if not transactions:
        await callback.answer("Belum ada transaksi.", show_alert=True)
        return

    await callback.message.edit_text(
        "✏️ *Pilih Transaksi yang Ingin Diedit:*",
        reply_markup=select_tx_to_edit_kb(transactions),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tx_edit_"))
async def cb_open_edit_tx(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        tx_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("ID Transaksi tidak valid.", show_alert=True)
        return

    await show_edit_card(callback.message, tx_id, callback.message.chat.id, is_edit_msg=True)
    await callback.answer()


@router.callback_query(F.data.startswith("tx_edamt_"))
async def cb_edit_amount_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        tx_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        return

    chat_id = callback.message.chat.id
    tx = await get_transaction_by_id(tx_id, chat_id)
    if not tx:
        await callback.message.edit_text("Transaksi tidak ditemukan.", reply_markup=main_menu_kb())
        return

    await state.set_state(EditTransaction.amount)
    await state.update_data(edit_tx_id=tx_id)

    await callback.message.edit_text(
        f"💵 *Ubah Nominal Transaksi #{tx_id}*\n\n"
        f"Nominal saat ini: *{format_rp(tx['amount'])}*\n\n"
        f"Silakan ketik nominal baru:\n"
        f"_(Contoh: 50k, 50rb, 1.5jt, atau 50.000)_",
        reply_markup=cancel_edit_kb(tx_id),
        parse_mode="Markdown",
    )


@router.message(StateFilter(EditTransaction.amount), F.text)
async def txt_edit_amount(message: Message, state: FSMContext):
    amount = parse_amount(message.text)
    if not amount or amount <= 0:
        await message.answer(
            "⚠️ Nominal tidak valid. Coba lagi, contoh:\n"
            "`50000`, `50.000`, `50k`, `50rb`, atau `1.5jt`",
            parse_mode="Markdown",
        )
        return

    state_data = await state.get_data()
    tx_id = state_data.get("edit_tx_id")
    await state.clear()

    if not tx_id:
        await message.answer("Sesi edit telah berakhir. Silakan pilih transaksi via /edit.", reply_markup=main_menu_kb())
        return

    success = await update_transaction(tx_id, message.chat.id, amount=amount)
    if success:
        await message.answer(f"✅ Nominal berhasil diubah menjadi *{format_rp(amount)}*!", parse_mode="Markdown")
        await show_edit_card(message, tx_id, message.chat.id, is_edit_msg=False)
    else:
        await message.answer("⚠️ Gagal memperbarui transaksi.", reply_markup=main_menu_kb())


@router.callback_query(F.data.startswith("tx_edcat_"))
async def cb_edit_category_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    try:
        tx_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        return

    chat_id = callback.message.chat.id
    tx = await get_transaction_by_id(tx_id, chat_id)
    if not tx:
        await callback.message.edit_text("Transaksi tidak ditemukan.", reply_markup=main_menu_kb())
        return

    categories = await get_categories(chat_id, tx["type"])
    await callback.message.edit_text(
        f"🏷 *Pilih Kategori Baru untuk Transaksi #{tx_id}:*\n"
        f"Kategori saat ini: *{tx['category_name']}*",
        reply_markup=edit_category_kb(categories, tx_id),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("tx_setcat_"))
async def cb_save_edited_category(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    try:
        tx_id = int(parts[2])
        cat_id = int(parts[3])
    except (IndexError, ValueError):
        return

    cat = await get_category_by_id(cat_id)
    if not cat:
        return

    success = await update_transaction(tx_id, callback.message.chat.id, category_id=cat_id)
    if success:
        await show_edit_card(callback.message, tx_id, callback.message.chat.id, is_edit_msg=True)
    else:
        await callback.message.answer("Gagal memperbarui kategori.", reply_markup=main_menu_kb())


@router.callback_query(F.data.startswith("tx_ednote_"))
async def cb_edit_note_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        tx_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        return

    chat_id = callback.message.chat.id
    tx = await get_transaction_by_id(tx_id, chat_id)
    if not tx:
        await callback.message.edit_text("Transaksi tidak ditemukan.", reply_markup=main_menu_kb())
        return

    await state.set_state(EditTransaction.note)
    await state.update_data(edit_tx_id=tx_id)

    curr_note = tx["note"] or "_(Tidak ada catatan)_"
    await callback.message.edit_text(
        f"📝 *Ubah Catatan Transaksi #{tx_id}*\n"
        f"Catatan saat ini: {curr_note}\n\n"
        f"Silakan ketik catatan baru (atau tekan tombol Kosongkan):",
        reply_markup=clear_note_kb(tx_id),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("tx_clearnote_"))
async def cb_clear_note(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Catatan dikosongkan!")
    await state.clear()
    try:
        tx_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        return

    success = await update_transaction(tx_id, callback.message.chat.id, note="")
    if success:
        await show_edit_card(callback.message, tx_id, callback.message.chat.id, is_edit_msg=True)
    else:
        await callback.message.answer("Gagal mengosongkan catatan.", reply_markup=main_menu_kb())


@router.message(StateFilter(EditTransaction.note), F.text)
async def txt_edit_note(message: Message, state: FSMContext):
    state_data = await state.get_data()
    tx_id = state_data.get("edit_tx_id")
    await state.clear()

    if not tx_id:
        await message.answer("Sesi edit telah berakhir. Silakan pilih transaksi via /edit.", reply_markup=main_menu_kb())
        return

    new_note = message.text.strip()
    if new_note == "-":
        new_note = ""

    success = await update_transaction(tx_id, message.chat.id, note=new_note)
    if success:
        await message.answer(f"✅ Catatan transaksi diperbarui!", parse_mode="Markdown")
        await show_edit_card(message, tx_id, message.chat.id, is_edit_msg=False)
    else:
        await message.answer("⚠️ Gagal memperbarui catatan.", reply_markup=main_menu_kb())


# ──────────────────────────────────────
# Quick-Add Shorthand Handler (Chat langsung)
# ──────────────────────────────────────

def find_best_category(note: str, categories: list[dict]) -> Optional[dict]:
    """Cari kategori yang cocok berdasarkan kata kunci di catatan."""
    if not note:
        return None
    note_lower = note.lower()

    # Prioritaskan kecocokan nama kategori persis
    for cat in categories:
        if cat["name"].lower() in note_lower:
            return cat

    # Pemetaan kata kunci umum Indonesia
    keyword_map = {
        "makan": "Makanan",
        "sarapan": "Makanan",
        "lunch": "Makanan",
        "dinner": "Makanan",
        "kopi": "Makanan",
        "cafe": "Makanan",
        "bensin": "Transportasi",
        "grab": "Transportasi",
        "gojek": "Transportasi",
        "ojol": "Transportasi",
        "parkir": "Transportasi",
        "tol": "Transportasi",
        "pulsa": "Tagihan",
        "listrik": "Tagihan",
        "pln": "Tagihan",
        "wifi": "Tagihan",
        "internet": "Tagihan",
        "baju": "Belanja",
        "sepatu": "Belanja",
        "shopee": "Belanja",
        "tokped": "Belanja",
        "obat": "Kesehatan",
        "dokter": "Kesehatan",
        "gaji": "Gaji",
        "salary": "Gaji",
        "proyek": "Freelance",
        "freelance": "Freelance",
        "dividen": "Investasi",
        "saham": "Investasi",
        "crypto": "Investasi",
    }

    for kw, target_name in keyword_map.items():
        if kw in note_lower:
            matched = next((c for c in categories if c["name"].lower() == target_name.lower()), None)
            if matched:
                return matched

    return None


@router.message(StateFilter(None), F.text)
async def handle_quick_add(message: Message):
    if not check_auth(message.chat.id):
        return

    parsed = parse_quick_add(message.text)
    if not parsed:
        # Bukan quick add format, berikan panduan jika mirip
        if message.text.startswith(("+", "-")) or message.text.lower().startswith(("masuk", "keluar")):
            await message.answer(
                "💡 Format Quick-Add kurang tepat. Contoh:\n"
                "`- 25k makan siang`\n"
                "`+ 5jt gaji bulanan`",
                parse_mode="Markdown",
            )
        return

    tx_type = parsed["type"]
    amount = parsed["amount"]
    note = parsed["note"]
    chat_id = message.chat.id

    categories = await get_categories(chat_id, tx_type)
    matched_cat = find_best_category(note, categories)

    if not matched_cat:
        default_name = "Lainnya" if tx_type == "expense" else "Pendapatan Lainnya"
        matched_cat = next((c for c in categories if c["name"] == default_name), categories[0] if categories else None)

    if not matched_cat:
        await message.answer("Belum ada kategori yang tersedia. Silakan gunakan /categories.")
        return

    tx_id = await add_transaction(
        chat_id=chat_id,
        tx_type=tx_type,
        amount=amount,
        category_id=matched_cat["id"],
        note=note,
    )

    type_icon = "💰 Pemasukan" if tx_type == "income" else "💸 Pengeluaran"
    note_str = f" ({note})" if note else ""

    await message.answer(
        f"⚡ *Quick-Add Berhasil!*\n\n"
        f"• ID: `#{tx_id}`\n"
        f"• {type_icon}: *{format_rp(amount)}*\n"
        f"• Kategori: *{matched_cat['name']}*{note_str}",
        reply_markup=post_save_kb(tx_id),
        parse_mode="Markdown",
    )


# ──────────────────────────────────────
# Riwayat Transaksi & Pagination
# ──────────────────────────────────────

PAGE_SIZE = 10

async def render_history(chat_id: int, page: int = 1, period_str: str = "cur") -> tuple[str, int]:
    today = datetime.date.today()
    if period_str and period_str != "cur":
        period_date = parse_period_date(period_str)
        if period_date:
            start = month_start(period_date)
            end = month_end(period_date)
            label = period_date.strftime("%B %Y")
        else:
            start = month_start(today)
            end = month_end(today)
            label = today.strftime("%B %Y")
    else:
        start = month_start(today)
        end = month_end(today)
        label = today.strftime("%B %Y")

    total_count = await count_transactions(chat_id, start, end)
    total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    offset = (page - 1) * PAGE_SIZE

    transactions = await get_transactions(chat_id, start, end, limit=PAGE_SIZE, offset=offset)

    if not transactions:
        text = f"📋 *Riwayat: {label}*\n\nBelum ada transaksi pada periode ini."
        return text, total_pages

    lines = [f"📋 *Riwayat: {label}* (Hal {page}/{total_pages})\n"]
    for tx in transactions:
        icon = "💰" if tx["type"] == "income" else "💸"
        note_str = f" • _{tx['note']}_" if tx["note"] else ""
        date_short = tx["created_at"][5:10]
        lines.append(
            f"`{date_short}` {icon} *{format_rp(tx['amount'])}* [{tx['category_name']}]{note_str}"
        )

    return "\n".join(lines), total_pages


@router.message(Command("history"))
async def cmd_history(message: Message, state: FSMContext):
    if not check_auth(message.chat.id):
        await reject_unauthorized(message)
        return

    await state.clear()
    args = message.text.split()
    period_str = args[1] if len(args) > 1 else "cur"

    text, total_pages = await render_history(message.chat.id, page=1, period_str=period_str)
    await message.answer(
        text,
        reply_markup=history_nav_kb(1, total_pages, period_str),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("hist_p_"))
async def cb_history_pagination(callback: CallbackQuery):
    parts = callback.data.split("_")
    page = int(parts[2])
    period_str = parts[3]

    text, total_pages = await render_history(callback.message.chat.id, page=page, period_str=period_str)
    try:
        await callback.message.edit_text(
            text,
            reply_markup=history_nav_kb(page, total_pages, period_str),
            parse_mode="Markdown",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


# ──────────────────────────────────────
# Laporan Keuangan & Visual Progress Bar
# ──────────────────────────────────────

def format_report_visual(report: dict, label: str) -> str:
    income = report["total_income"]
    expense = report["total_expense"]
    net = report["net"]

    lines = [f"📊 *Laporan Keuangan: {label}*\n"]
    lines.append(f"💰 *Total Pemasukan :* {format_rp(income)}")
    lines.append(f"💸 *Total Pengeluaran:* {format_rp(expense)}")

    sign = "+" if net >= 0 else "-"
    net_icon = "📈" if net >= 0 else "📉"
    lines.append(f"{net_icon} *Saldo Bersih     :* `{sign}{format_rp(abs(net))}`\n")

    if report["expense_breakdown"]:
        lines.append("*Breakdown Pengeluaran:*")
        for item in report["expense_breakdown"]:
            pct = (item["amount"] / expense * 100) if expense > 0 else 0
            bar = generate_progress_bar(pct, length=8)
            lines.append(
                f"• *{item['category']}*: {format_rp(item['amount'])}\n"
                f"  `[{bar}]` {pct:.1f}%"
            )
        lines.append("")

    if report["income_breakdown"]:
        lines.append("*Breakdown Pemasukan:*")
        for item in report["income_breakdown"]:
            pct = (item["amount"] / income * 100) if income > 0 else 0
            lines.append(f"• *{item['category']}*: {format_rp(item['amount'])} ({pct:.1f}%)")

    return "\n".join(lines)


@router.message(Command("report"))
async def cmd_report(message: Message, state: FSMContext):
    if not check_auth(message.chat.id):
        await reject_unauthorized(message)
        return

    await state.clear()
    await message.answer(
        "Pilih periode laporan yang ingin dilihat:",
        reply_markup=report_period_kb(),
    )


@router.callback_query(F.data == "report_month_current")
async def cb_report_month(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    today = datetime.date.today()
    start = month_start(today)
    end = month_end(today)
    report = await get_report(callback.message.chat.id, start, end)
    label = today.strftime("%B %Y")
    text = format_report_visual(report, label)

    await callback.message.edit_text(
        text,
        reply_markup=main_menu_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "report_week_current")
async def cb_report_week(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    today = datetime.date.today()
    start = week_start_iso(today)
    end = week_end_iso(today)
    report = await get_report(callback.message.chat.id, start, end)
    label = format_period_label(start, end)
    text = format_report_visual(report, label)

    await callback.message.edit_text(
        text,
        reply_markup=main_menu_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ──────────────────────────────────────
# Kelola Kategori
# ──────────────────────────────────────

@router.message(Command("categories"))
async def cmd_categories(message: Message, state: FSMContext):
    if not check_auth(message.chat.id):
        await reject_unauthorized(message)
        return

    await state.clear()
    categories = await get_categories(message.chat.id)
    await message.answer(
        "🏷 *Kelola Kategori*\nPilih kategori untuk melihat detail/hapus, atau tambah baru:",
        reply_markup=categories_list_kb(categories),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("cat_view_"))
async def cb_cat_view(callback: CallbackQuery):
    cat_id = int(callback.data.split("_")[2])
    cat = await get_category_by_id(cat_id)
    if not cat:
        await callback.answer("Kategori tidak ditemukan.", show_alert=True)
        return

    type_label = "Pemasukan 💰" if cat["type"] == "income" else "Pengeluaran 💸"
    default_str = "Ya (Kategori Bawaan)" if cat["is_default"] else "Tidak (Kategori Kustom)"

    text = (
        f"🏷 *Detail Kategori*\n\n"
        f"• Nama: *{cat['name']}*\n"
        f"• Tipe: *{type_label}*\n"
        f"• Bawaan: {default_str}\n"
    )
    await callback.message.edit_text(
        text,
        reply_markup=category_detail_kb(cat_id, cat["is_default"]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_del_ask_"))
async def cb_cat_del_ask(callback: CallbackQuery):
    cat_id = int(callback.data.split("_")[3])
    cat = await get_category_by_id(cat_id)
    if not cat:
        await callback.answer("Kategori tidak ditemukan.", show_alert=True)
        return

    await callback.message.edit_text(
        f"⚠️ *Konfirmasi Hapus Kategori*\n\n"
        f"Apakah Anda yakin ingin menghapus kategori *{cat['name']}*?",
        reply_markup=delete_cat_confirm_kb(cat_id),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_del_do_"))
async def cb_cat_del_do(callback: CallbackQuery):
    cat_id = int(callback.data.split("_")[3])
    success, msg = await delete_category(cat_id)

    if success:
        await callback.answer("Kategori berhasil dihapus!", show_alert=True)
        categories = await get_categories(callback.message.chat.id)
        await callback.message.edit_text(
            "🏷 *Kelola Kategori*\nKategori telah dihapus.",
            reply_markup=categories_list_kb(categories),
            parse_mode="Markdown",
        )
    else:
        await callback.answer(msg, show_alert=True)


@router.callback_query(F.data == "cat_add_new")
async def cb_cat_add_new(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCategoryWizard.name)
    await callback.message.edit_text(
        "Ketik *nama kategori baru* yang ingin Anda buat:\n"
        "_(Contoh: `Investasi Emas`, `Asuransi`, `Game`)_",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(StateFilter(AddCategoryWizard.name), F.text)
async def txt_cat_wizard_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Nama tidak boleh kosong. Coba lagi:")
        return

    await state.update_data(cat_name=name)
    await state.set_state(AddCategoryWizard.type)

    await message.answer(
        f"Kategori: *{name}*\nPilih tipe kategori:",
        reply_markup=type_selection_kb(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.in_(["tx_income", "tx_expense"]), StateFilter(AddCategoryWizard.type))
async def cb_cat_wizard_type(callback: CallbackQuery, state: FSMContext):
    cat_type = "income" if callback.data == "tx_income" else "expense"
    data = await state.get_data()
    cat_name = data["cat_name"]

    cat_id = await add_category(cat_name, cat_type)
    await state.clear()

    if cat_id:
        type_str = "Pemasukan 💰" if cat_type == "income" else "Pengeluaran 💸"
        await callback.message.edit_text(
            f"✅ Kategori *{cat_name}* ({type_str}) berhasil ditambahkan!",
            reply_markup=main_menu_kb(),
            parse_mode="Markdown",
        )
    else:
        await callback.message.edit_text(
            f"⚠️ Kategori *{cat_name}* sudah pernah dibuat sebelumnya.",
            reply_markup=main_menu_kb(),
            parse_mode="Markdown",
        )
    await callback.answer()


# ──────────────────────────────────────
# Export CSV
# ──────────────────────────────────────

async def do_export(chat_id: int, period_str: str = "cur") -> tuple[Optional[BufferedInputFile], str]:
    today = datetime.date.today()
    if period_str and period_str != "cur":
        period_date = parse_period_date(period_str)
        if period_date:
            start = month_start(period_date)
            end = month_end(period_date)
            label = period_date.strftime("%B %Y")
        else:
            return None, "Format tanggal tidak valid. Gunakan format YYYY-MM, contoh: `/export 2026-09`."
    else:
        start = month_start(today)
        end = month_end(today)
        label = today.strftime("%B %Y")

    transactions = await get_transactions(chat_id, start, end, limit=5000, offset=0)
    if not transactions:
        return None, f"Tidak ada data transaksi untuk diexport pada periode *{label}*."

    filename, csv_content = generate_csv(transactions, label)
    file_bytes = csv_content.encode("utf-8-sig")  # utf-8-sig agar rapi di Microsoft Excel Windows
    doc = BufferedInputFile(file_bytes, filename=filename)
    return doc, f"📤 *Export CSV Selesai!*\nPeriode: *{label}*\nTotal: *{len(transactions)} transaksi*"


@router.message(Command("export"))
async def cmd_export(message: Message, state: FSMContext):
    if not check_auth(message.chat.id):
        await reject_unauthorized(message)
        return

    await state.clear()
    args = message.text.split()
    period_str = args[1] if len(args) > 1 else "cur"

    doc, caption = await do_export(message.chat.id, period_str)
    if not doc:
        await message.answer(caption, reply_markup=main_menu_kb(), parse_mode="Markdown")
        return

    await message.answer_document(
        document=doc,
        caption=caption,
        parse_mode="Markdown",
    )


# ──────────────────────────────────────
# Menu Callbacks
# ──────────────────────────────────────

@router.callback_query(F.data == "menu_main")
async def cb_menu_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_main_menu(callback)


@router.callback_query(F.data == "menu_add")
async def cb_menu_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddTransaction.type)
    await callback.message.edit_text(
        "Pilih tipe transaksi:",
        reply_markup=type_selection_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu_history")
async def cb_menu_history(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text, total_pages = await render_history(callback.message.chat.id, page=1, period_str="cur")
    await callback.message.edit_text(
        text,
        reply_markup=history_nav_kb(1, total_pages, "cur"),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "menu_report")
async def cb_menu_report(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Pilih periode laporan yang ingin dilihat:",
        reply_markup=report_period_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu_categories")
async def cb_menu_categories(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    categories = await get_categories(callback.message.chat.id)
    await callback.message.edit_text(
        "🏷 *Kelola Kategori*\nPilih kategori untuk melihat detail/hapus, atau tambah baru:",
        reply_markup=categories_list_kb(categories),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "menu_export")
async def cb_menu_export(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    doc, caption = await do_export(callback.message.chat.id, "cur")
    if not doc:
        await callback.message.edit_text(caption, reply_markup=main_menu_kb(), parse_mode="Markdown")
        await callback.answer()
        return

    await callback.message.answer_document(
        document=doc,
        caption=caption,
        parse_mode="Markdown",
    )
    await callback.message.answer("Kembali ke menu:", reply_markup=main_menu_kb())
    await callback.answer()


# ──────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────

async def main():
    logger.info("Menginisialisasi database...")
    await init_db()
    logger.info("Finance Tracker Bot berhasil aktif dan siap menerima pesan.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
