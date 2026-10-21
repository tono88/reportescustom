"""Build embedded numeral images offline; never runs inside Odoo.

Requires Pillow in the build environment, not on the Odoo server.
Usage: python build_amount_glyphs.py --font /path/to/arialbd.ttf
"""

import argparse
import base64
from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont


def build(font_path):
    font = ImageFont.truetype(str(font_path), 128)
    chars = '0123456789,.'
    top = min(font.getbbox(char)[1] for char in chars)
    glyphs = {}
    for char in chars:
        advance = 556 if char.isdigit() else 278
        # Use the same em advances as the QWeb layout. Full-height cells keep
        # punctuation at the common baseline without stretching individual ink.
        width = round(128 * advance / 1000)
        image = Image.new('L', (width, 128), 255)
        draw = ImageDraw.Draw(image)
        draw.text((0, 10-top), char, font=font, fill=0)
        assert image.getextrema()[0] == 0
        output = BytesIO()
        image.save(output, format='PNG', optimize=True)
        glyphs[char] = base64.b64encode(output.getvalue()).decode('ascii')
    return glyphs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--font', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).parents[2] / 'l10n_gt_check_printing2_pdf_live'
    path = root / 'reports/check_reports.xml'
    glyphs = build(args.font)
    content = path.read_text(encoding='utf-8')
    declaration = '<t t-set="amount_glyphs" t-value="' + repr(glyphs) + '"/>'
    replacement = '<!-- amount-glyphs-begin -->\n                                ' + declaration + '\n                                <!-- amount-glyphs-end -->'
    content, count = re.subn(r'<!-- amount-glyphs-begin -->.*?<!-- amount-glyphs-end -->', replacement, content, flags=re.S)
    assert count == 1
    path.write_text(content, encoding='utf-8')
    print(f'Embedded {len(glyphs)} numeral/punctuation PNGs; no server dependencies added.')


if __name__ == '__main__':
    main()
