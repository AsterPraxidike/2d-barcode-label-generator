# Inventory Label Generator

Interactive Python tool for printing **2 × 1 inch** inventory labels on US Letter paper (3 columns × 10 rows, 30 per page). Generates Micro QR and/or Data Matrix (ECC200) codes, sequential IDs, custom text, and printable PDFs.

## Quick start (EndeavourOS / Arch Linux)

Install Python once, if needed:

```bash
sudo pacman -S --needed python
```

Clone the repository, enter it, and launch:

```bash
git clone YOUR_GITHUB_REPO_URL
cd inventory-label-generator
./run.sh
```

Or download the project, extract it, and run `./run.sh` from the extracted directory.

**First run:** `run.sh` creates `.venv/` and installs the packages listed in `requirements.txt` using pip. The first run requires internet. Later runs reuse the environment without reinstalling packages. No system-wide pip changes are needed.

**Manual setup** (Linux, macOS, Windows with adjusted activation command):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python label_generator.py
```

PDFs are saved in `output/` (ignored by Git).

## Options

- Prefix and suffix (optional); start number, count, numeric zero-padding
- Micro QR, Data Matrix, or both, with separate PDF outputs
- Micro QR error correction: automatic, L, M, Q. Not every payload fits in Micro QR at every level; reduce the payload or use Data Matrix if a Micro QR is too small.
- Data Matrix uses **ECC200**, with fixed error correction (not user-selectable)
- Extra label text, `|` separates lines
- Optional code-type details and label outlines
- Final confirmation before PDFs are generated

## Dependencies

- `segno` for Micro QR
- `pyStrich` for ECC200 Data Matrix (pure Python, **no `libdmtx`/`pylibdmtx`/`distutils`**)
- `Pillow` for image handling
- `reportlab` for PDF output

The source, pinned dependency list and bootstrap launcher are GitHub-ready. They do **not** embed Python or the third-party libraries; installation uses pip automatically on first run. This is a reproducible repo distribution, not a standalone binary or offline installer.

## Troubleshooting

If dependencies fail to install, confirm network access and that your Python version is supported by the dependency versions (Python 3.10+ recommended). On some Linux installations, `python3 -m venv` needs additional distribution support.

If the barcode is too dense for your physical printer, shorten the UID or increase the barcode's printed dimensions (`CODE_SIZE` in `label_generator.py`). Always test with the target scanner before applying labels.
