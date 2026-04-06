from datetime import date, datetime
from typing import Optional
import openpyxl


def load_payments(filepath: str) -> list[dict]:
    """
    Read an xlsx file and return a list of payment dicts.

    The workbook is expected to have 3 header rows (skipped) followed by
    data rows with columns:
        creditor | payment_num | amount | due_date | balance_before | balance_after

    The balance_after column typically contains a formula and is read as None;
    it is computed as balance_before - amount.

    Blank rows (no creditor value) are ignored.
    """
    try:
        wb = openpyxl.load_workbook(filepath, data_only=True)
    except FileNotFoundError:
        raise FileNotFoundError(f"No such file: {filepath}")

    ws = wb.active
    payments = []

    for row in ws.iter_rows(min_row=4, values_only=True):
        creditor, payment_num, amount, due_date, balance_before, balance_after = row[:6]

        # Skip blank separator rows
        if creditor is None:
            continue

        # due_date may come back as a datetime from openpyxl
        if isinstance(due_date, datetime):
            due_date = due_date.date()

        # balance_after is often a formula cell (reads as None); compute it
        if balance_after is None:
            balance_after = (balance_before or 0.0) - (amount or 0.0)

        payments.append(
            {
                "creditor": creditor,
                "payment_num": payment_num,
                "amount": float(amount) if amount is not None else None,
                "due_date": due_date,
                "balance_before": float(balance_before) if balance_before is not None else None,
                "balance_after": float(balance_after),
            }
        )

    return payments


def get_upcoming_payments(payments: list[dict], days: int = 14) -> list[dict]:
    """
    Return payments whose due_date falls within [today, today + days] inclusive.
    """
    today = date.today()
    cutoff = today.replace(year=today.year) + __import__("datetime").timedelta(days=days)
    return [p for p in payments if today <= p["due_date"] <= cutoff]


def get_monthly_summary(payments: list[dict]) -> list[dict]:
    """
    Group future payments (due_date >= today) by calendar month.

    Returns a list of dicts sorted chronologically, each with:
      month  — label like "April 2026"
      total  — sum of all amounts due that month
    """
    today = date.today()
    buckets: dict[tuple, float] = {}
    for p in payments:
        if p["due_date"] < today:
            continue
        key = (p["due_date"].year, p["due_date"].month)
        buckets[key] = round(buckets.get(key, 0.0) + p["amount"], 2)

    return [
        {"month": date(year, month, 1).strftime("%B %Y"), "total": total}
        for (year, month), total in sorted(buckets.items())
    ]


def is_paid_off(payments: list[dict], creditor: str) -> bool:
    """
    Return True if the last payment for the given creditor has balance_after == 0.

    Raises ValueError if the creditor is not found in the payment list.
    """
    creditor_payments = [p for p in payments if p["creditor"] == creditor]
    if not creditor_payments:
        raise ValueError(f"Creditor not found: {creditor!r}")
    return creditor_payments[-1]["balance_after"] == 0.0
