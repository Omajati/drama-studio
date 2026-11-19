#!/usr/bin/env python3
"""Проверка папки сценария перед упаковкой.

python3 check_script.py истории/сценарии/01_ПАМЯТЬ [--wpm 120]

Канал «Истории RU» («Как жили в СССР», с 19.11.2026): 30–40 мин ≈ 3 600–4 800 слов, число сцен не ограничено — сколько нужно по сценарию (первые ~4–5 минут — сцена на предложение, решение 19.11.2026).

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
           r"\bэто не\b[^.]{0,40}\. это\b", r"давайте разбер[её]мся", r"в этом видео", r"начн[её]м с того"],
}
UPLOAD_HEADS = ["## 1. Название", "## 2. Превью", "## 3. Описание", "## 4. Теги", "## 5. Категория", "## Служебное", "## Проверка"]


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


def check_binding(root, errors, warns):
    """привязка.txt: «S014 | первые слова сцены» — программа кладёт сцену точно на эти слова озвучки."""
    f = root / "привязка.txt"
    if not f.is_file():
        return
    scenes_file = root / "сцены_генерация.txt"
    ids = re.findall(r"(?m)^\s*SCENE\s+(S\d{3})", scenes_file.read_text("utf-8")) if scenes_file.is_file() else []
    voice = next(iter(sorted(root.glob("озвучка_*.txt"))), None)
    words = [w for w in re.findall(r"[\wё]+", voice.read_text("utf-8").lower().replace("ё", "е"))] if voice else []
    got, pos = {}, 0
    for n, line in enumerate(f.read_text("utf-8").splitlines(), 1):
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.fullmatch(r"\s*(S\d{3})\s*\|\s*(.+?)\s*", line)
        if not m:
            errors.append(f"привязка.txt, строка {n}: нужен вид «S014 | первые слова сцены»")
            continue
        got[m.group(1)] = m.group(2)
        seq = re.findall(r"[\wё]+", m.group(2).lower().replace("ё", "е"))[:6]
        found = next((i for i in range(pos, len(words) - len(seq) + 1) if words[i:i + len(seq)] == seq), None) if seq else None
        if found is None:
            errors.append(f"привязка.txt, строка {n}: слов «{m.group(2)[:40]}» нет в озвучке после прошлой сцены (порядок или опечатка)")
        else:
            pos = found + 1
    missing = [s for s in ids if s not in got]
    if ids and missing:
        errors.append(f"привязка.txt: нет строк для сцен {', '.join(missing[:8])}{' …' if len(missing) > 8 else ''}")
    extra = [s for s in got if s not in ids]
    if extra:
        errors.append(f"привязка.txt: сцен {', '.join(extra[:8])} нет в сцены_генерация.txt")
    print(f"Привязка сцен к словам: {len(got)} строк")

def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    root = Path(args[0])
    wpm = int(args[args.index("--wpm") + 1]) if "--wpm" in args else 120
    errors, warns = [], []
    trailer = "ТРЕЙЛЕР" in root.name.upper()  # короткий ролик-приветствие канала: своя норма слов и сцен
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
    for n in sorted(set(names) - expected - {"вставки.txt", "привязка.txt", "ударения.txt"}):
        warns.append(f"Лишний файл {n}: в архиве должны быть только файлы формата.")
    check_inserts(root, errors, warns)
    check_binding(root, errors, warns)

    for lang in langs:
        p = root / f"озвучка_{lang}.txt"
        text = p.read_text("utf-8")
        words = len(text.split())
        digits = [(i + 1, l.strip()[:80]) for i, l in enumerate(text.splitlines()) if re.search(r"\d", l)]
        for ln, l in digits[:10]:
            errors.append(f"{p.name}:{ln}: цифра в озвучке — «{l}»")
        if len(digits) > 10:
            errors.append(f"{p.name}: ещё {len(digits) - 10} строк с цифрами")
        abbr = sorted(set(re.findall(r"\b[А-ЯЁA-Z]{2,}\b", text)))
        if abbr:  # решение владельца 19.11.2026: голос читает сокращения странно
            errors.append(f"{p.name}: сокращения в озвучке — {', '.join(abbr[:10])} (писать словами: «Советский Союз», «госбезопасность»; «загс», «вуз» — строчными)")
        for ln, l in enumerate(text.splitlines(), 1):
            if re.match(r"\s*(#|\[|глава|chapter|cap[ií]tulo|kapitel|SCENE|S\d{3})", l, re.I):
                errors.append(f"{p.name}:{ln}: служебная пометка в озвучке — «{l.strip()[:60]}»")
        for pat in AI.get(lang, []):
            for m in re.finditer(pat, text, re.I):
                warns.append(f"{p.name}: ИИ-оборот «{m.group(0)[:60]}»")
        paras = len([x for x in re.split(r"\n\s*\n", text) if x.strip()])
        
        if trailer:
            if not 120 <= words <= 260:
                warns.append(f"{p.name}: {words} слов, норма трейлера 60–100 с — 130–230 слов")
        elif not 3300 <= words <= 4900:
            warns.append(f"{p.name}: {words} слов, норма 30–40 мин — 3 600–4 800")
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
            if not re.search(r"(?m)^## 6\. Закреплённый комментарий", ut):
                warns.append(f"{up.name}: нет раздела «## 6. Закреплённый комментарий» (вовлечение, с 19.11.2026)")
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
        lo, hi = (15, 40) if trailer else (1, 10 ** 6)  # решение 19.11.2026: сцен сколько нужно по сценарию
        if ids and not lo <= len(ids) <= hi:
            errors.append(f"сцены_генерация.txt: сцен {len(ids)}, нужно от {lo} до {hi} (канал «Истории RU»{', трейлер' if trailer else ''})")

    for w in warns:
        print("ПРЕДУПРЕЖДЕНИЕ:", w)
    for e in errors:
        print("ОШИБКА:", e)
    print("ИТОГ:", "ошибок нет" if not errors else f"ошибок {len(errors)}")
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
