#!/usr/bin/env python3
"""Проверка папки сценария перед упаковкой.

python3 check_script.py истории/сценарии/01_ПАМЯТЬ [--wpm 120]

Канал «Истории RU»: 30 мин ≈ 3 400–3 800 слов, сцен 90–130.

Проверяет: набор файлов и их имена; в озвучке нет цифр и служебных пометок; объём и хронометраж;
ИИ-обороты; сцены S001… подряд без пропусков, каждая отдельным абзацем, со Style и запретом текста;
референсы; разделы файла загрузки и превью. Выход 1, если есть ошибки (предупреждения не валят).
"""
import re, sys
from pathlib import Path

AI = {
    "EN": [r"\bit'?s not (?:just )?\w+[^.]{0,40}, it'?s\b", r"let that sink in", r"\bnot just\b[^.]{0,60}\bbut\b"],
    "ES": [r"\bno es\b[^.]{0,60}\bsino\b", r"\bno solo\b[^.]{0,60}\bsino\b", r"pi[eé]nsenlo"],
    "DE": [r"\bnicht nur\b[^.]{0,60}\bsondern\b", r"\bes ist nicht\b[^.]{0,40}, es ist\b"],
    "RU": [r"\bэто не\b[^.]{0,40}, это\b", r"\bне просто\b[^.]{0,60}\bа\b", r"вдумайся", r"\bмужик",
           r"давайте разбер[её]мся", r"в этом видео", r"начн[её]м с того"],
}
UPLOAD_HEADS = ["## 1. Название", "## 2. Превью", "## 3. Описание", "## 4. Теги", "## 5. Категория", "## Служебное", "## Проверка"]

def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    root = Path(args[0])
    wpm = int(args[args.index("--wpm") + 1]) if "--wpm" in args else 120
    errors, warns = [], []
    names = [p.name for p in root.iterdir() if p.is_file() and not p.name.startswith(".")]
    if not re.fullmatch(r"\d{2,3}_[A-ZА-ЯЁ0-9_]+", root.name):
        warns.append(f"Имя папки «{root.name}»: ожидается NN_КЛЮЧ капсом (10_РЕЦЕПТЫ).")
    langs = sorted({m.group(1) for n in names if (m := re.fullmatch(r"озвучка_([A-Z]{2})\.txt", n))})
    if not langs:
        errors.append("Нет файла озвучка_<LANG>.txt")
    if "сцены_генерация.txt" not in names:
        errors.append("Нет файла сцены_генерация.txt")
    expected = {"сцены_генерация.txt"} | {f"{k}_{l}{e}" for l in langs for k, e in
                (("озвучка", ".txt"), ("превью", ".txt"), ("загрузка_YouTube", ".md"))}
    for n in sorted(expected - set(names)):
        errors.append(f"Нет файла {n}")
    for n in sorted(set(names) - expected):
        warns.append(f"Лишний файл {n}: в архиве должны быть только файлы формата.")

    for lang in langs:
        p = root / f"озвучка_{lang}.txt"
        text = p.read_text("utf-8")
        words = len(text.split())
        digits = [(i + 1, l.strip()[:80]) for i, l in enumerate(text.splitlines()) if re.search(r"\d", l)]
        for ln, l in digits[:10]:
            errors.append(f"{p.name}:{ln}: цифра в озвучке — «{l}»")
        if len(digits) > 10:
            errors.append(f"{p.name}: ещё {len(digits) - 10} строк с цифрами")
        for ln, l in enumerate(text.splitlines(), 1):
            if re.match(r"\s*(#|\[|глава|chapter|cap[ií]tulo|kapitel|SCENE|S\d{3})", l, re.I):
                errors.append(f"{p.name}:{ln}: служебная пометка в озвучке — «{l.strip()[:60]}»")
        for pat in AI.get(lang, []):
            for m in re.finditer(pat, text, re.I):
                warns.append(f"{p.name}: ИИ-оборот «{m.group(0)[:60]}»")
        paras = len([x for x in re.split(r"\n\s*\n", text) if x.strip()])
        
        if not 3300 <= words <= 3900:
            warns.append(f"{p.name}: {words} слов, норма 30 мин — 3 400–3 800")
        print(f"{p.name}: {words} слов ≈ {words / wpm:.0f} мин при {wpm} сл/мин, абзацев {paras}")
        up = root / f"загрузка_YouTube_{lang}.md"
        if up.is_file():
            ut = up.read_text("utf-8")
            for h in UPLOAD_HEADS:
                if h not in ut:
                    errors.append(f"{up.name}: нет раздела «{h}»")
            title = re.search(r"(?m)^## 1\. Название\s*\n+(.+)", ut)
            if title:
                n = len(title.group(1).strip())
                print(f"{up.name}: название {n} знаков")
                if not 55 <= n <= 95:
                    warns.append(f"{up.name}: название {n} знаков, норма канала 55–95")
            if not re.search(r"Темп:\s*\d+ слов в минуту", ut):
                errors.append(f"{up.name}: в «Служебном» нет строки «Темп: 120 слов в минуту» (по ней программа ставит главы)")
            if "Факты [CHECK]" not in ut:
                errors.append(f"{up.name}: нет раздела «Факты [CHECK]» в «Служебном»")
            if "Источники" not in ut:
                warns.append(f"{up.name}: в описании нет блока «Источники»")
            stamps = re.findall(r"(?m)^\d{1,2}:\d{2}(?::\d{2})? ", ut)
            if stamps and not ut.count("0:00 "):
                errors.append(f"{up.name}: таймкоды должны начинаться с 0:00")
        th = root / f"превью_{lang}.txt"
        if th.is_file():
            tt = th.read_text("utf-8")
            for h in ("1. ПРОМТ КАРТИНКИ БЕЗ ТЕКСТА", "2. ТЕКСТ", "3. ПЛАШКА"):
                if h not in tt:
                    errors.append(f"{th.name}: нет секции «{h}»")
            if re.search(r"(?m)^РАСКЛАДКА:\s*[А-ЯЁ]", tt):
                errors.append(f"{th.name}: буква раскладки кириллицей — программа превратит её в A, нужна латиница")
            elif not re.search(r"(?m)^РАСКЛАДКА:\s*[A-H]\b", tt):
                warns.append(f"{th.name}: нет строки «РАСКЛАДКА: <A–H>» (см. 10_превью_раскладки.md)")

    sc = root / "сцены_генерация.txt"
    if sc.is_file():
        st = sc.read_text("utf-8")
        for h in ("MANDATORY RULE — SCENE NUMBERING", "MANDATORY RULE — FILE NAMES", "PROJECT CONTEXT:",
                  "Recurring characters", "Hard rules:", "SCENES (one image each", "FINAL CHECK BEFORE EXPORT"):
            if h not in st:
                errors.append(f"сцены_генерация.txt: нет блока «{h}»")
        ids = [int(x) for x in re.findall(r"(?m)^SCENE S(\d{3})\.", st)]
        refs = re.findall(r"(?m)^REFERENCE (R\d+)\.", st)
        if ids != list(range(1, len(ids) + 1)):
            missing = sorted(set(range(1, max(ids or [0]) + 1)) - set(ids))
            errors.append(f"сцены_генерация.txt: номера сцен не подряд (пропуски/повторы: {missing[:10] or 'порядок'})")
        for m in re.finditer(r"(?m)^SCENE (S\d{3})\.(.*)$", st):
            body = m.group(2)
            if "no text" not in body.lower():
                errors.append(f"{m.group(1)}: нет «no text» в хвосте стиля")
            if "Style:" not in body:
                warns.append(f"{m.group(1)}: нет «Style:» — программа подставит общий стиль")
        if re.search(r"(?m)^SCENE S\d{3}\..*\n(?!\s*\n|\Z)", st):
            errors.append("сцены_генерация.txt: сцены должны разделяться пустой строкой (одна сцена = один абзац)")
        print(f"сцены_генерация.txt: сцен {len(ids)}, референсов {len(refs)}")
        if langs:
            w = len((root / f"озвучка_{langs[0]}.txt").read_text("utf-8").split())
            per = w / wpm * 60 / max(len(ids), 1)
            print(f"   ≈ {per:.0f} с на сцену")
        if ids and not 90 <= len(ids) <= 130:
            errors.append(f"сцены_генерация.txt: сцен {len(ids)}, нужно от 90 до 130 (канал «Истории RU»)")

    for w in warns:
        print("ПРЕДУПРЕЖДЕНИЕ:", w)
    for e in errors:
        print("ОШИБКА:", e)
    print("ИТОГ:", "ошибок нет" if not errors else f"ошибок {len(errors)}")
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
