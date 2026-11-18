#!/usr/bin/env python3
"""Упаковать папку сценария в <имя папки>.zip рядом с ней: одна корневая папка, без __MACOSX и скрытых файлов.

python3 make_archive.py /path/to/10_РЕЦЕПТЫ [--out /path/to/dir]
"""
import sys, zipfile
from pathlib import Path

def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    src = Path(args[0]).resolve()
    out_dir = Path(args[args.index("--out") + 1]).resolve() if "--out" in args else src.parent
    if not src.is_dir():
        sys.exit(f"Нет папки: {src}")
    out = out_dir / f"{src.name}.zip"
    files = sorted(p for p in src.rglob("*") if p.is_file()
                   and not any(part.startswith(".") or part == "__MACOSX" for part in p.relative_to(src).parts))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo(src.name + "/"), "")
        for p in files:
            z.write(p, f"{src.name}/{p.relative_to(src).as_posix()}")  # Python пишет UTF-8 флаг для не-ASCII имён
    print(out)
    for p in files:
        print("  ", p.relative_to(src))

if __name__ == "__main__":
    main()
