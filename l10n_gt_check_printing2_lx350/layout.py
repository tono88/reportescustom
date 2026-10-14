"""Geometry and monetary helpers; no printer or database side effects."""

from decimal import Decimal, ROUND_HALF_UP
import math

MODULE = "l10n_gt_check_printing2_lx350"
PERSONAL = MODULE + ".action_check_personal"
COMMERCIAL = MODULE + ".action_check_commercial"
LAYOUTS = {PERSONAL: 165.10, COMMERCIAL: 190.50}
HEIGHT = 69.85
MICR_HEIGHT = 16.0


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
