import calendar
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

MONTH_NAMES = [
    "",
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    month += delta
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return year, month


def build_calendar(
    year: int,
    month: int,
    *,
    prefix: str = "cal",
    min_date: date | None = None,
    max_date: date | None = None,
    blocked_dates: set[date] | None = None,
    selected: date | None = None,
) -> InlineKeyboardMarkup:
    blocked_dates = blocked_dates or set()
    min_date = min_date or date.today()
    builder = InlineKeyboardBuilder()

    prev_y, prev_m = _shift_month(year, month, -1)
    next_y, next_m = _shift_month(year, month, 1)
    builder.row(
        InlineKeyboardButton(text="◀", callback_data=f"{prefix}:nav:{prev_y}-{prev_m:02d}"),
        InlineKeyboardButton(text=f"{MONTH_NAMES[month]} {year}", callback_data=f"{prefix}:noop"),
        InlineKeyboardButton(text="▶", callback_data=f"{prefix}:nav:{next_y}-{next_m:02d}"),
    )
    builder.row(*[InlineKeyboardButton(text=wd, callback_data=f"{prefix}:noop") for wd in WEEKDAYS])

    cal = calendar.Calendar(firstweekday=0)
    for week in cal.monthdayscalendar(year, month):
        row: list[InlineKeyboardButton] = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data=f"{prefix}:noop"))
                continue
            current = date(year, month, day)
            if current < min_date or (max_date and current > max_date) or current in blocked_dates:
                row.append(InlineKeyboardButton(text="·", callback_data=f"{prefix}:noop"))
                continue
            label = f"[{day}]" if selected and selected == current else str(day)
            row.append(
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"{prefix}:pick:{current.isoformat()}",
                )
            )
        builder.row(*row)

    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"{prefix}:cancel"))
    return builder.as_markup()
