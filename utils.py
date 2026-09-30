"""
Utility functions: formatting, CSV export, date helpers, and input parsing.
"""

import csv
import io
import re
import datetime
from typing import Optional


# ──────────────────────────────────────
# Formatting
# ──────────────────────────────────────

def format_rp(amount: float) -> str:
    """Format angka ke format Rupiah standar Indonesia: Rp 1.200.000"""
    formatted = f"{amount:,.0f}".replace(",", ".")
    return f"Rp {formatted}"


def generate_progress_bar(percentage: float, length: int = 10) -> str:
    """Generate ASCII/emoji progress bar: [██████░░░░]"""
    filled = int(round((max(0.0, min(100.0, percentage)) / 100) * length))
    return "█" * filled + "░" * (length - filled)


# ──────────────────────────────────────
# Smart Parsers (Indonesian Currency & Shorthand)
# ──────────────────────────────────────

def parse_amount(text: str) -> Optional[float]:
    """
    Parse nominal uang bahasa Indonesia ke float.
    Mendukung format:
    - '50000', '50.000', '50,000'
    - '50k', '50rb' (ribu -> x1.000)
    - '1.5jt', '1,5jt' (juta -> x1.000.000)
    - '2m' (juta / million -> x1.000.000)
    - Prefix 'Rp', 'idr'
    Return None jika format tidak valid atau <= 0.
    """
    if not text:
        return None

    t = text.strip().lower()
    t = re.sub(r"^(rp|idr)\.?\s*", "", t)

    mult = 1.0
    if t.endswith(("rb", "k")):
        mult = 1_000.0
        t = re.sub(r"(rb|k)$", "", t).strip()
    elif t.endswith("jt"):
        mult = 1_000_000.0
        t = re.sub(r"jt$", "", t).strip()
    elif t.endswith("m") and not t.endswith("rb"):
        mult = 1_000_000.0
        t = re.sub(r"m$", "", t).strip()

    if not t:
        return None

    try:
        # Menangani separator titik dan koma
        if "." in t and "," in t:
            if t.find(".") < t.find(","):
                # Format Indo standar: 1.500,50
                t = t.replace(".", "").replace(",", ".")
            else:
                # Format US: 1,500.50
                t = t.replace(",", "")
        elif "." in t:
            parts = t.split(".")
            # Jika ada lebih dari satu titik atau 3 digit setelah titik tanpa pengali, anggap titik ribuan
            if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and mult == 1.0):
                t = t.replace(".", "")
        elif "," in t:
            parts = t.split(",")
            if len(parts) == 2 and len(parts[1]) == 3 and mult == 1.0:
                t = t.replace(",", "")
            else:
                t = t.replace(",", ".")

        val = float(t) * mult
        return val if val > 0 else None
    except (ValueError, TypeError):
        return None


def parse_quick_add(text: str) -> Optional[dict]:
    """
    Parse input cepat transaksi satu baris.
    Contoh:
    - '- 25k makan siang' -> {'type': 'expense', 'amount': 25000.0, 'note': 'makan siang'}
    - '+ 5jt bonus project' -> {'type': 'income', 'amount': 5000000.0, 'note': 'bonus project'}
    - 'keluar 50rb bensin' -> {'type': 'expense', 'amount': 50000.0, 'note': 'bensin'}
    - 'masuk 200k freelance' -> {'type': 'income', 'amount': 200000.0, 'note': 'freelance'}
    """
    t = text.strip()
    match = re.match(
        r"^([\+\-]|masuk\s+|keluar\s+)\s*([0-9.,]+[a-zA-Z]*)\s*(.*)$",
        t,
        re.IGNORECASE,
    )
    if not match:
        return None

    prefix, amt_str, note = match.groups()
    prefix = prefix.strip().lower()
    tx_type = "income" if prefix in ("+", "masuk") else "expense"

    amount = parse_amount(amt_str)
    if not amount:
        return None

    return {
        "type": tx_type,
        "amount": amount,
        "note": note.strip(),
    }


# ──────────────────────────────────────
# Date helpers
# ──────────────────────────────────────

def month_start(month: Optional[datetime.date] = None) -> str:
    """Return first day of month as 'YYYY-MM-DD 00:00:00'."""
    if month is None:
        month = datetime.date.today()
    return datetime.datetime(month.year, month.month, 1).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def month_end(month: Optional[datetime.date] = None) -> str:
    """Return last day of month as 'YYYY-MM-DD 23:59:59'."""
    if month is None:
        month = datetime.date.today()
    next_month = month.replace(day=28) + datetime.timedelta(days=4)
    last_day = next_month - datetime.timedelta(days=next_month.day)
    return datetime.datetime(last_day.year, last_day.month, last_day.day, 23, 59, 59).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def week_start_iso(date: Optional[datetime.date] = None) -> str:
    """Return start of ISO week (Monday) as 'YYYY-MM-DD 00:00:00'."""
    if date is None:
        date = datetime.date.today()
    days_since_monday = date.weekday()
    monday = date - datetime.timedelta(days=days_since_monday)
    return datetime.datetime(monday.year, monday.month, monday.day).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def week_end_iso(date: Optional[datetime.date] = None) -> str:
    """Return end of ISO week (Sunday) as 'YYYY-MM-DD 23:59:59'."""
    if date is None:
        date = datetime.date.today()
    days_since_monday = date.weekday()
    monday = date - datetime.timedelta(days=days_since_monday)
    sunday = monday + datetime.timedelta(days=6)
    return datetime.datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def parse_period_date(text: str) -> Optional[datetime.date]:
    """Parse 'YYYY-MM' atau 'YYYY-MM-DD' ke datetime.date."""
    for fmt in ("%Y-%m", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def format_period_label(start: str, end: str) -> str:
    """Buat label deskriptif dari range tanggal."""
    start_d = datetime.datetime.strptime(start[:10], "%Y-%m-%d").date()
    end_d = datetime.datetime.strptime(end[:10], "%Y-%m-%d").date()

    if start_d.month == end_d.month and start_d.year == end_d.year:
        if (end_d - start_d).days <= 7 and start_d != end_d:
            return f"{start_d.day} - {end_d.day} {start_d.strftime('%B %Y')}"
        return start_d.strftime("%B %Y")

    if start_d == end_d:
        return start_d.strftime("%d %B %Y")

    # Mingguan lintas bulan
    if (end_d - start_d).days <= 7:
        if start_d.year == end_d.year:
            return f"{start_d.day} {start_d.strftime('%b')} - {end_d.day} {end_d.strftime('%b %Y')}"
        return f"{start_d.strftime('%d %b %Y')} - {end_d.strftime('%d %b %Y')}"

    return f"{start_d.strftime('%d %B %Y')} - {end_d.strftime('%d %B %Y')}"


# ──────────────────────────────────────
# CSV Export
# ──────────────────────────────────────

def generate_csv(
    transactions: list[dict],
    period_label: str = "Laporan Keuangan",
) -> tuple[str, str]:
    """
    Generate CSV dari list transaksi.
    Return (filename, csv_content_string).
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Tanggal",
        "Tipe",
        "Kategori",
        "Jumlah (Rp)",
        "Catatan",
    ])

    # Data rows
    for tx in transactions:
        writer.writerow([
            tx["created_at"],
            "Pemasukan" if tx["type"] == "income" else "Pengeluaran",
            tx["category_name"],
            f"{tx['amount']:,.0f}".replace(",", "."),
            tx["note"] or "",
        ])

    safe_label = re.sub(r"[^\w\-_]", "_", period_label)
    filename = f"finance_report_{safe_label}.csv"
    return filename, output.getvalue()
