#!/usr/bin/env python3

from pathlib import Path
from io import BytesIO
from math import floor

from PIL import Image
import segno

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder


# ============================================================
# GLOBAL SETTINGS FILLED BY USER INPUT
# ============================================================

CODE_TYPES = []
PREFIX = ""
SUFFIX = ""

START_NUMBER = 1
COUNT = 1
DIGITS = 4

RIGHT_TEXT_LINES = []
SHOW_CODE_TYPE = False
DRAW_LABEL_BORDER = True

# Micro QR redundancy:
# None = automatic/default
# "L" = low
# "M" = medium
# "Q" = high / max for Micro QR
ERROR_CORRECTION = None

OUTPUT_BASENAME = "inventory_labels"

# Paper size
PAGE_SIZE = letter
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE

# Each label is 1 inch tall by 2 inches wide
LABEL_WIDTH = 2.0 * inch
LABEL_HEIGHT = 1.0 * inch

# Page margins
MARGIN_X = 0.25 * inch
MARGIN_Y = 0.25 * inch

# No gap = maximum density
GAP_X = 0.00 * inch
GAP_Y = 0.00 * inch

# Layout inside each label
INNER_PAD = 0.06 * inch
CODE_SIZE = 0.72 * inch
TEXT_GAP = 0.08 * inch


# ============================================================
# UID GENERATION
# ============================================================

def make_uid(prefix: str, number: int, digits: int, suffix: str = "") -> str:
    parts = []

    prefix = prefix.strip()
    suffix = suffix.strip()

    if prefix:
        parts.append(prefix)

    parts.append(f"{number:0{digits}d}")

    if suffix:
        parts.append(suffix)

    return "-".join(parts)


# ============================================================
# CODE IMAGE GENERATION
# ============================================================

def make_datamatrix_pil(data: str) -> Image.Image:
    """Generate ECC200 Data Matrix using a pure-Python backend."""
    payload = DataMatrixData(data, auto_encoding=True)
    encoder = DataMatrixEncoder(payload, quiet_zone=2, symbol_shape="square")
    image_bytes = encoder.get_imagedata(cellsize=8)
    with Image.open(BytesIO(image_bytes)) as img:
        return img.convert("RGB")


def make_microqr_pil(data: str) -> Image.Image:
    if ERROR_CORRECTION is None:
        qr = segno.make_micro(data)
    else:
        qr = segno.make_micro(data, error=ERROR_CORRECTION)

    buf = BytesIO()
    qr.save(buf, kind="png", scale=8, border=1, dark="black", light="white")
    buf.seek(0)

    img = Image.open(buf).convert("RGB")
    return img


def make_code_image(data: str, code_type: str) -> ImageReader:
    if code_type == "datamatrix":
        pil_img = make_datamatrix_pil(data)
    elif code_type == "microqr":
        pil_img = make_microqr_pil(data)
    else:
        raise ValueError(f"Unsupported code type: {code_type}")

    return ImageReader(pil_img)


# ============================================================
# LABEL DRAWING
# ============================================================

def right_side_lines(uid: str, code_type: str) -> list[str]:
    lines = [uid]
    lines.extend(RIGHT_TEXT_LINES)

    if SHOW_CODE_TYPE:
        if code_type == "microqr":
            ecc_text = ERROR_CORRECTION if ERROR_CORRECTION is not None else "DEFAULT"
            lines.append(f"MICRO QR ECC {ecc_text}")
        elif code_type == "datamatrix":
            lines.append("DATAMATRIX ECC200")

    return lines


def draw_label(c: canvas.Canvas, x: float, y: float, uid: str, code_type: str):
    if DRAW_LABEL_BORDER:
        c.setLineWidth(0.25)
        c.rect(x, y, LABEL_WIDTH, LABEL_HEIGHT)

    code_x = x + INNER_PAD
    code_y = y + (LABEL_HEIGHT - CODE_SIZE) / 2

    code_img = make_code_image(uid, code_type)
    c.drawImage(code_img, code_x, code_y, width=CODE_SIZE, height=CODE_SIZE)

    text_x = code_x + CODE_SIZE + TEXT_GAP
    text_top = y + LABEL_HEIGHT - INNER_PAD - 0.02 * inch

    lines = right_side_lines(uid, code_type)

    if not lines:
        return

    c.setFont("Helvetica-Bold", 8)
    c.drawString(text_x, text_top - 0.12 * inch, lines[0])

    c.setFont("Helvetica", 6)
    line_y = text_top - 0.28 * inch
    line_step = 0.14 * inch

    for line in lines[1:]:
        c.drawString(text_x, line_y, line)
        line_y -= line_step


# ============================================================
# PDF LAYOUT
# ============================================================

def labels_per_row() -> int:
    usable_width = PAGE_WIDTH - 2 * MARGIN_X
    return floor((usable_width + GAP_X) / (LABEL_WIDTH + GAP_X))


def labels_per_col() -> int:
    usable_height = PAGE_HEIGHT - 2 * MARGIN_Y
    return floor((usable_height + GAP_Y) / (LABEL_HEIGHT + GAP_Y))


def label_origin(row: int, col: int) -> tuple[float, float]:
    x = MARGIN_X + col * (LABEL_WIDTH + GAP_X)
    y = PAGE_HEIGHT - MARGIN_Y - LABEL_HEIGHT - row * (LABEL_HEIGHT + GAP_Y)
    return x, y


# ============================================================
# PDF GENERATION
# ============================================================

def output_filename(code_type: str) -> str:
    safe_prefix = PREFIX.strip() or "NO-PREFIX"
    safe_suffix = f"-{SUFFIX.strip()}" if SUFFIX.strip() else ""

    first_num = START_NUMBER
    last_num = START_NUMBER + COUNT - 1

    if code_type == "microqr":
        ecc = ERROR_CORRECTION if ERROR_CORRECTION is not None else "DEFAULT"
        return f"{safe_prefix}{safe_suffix}_{first_num}_to_{last_num}_microqr_ECC-{ecc}.pdf"

    if code_type == "datamatrix":
        return f"{safe_prefix}{safe_suffix}_{first_num}_to_{last_num}_datamatrix_ECC200.pdf"

    return f"{safe_prefix}{safe_suffix}_{first_num}_to_{last_num}_{code_type}.pdf"


def generate_pdf(code_type: str):
    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / output_filename(code_type)
    c = canvas.Canvas(str(out_path), pagesize=PAGE_SIZE)

    cols = labels_per_row()
    rows = labels_per_col()
    per_page = cols * rows

    if cols <= 0 or rows <= 0:
        raise RuntimeError("Label/page configuration does not fit even one label.")

    for idx in range(COUNT):
        n = START_NUMBER + idx
        uid = make_uid(PREFIX, n, DIGITS, SUFFIX)

        pos = idx % per_page

        if idx > 0 and pos == 0:
            c.showPage()

        row = pos // cols
        col = pos % cols

        x, y = label_origin(row, col)
        draw_label(c, x, y, uid, code_type)

    c.save()

    first_uid = make_uid(PREFIX, START_NUMBER, DIGITS, SUFFIX)
    last_uid = make_uid(PREFIX, START_NUMBER + COUNT - 1, DIGITS, SUFFIX)

    print(f"Generated: {out_path.resolve()}")
    print(f"  code type:   {code_type}")
    print(f"  labels/page: {per_page} ({cols} cols x {rows} rows)")
    print(f"  first UID:   {first_uid}")
    print(f"  last UID:    {last_uid}")
    print()


# ============================================================
# USER INPUT
# ============================================================

def ask_string(prompt: str, allow_blank: bool = False) -> str:
    while True:
        value = input(f"{prompt}: ").strip()

        if value or allow_blank:
            return value

        print("This field is required.")


def ask_int(prompt: str, minimum: int | None = None, maximum: int | None = None) -> int:
    while True:
        value = input(f"{prompt}: ").strip()

        try:
            number = int(value)
        except ValueError:
            print("Enter a whole number.")
            continue

        if minimum is not None and number < minimum:
            print(f"Enter a number >= {minimum}.")
            continue

        if maximum is not None and number > maximum:
            print(f"Enter a number <= {maximum}.")
            continue

        return number


def ask_yes_no(prompt: str) -> bool:
    while True:
        value = input(f"{prompt} [y/n]: ").strip().lower()

        if value in ("y", "yes"):
            return True

        if value in ("n", "no"):
            return False

        print("Choose y or n.")


def ask_code_types() -> list[str]:
    while True:
        print()
        print("Code type:")
        print("  1 = Micro QR only")
        print("  2 = Data Matrix only")
        print("  3 = Both")
        choice = input("Choose code type: ").strip()

        if choice == "1":
            return ["microqr"]

        if choice == "2":
            return ["datamatrix"]

        if choice == "3":
            return ["microqr", "datamatrix"]

        print("Choose 1, 2, or 3.")


def ask_redundancy_level(code_types: list[str]) -> int:
    print()
    print("Redundancy / error correction level:")
    print()

    if "microqr" in code_types:
        print("Micro QR:")
        print("  0 = automatic/default")
        print("  1 = L / low redundancy")
        print("  2 = M / medium redundancy")
        print("  3 = Q / high redundancy / max for Micro QR")
        print()

    if "datamatrix" in code_types:
        print("Data Matrix:")
        print("  0 = ECC200 fixed")
        print("  Data Matrix ECC200 does not have selectable levels.")
        print()

    if code_types == ["datamatrix"]:
        return ask_int("Data Matrix redundancy level, only 0 is valid", minimum=0, maximum=0)

    return ask_int("Micro QR redundancy level", minimum=0, maximum=3)


def microqr_error_from_redundancy(level: int):
    if level == 0:
        return None
    if level == 1:
        return "L"
    if level == 2:
        return "M"
    if level == 3:
        return "Q"

    raise ValueError(f"Unsupported Micro QR redundancy level: {level}")


def apply_user_inputs():
    global PREFIX, SUFFIX, START_NUMBER, COUNT, DIGITS, CODE_TYPES
    global RIGHT_TEXT_LINES, SHOW_CODE_TYPE, DRAW_LABEL_BORDER
    global ERROR_CORRECTION

    print("Inventory label PDF generator")
    print("-" * 40)
    print("No defaults. Fill in each prompt.")
    print("For prefix/suffix/right-side text, blank is allowed where stated.")
    print()

    PREFIX = ask_string("Prefix, blank for none", allow_blank=True)
    SUFFIX = ask_string("Suffix, blank for none", allow_blank=True)

    START_NUMBER = ask_int("Start number", minimum=0)
    COUNT = ask_int("How many labels", minimum=1)
    DIGITS = ask_int("Number padding digits", minimum=1)

    CODE_TYPES = ask_code_types()

    redundancy_level = ask_redundancy_level(CODE_TYPES)
    ERROR_CORRECTION = microqr_error_from_redundancy(redundancy_level)

    print()
    print("Right-side text:")
    print("Enter text lines separated by |")
    print("Example: INVENTORY ID|SCAN FOR RECORD")
    RIGHT_TEXT_LINES = [
        line.strip()
        for line in ask_string("Text lines, blank for none", allow_blank=True).split("|")
        if line.strip()
    ]

    SHOW_CODE_TYPE = ask_yes_no("Show code type text on label")
    DRAW_LABEL_BORDER = ask_yes_no("Draw label borders")

    first_uid = make_uid(PREFIX, START_NUMBER, DIGITS, SUFFIX)
    last_uid = make_uid(PREFIX, START_NUMBER + COUNT - 1, DIGITS, SUFFIX)

    print()
    print("Preview:")
    print(f"  First UID:        {first_uid}")
    print(f"  Last UID:         {last_uid}")
    print(f"  Count:            {COUNT}")
    print(f"  Code(s):          {', '.join(CODE_TYPES)}")

    if "microqr" in CODE_TYPES:
        shown_ecc = ERROR_CORRECTION if ERROR_CORRECTION is not None else "default"
        print(f"  Micro QR ECC:     {shown_ecc}")

    if "datamatrix" in CODE_TYPES:
        print("  Data Matrix ECC:  ECC200 fixed")

    print(f"  Text:             {RIGHT_TEXT_LINES}")
    print(f"  Label borders:    {DRAW_LABEL_BORDER}")
    print()

    if not ask_yes_no("Generate PDF now"):
        print("Cancelled.")
        raise SystemExit


def main():
    apply_user_inputs()

    print()
    print("Generating PDFs")
    print("-" * 40)

    had_error = False
    for code_type in CODE_TYPES:
        try:
            generate_pdf(code_type)
        except Exception as e:
            had_error = True
            print(f"Failed to generate {code_type}: {e}")
            print()
    if had_error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()