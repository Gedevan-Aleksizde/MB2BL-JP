# /// script
# requires-python = ">=3.10"
# dependencies = ["polib>=1.2.0,<2"]
# ///
"""Import an installed module's VoiceLines.txt files into a local PO file."""

import argparse
from pathlib import Path
import sys

from voicelines import export_po


MODULES_DIR = Path("C:/Program Files (x86)/Steam/steamapps/common/Mount & Blade II Bannerlord/Modules")
MODS_DIR = Path(__file__).resolve().parent.parent / "Mods"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", help="Installed module folder name (e.g. LT_Nemesis)")
    parser.add_argument("--po", type=Path,
                        help="PO path, relative to Mods/<folder> unless absolute (default: <folder>.po)")
    args = parser.parse_args()
    if args.folder in ("", ".", "..") or Path(args.folder).name != args.folder:
        parser.error("folder must be a module folder name, not a path")
    root = MODULES_DIR / args.folder
    po_path = MODS_DIR / args.folder / (args.po if args.po is not None else Path(f"{args.folder}.po"))
    try:
        files, entries = export_po(root, po_path)
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Imported {entries} entries from {files} files to {po_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
