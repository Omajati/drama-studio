#!/usr/bin/env python3
"""Проверка папки сценария канала природы перед упаковкой (формат — природа/_общее/формат_архива.md).

python3 check_script.py природа/<канал>/сценарии/04_ЛЮТЫЙ_ВОЛК [--wpm 160] [--min 12 --max 24] [--trailer]

--trailer — трейлер канала: быстрая нарезка, 1–4 с на сцену (одно предложение = одна сцена).

Проверяет: три файла формата; в озвучке нет цифр, служебных пометок и запрещённых оборотов; хронометраж;
сцены S001… подряд, по абзацу, со Style и «no text», 6–10 секунд озвучки на сцену; разделы файла загрузки,
превью: превью_EN.txt с РАСКЛАДКОЙ или промпт и слова в «2. Превью» в форме, которую читает программа. Выход 1, если есть ошибки (предупреждения не валят).
"""
import re
import sys
from pathlib import Path

BANNED = [
    (r"\bdid you know\b", "«did you know»"), (r"\bin this video\b", "«in this video»"), (r"\blet'?s dive in\b", "«let's dive in»"),
    (r"\bnature is amazing\b", "«nature is amazing»"), (r"\blet that sink in\b", "«let that sink in»"),
    (r"\bsmash (?:that|the) like\b", "просьба лайка"), (r"\bring the bell\b", "колокольчик"),
]
NOT_X_BUT_Y = r"\bit'?s not (?:just )?[^.]{1,40}[,;—-]+\s*it'?s\b|\bnot just\b[^.]{0,60}\bbut\b"
SOFT_STARTS = r"^(?:start with|there are two main ways|let'?s look at|let'?s start|first, let'?s|so, )"
UPLOAD_HEADS = ["## 1. Название", "## 2. Превью", "## 3. Описание", "## 4. Теги", "## 5. Категория", "## Служебное", "## Проверка"]


def opt(args, name, default):
    return type(default)(args[args.index(name) + 1]) if name in args else default



# --- вставки.txt: заказ моушен-вставок (см. _общее/вставки_моушен.md) ---
INSERT_KINDS = {"цифра", "число", "цифра на фото", "число на фото", "термометр", "календарь", "сетка", "сетка-календарь",
                "проценты", "шкала", "слой", "слой и человек", "график", "столбцы", "сравнение", "против",
                "линия времени", "даты", "карта", "карта рельефа", "глобус", "место", "плашка места", "документ",
                "цитата", "список"}


def check_inserts(root, errors, warns):
    f = root / "вставки.txt"
    if not f.is_file():
        warns.append("нет вставки.txt: моушен-вставки заказываются в каждом сценарии (_общее/вставки_моушен.md)")
        return
    scenes_file = root / "сцены_генерация.txt"
    ids = set(re.findall(r"(?m)^\s*SCENE\s+(S\d{3})", scenes_file.read_text("utf-8"))) if scenes_file.is_file() else set()
    seen = []
    for n, line in enumerate(f.read_text("utf-8").splitlines(), 1):
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.fullmatch(r"\s*(S\d{3})\s*\|\s*([^|]+?)\s*\|\s*(.+?)\s*", line)
        if not m:
            errors.append(f"вставки.txt, строка {n}: нужен вид «S012 | вид | что показать»")
            continue
        sid, kind, what = m.group(1), " ".join(m.group(2).lower().replace("ё", "е").split()), m.group(3)
        if ids and sid not in ids:
            errors.append(f"вставки.txt, строка {n}: сцены {sid} нет в сцены_генерация.txt")
        if kind not in {k.replace("ё", "е") for k in INSERT_KINDS}:
            errors.append(f"вставки.txt, строка {n}: неизвестный вид «{m.group(2)}» (список — _общее/вставки_моушен.md)")
        if sid in [s for s, _ in seen]:
            errors.append(f"вставки.txt, строка {n}: на сцену {sid} уже есть вставка")
        if len(what) < 4:
            errors.append(f"вставки.txt, строка {n}: не написано, что показать")
        seen.append((sid, kind))
    nums = sorted(int(s[1:]) for s, _ in seen)
    for a, b in zip(nums, nums[1:]):
        if b - a == 1:
            warns.append(f"вставки.txt: вставки на соседних сценах S{a:03d} и S{b:03d} — лучше не подряд")
    if seen:
        print(f"Вставок заказано: {len(seen)}")

def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    root = Path(args[0])
    wpm, lo, hi = opt(args, "--wpm", 160), opt(args, "--min", 10), opt(args, "--max", 26)
    errors, warns = [], []
    names = {p.name for p in root.iterdir() if p.is_file() and not p.name.startswith(".")}
    if not re.fullmatch(r"\d{2,3}_[A-ZА-ЯЁ0-9_]+", root.name):
        warns.append(f"Имя папки «{root.name}»: ожидается NN_КЛЮЧ капсом (04_ЛЮТЫЙ_ВОЛК).")
    expected = {"озвучка_EN.txt", "сцены_генерация.txt", "загрузка_YouTube_EN.md"}
    for n in sorted(expected - names):
        errors.append(f"Нет файла {n}")
    for n in sorted(names - expected - {"вставки.txt"} - {"превью_EN.txt"}):
        warns.append(f"Лишний файл {n}: в архиве только файлы формата")
    check_inserts(root, errors, warns)
    th = root / "превью_EN.txt"
    if th.is_file():
        tt = th.read_text("utf-8")
        lay = re.search(r"(?m)^\s*РАСКЛАДКА:\s*([A-H])", tt)
        if not lay:
            errors.append("превью_EN.txt: нет строки «РАСКЛАДКА: <буква> — <название>»")
        elif lay.group(1) in "ABH":
            warns.append(f"превью_EN.txt: раскладка {lay.group(1)} — стиль драм; природе подходят C, D, E, F, G")
        for h in (r"1\.\s+ПРОМТ КАРТИНКИ БЕЗ ТЕКСТА", r"2\.\s+ТЕКСТ", r"3\.\s+ПЛАШКА"):
            if not re.search(r"(?m)^\s*" + h, tt):
                errors.append(f"превью_EN.txt: нет раздела «{h.replace(chr(92), '')}»")
        print(f"превью_EN.txt: раскладка {lay.group(1) if lay else '?'}")

    words = 0
    voice = root / "озвучка_EN.txt"
    if voice.is_file():
        text = voice.read_text("utf-8")
        words = len(text.split())
        lines = text.splitlines()
        digits = [(i + 1, l.strip()[:80]) for i, l in enumerate(lines) if re.search(r"\d", l)]
        for ln, l in digits[:10]:
            errors.append(f"озвучка_EN.txt:{ln}: цифра — «{l}»")
        if len(digits) > 10:
            errors.append(f"озвучка_EN.txt: ещё {len(digits) - 10} строк с цифрами")
        for ln, l in enumerate(lines, 1):
            if re.match(r"\s*(#|\[|chapter\b|SCENE|S\d{3}|REFERENCE)", l, re.I):
                errors.append(f"озвучка_EN.txt:{ln}: служебная пометка — «{l.strip()[:60]}»")
        for pat, name in BANNED:
            for m in re.finditer(pat, text, re.I):
                errors.append(f"озвучка_EN.txt: запрещённый оборот {name}: «{m.group(0)}»")
        n = len(re.findall(NOT_X_BUT_Y, text, re.I))
        if n > 1:
            warns.append(f"озвучка_EN.txt: оборот «not X, but Y» {n} раз (норма — не больше одного)")
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        for p in paras:
            if re.match(SOFT_STARTS, p, re.I):
                warns.append(f"озвучка_EN.txt: мягкое начало абзаца — «{p[:50]}…» (главы открываются крючком)")
        mins = words / wpm
        print(f"озвучка_EN.txt: {words} слов ≈ {mins:.1f} мин при {wpm} сл/мин, абзацев {len(paras)}")
        if not lo <= mins <= hi:
            warns.append(f"Хронометраж {mins:.1f} мин вне {lo}–{hi} мин для этого канала")

    up = root / "загрузка_YouTube_EN.md"
    if up.is_file():
        ut = up.read_text("utf-8")
        for h in UPLOAD_HEADS:
            if h not in ut:
                errors.append(f"{up.name}: нет раздела «{h}»")
        title = re.search(r"(?m)^## 1\. Название\s*\n+(.+)", ut)
        if title:
            n = len(title.group(1).strip())
            print(f"{up.name}: название {n} знаков — {title.group(1).strip()}")
            if not 30 <= n <= 75:
                warns.append(f"{up.name}: название {n} знаков, у хитов ниши 40–70")
        thumb = re.search(r"(?ms)^## 2\. Превью\s*\n(.*?)(?=^## )", ut)
        body = re.split(r"(?i)\*\*\s*запасн", thumb.group(1))[0] if thumb else ""
        if th.is_file():
            pass  # превью рисуется по превью_EN.txt; раздел 2 — краткая запись и запасные идеи
        elif not re.search(r"(?m)^\s*>\s*\S", body):
            errors.append(f"{up.name}: в «2. Превью» нет промпта картинки строкой «> …»")
        elif "no text" not in body.lower():
            warns.append(f"{up.name}: в промпте превью нет «no text»")
        pairs = re.findall(r"([^\n—;,*]+?)\s+—\s+(чёрн\w*|черн\w*|бел\w*(?:\s+в\s+красн\w*\s+плашк\w*)?|красн\w*)", body)
        if th.is_file():
            pass
        elif not re.search(r"(?i)текст[^:\n]*:", body):
            warns.append(f"{up.name}: в «2. Превью» нет строки «Текст: СЛОВА — цвет» (превью будет без слов)")
        elif not pairs:
            errors.append(f"{up.name}: строка «Текст:» не в форме «СЛОВА — чёрный; СЛОВО — белый в красной плашке»")
        elif len(pairs) > 3:
            warns.append(f"{up.name}: на превью {len(pairs)} строк, программа нарисует только 3")
        stamps = re.findall(r"(?m)^\d{1,2}:\d{2}(?::\d{2})? ", ut)
        if stamps and "0:00 " not in ut:
            errors.append(f"{up.name}: таймкоды должны начинаться с 0:00")

    sc = root / "сцены_генерация.txt"
    if sc.is_file():
        st = sc.read_text("utf-8")
        for h in ("MANDATORY RULE — SCENE NUMBERING", "MANDATORY RULE — FILE NAMES", "PROJECT CONTEXT:",
                  "Hard rules:", "SCENES (one image each", "FINAL CHECK BEFORE EXPORT"):
            if h not in st:
                errors.append(f"сцены_генерация.txt: нет блока «{h}»")
        ids = [int(x) for x in re.findall(r"(?m)^SCENE S(\d{3})\.", st)]
        if ids != list(range(1, len(ids) + 1)):
            missing = sorted(set(range(1, max(ids or [0]) + 1)) - set(ids))
            errors.append(f"сцены_генерация.txt: номера сцен не подряд (пропуски/повторы: {missing[:10] or 'порядок'})")
        for m in re.finditer(r"(?m)^SCENE (S\d{3})\.(.*)$", st):
            if "no text" not in m.group(2).lower():
                errors.append(f"{m.group(1)}: нет «no text» в хвосте стиля")
            if "Style:" not in m.group(2):
                warns.append(f"{m.group(1)}: нет «Style:» — программа подставит общий стиль")
        if re.search(r"(?m)^SCENE S\d{3}\..*\n(?!\s*\n|\Z)", st):
            errors.append("сцены_генерация.txt: сцены разделяются пустой строкой (одна сцена = один абзац)")
        refs = re.findall(r"(?m)^REFERENCE (R\d+)\.", st)
        print(f"сцены_генерация.txt: сцен {len(ids)}, референсов {len(refs)}")
        if words and ids:
            per = words / wpm * 60 / len(ids)
            trailer = "--trailer" in args
            print(f"   ≈ {per:.1f} с на сцену (норма сети 5–9: начало по 3–6 с, дальше 7–9" + ("; трейлер — 1–4)" if trailer else ")"))
            if trailer:
                if not 1 <= per <= 4:
                    errors.append(f"сцены_генерация.txt: {per:.1f} с на сцену, для трейлера нужно 1–4 "
                                  "(одна короткая фраза = одна сцена)")
            elif not 5 <= per <= 9:
                errors.append(f"сцены_генерация.txt: {per:.1f} с на сцену, нужно в среднем 5–9 (первые ~4–5 минут — "
                              f"сцена на предложение по 3–6 с, дальше 7–9 с) — для этого текста ≈ {round(words / wpm * 60 / 6.5)} сцен")

    for w in warns:
        print("ПРЕДУПРЕЖДЕНИЕ:", w)
    for e in errors:
        print("ОШИБКА:", e)
    print("ИТОГ:", "ошибок нет" if not errors else f"ошибок {len(errors)}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
