"""Geometry and monetary helpers; no printer or database side effects."""

from decimal import Decimal, ROUND_HALF_UP
import math

MODULE = "l10n_gt_check_printing2_lx350"
PERSONAL = MODULE + ".action_check_personal"
GYT = MODULE + ".action_check_gyt"
LAYOUTS = {PERSONAL: 165.10, GYT: 165.10}
BANKS = {PERSONAL: "banrural", GYT: "gyt"}
BANK_LABELS = {PERSONAL: "Banrural", GYT: "G&T Continental"}
# Starting positions estimated from the supplied photographs. Each journal
# retains its own calibration; loading a profile is an explicit user action.
INITIAL_POSITIONS = {
    PERSONAL: {"date": (18, 24, 110), "amount": (139, 24, 23), "payee": (18, 31, 144), "words": (18, 38, 144)},
    GYT: {"date": (24, 25, 100), "amount": (139, 25, 23), "payee": (24, 33, 138), "words": (24, 41, 138)},
}
HEIGHT = 69.85
# Odoo 18 report.paperformat uses Integer page dimensions. Keep the nominal
# cheque geometry separate from the native PDF canvas.
PAPER_WIDTH = 165
PAPER_HEIGHT = 70
MICR_HEIGHT = 16.0


def require_bank(layout, bank):
    if BANKS.get(layout) != bank:
        raise ValueError("El botón no corresponde al banco configurado en el diario del pago.")


def amount_parts(amount):
    value = Decimal(str(amount))
    if not value.is_finite() or value < 0:
        raise ValueError("El importe debe ser un número positivo o cero.")
    total_cents = int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return divmod(total_cents, 100)


def fit_font(text, width, preferred):
    # Conservative estimate for uppercase text. Never silently truncate a payee
    # or amount; refuse content that would need less than 7 pt.
    size = min(preferred, width / max(len(text), 1) / 0.27)
    if size < 7:
        raise ValueError("El texto es demasiado largo. Amplía su campo o revisa el beneficiario.")
    return round(size, 2)


def validate_geometry(width, positions, font_size):
    if not math.isfinite(font_size) or not 7 <= font_size <= 12:
        raise ValueError("El tamaño de letra debe estar entre 7 y 12 puntos.")
    for label, box in positions.items():
        x, y, field_width = box
        if not all(math.isfinite(v) for v in box):
            raise ValueError("Las posiciones deben ser números finitos.")
        if field_width <= 0 or x < 3 or x + field_width > width - 3:
            raise ValueError(f"{label}: el campo queda fuera de los márgenes laterales de 3 mm.")
        if y < 4.2 or y + font_size * 25.4 / 72 > HEIGHT - MICR_HEIGHT:
            raise ValueError(f"{label}: el campo invade el borde superior o la banda magnética inferior.")
