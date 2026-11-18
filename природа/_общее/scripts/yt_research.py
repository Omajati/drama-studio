#!/usr/bin/env python3
"""Разбор конкурентов через YouTube Data API (ключ подставляет прокси сессии; без ключа — передайте YT_KEY).

python3 yt_research.py search "deep sea creatures" [--max 50] [--months 18] [--min 8] [--dur both|medium|long]
    ролики по запросу (порядок по просмотрам): просмотры, подписчики канала, просм./подп., длина, дата, канал, название
python3 yt_research.py channel @Handle|UCxxxx [--n 50]
    последние ролики канала: просмотры, ×медианы канала (выбросы ≥2× помечены *), длина, название
python3 yt_research.py video ID [ID …]
    название, длина, теги, описание (главы-таймкоды видны в описании)
python3 yt_research.py thumbs OUT.jpg ID [ID …]
    лист превью (по 4 в ряд, подпись — просмотры) для разбора упаковки

Ответы кэшируются в .yt_cache/ рядом со скриптом (квота: поиск 100 единиц на каждую длину, т. е. 200 за запрос; остальное 1).
Строки выводятся табами — удобно складывать в файлы разбора.
"""
import hashlib, json, os, re, statistics, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://www.googleapis.com/youtube/v3/"
CACHE = Path(__file__).with_name(".yt_cache")


def call(method: str, **params):
    if os.environ.get("YT_KEY"):
        params["key"] = os.environ["YT_KEY"]
    url = API + method + "?" + urllib.parse.urlencode(params)
    CACHE.mkdir(exist_ok=True)
    f = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if f.is_file():
        return json.loads(f.read_text())
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.loads(r.read().decode())
    f.write_text(json.dumps(data))
    return data


def minutes(iso: str) -> float:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0.0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return round(d * 1440 + h * 60 + mi + s / 60, 1)


def videos(ids):
    out = []
    for i in range(0, len(ids), 50):
        out += call("videos", part="snippet,statistics,contentDetails", id=",".join(ids[i:i + 50]),
                    maxResults=50).get("items", [])
    return out


def channels(ids):
    out = {}
    ids = sorted(set(ids))
    for i in range(0, len(ids), 50):
        for c in call("channels", part="snippet,statistics,contentDetails", id=",".join(ids[i:i + 50]),
                      maxResults=50).get("items", []):
            out[c["id"]] = c
    return out


def fmt(n) -> str:
    n = int(n or 0)
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}K" if n >= 1e3 else str(n)


def opt(args, name, default):
    return type(default)(args[args.index(name) + 1]) if name in args else default


def cmd_search(args):
    q = args[0]
    after = (datetime.now(timezone.utc) - timedelta(days=30 * opt(args, "--months", 18))).strftime("%Y-%m-%dT%H:%M:%SZ")
    durs = {"both": ("medium", "long")}.get(opt(args, "--dur", "both"), (opt(args, "--dur", "both"),))
    ids = []
    for dur in durs:  # «medium» 4–20 мин, «long» > 20 мин: без этого выдачу забивают шортсы
        found = call("search", part="snippet", q=q, type="video", order="viewCount", maxResults=min(opt(args, "--max", 50), 50),
                     publishedAfter=after, relevanceLanguage="en", videoDuration=dur)
        ids += [x["id"]["videoId"] for x in found.get("items", []) if x["id"]["videoId"] not in ids]
    vs = sorted(videos(ids), key=lambda v: -int(v["statistics"].get("viewCount") or 0))
    ch = channels([v["snippet"]["channelId"] for v in vs])
    print(f"# search «{q}» за {opt(args, '--months', 18)} мес., длина от {opt(args, '--min', 8)} мин")
    print("просм\tподп\tпросм/подп\tмин\tдата\tканал\tназвание\tid")
    for v in vs:
        mins = minutes(v["contentDetails"]["duration"])
        if mins < opt(args, "--min", 8):
            continue
        c = ch.get(v["snippet"]["channelId"], {})
        subs = int(c.get("statistics", {}).get("subscriberCount") or 0)
        views = int(v["statistics"].get("viewCount") or 0)
        print(f"{fmt(views)}\t{fmt(subs)}\t{views / subs if subs else 0:.1f}×\t{mins}\t{v['snippet']['publishedAt'][:10]}\t"
              f"{v['snippet']['channelTitle']}\t{v['snippet']['title']}\t{v['id']}")


def channel_id(ref: str) -> str:
    if ref.startswith("UC"):
        return ref
    r = call("channels", part="id", forHandle=ref.lstrip("@"))
    if not r.get("items"):
        sys.exit(f"Канал не найден: {ref}")
    return r["items"][0]["id"]


def cmd_channel(args):
    cid = channel_id(args[0])
    c = channels([cid])[cid]
    uploads = c["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, token, n = [], None, opt(args, "--n", 50)
    while len(ids) < n:
        p = dict(part="contentDetails", playlistId=uploads, maxResults=50)
        if token:
            p["pageToken"] = token
        r = call("playlistItems", **p)
        ids += [x["contentDetails"]["videoId"] for x in r.get("items", [])]
        token = r.get("nextPageToken")
        if not token:
            break
    vs = [v for v in videos(ids[:n]) if minutes(v["contentDetails"]["duration"]) >= 3]  # без шортсов
    views = [int(v["statistics"].get("viewCount") or 0) for v in vs]
    med = statistics.median(views) if views else 0
    print(f"# {c['snippet']['title']} ({args[0]}) · подписчиков {fmt(c['statistics'].get('subscriberCount'))} · "
          f"роликов {c['statistics'].get('videoCount')} · медиана последних {len(vs)}: {fmt(med)}")
    print("просм\t×мед\tмин\tдата\tназвание\tid")
    for v, views_ in zip(vs, views):
        x = views_ / med if med else 0
        print(f"{fmt(views_)}\t{x:.1f}×{' *' if x >= 2 else ''}\t{minutes(v['contentDetails']['duration'])}\t"
              f"{v['snippet']['publishedAt'][:10]}\t{v['snippet']['title']}\t{v['id']}")


def cmd_video(args):
    for v in videos(args):
        s = v["snippet"]
        print(f"# {s['title']} · {fmt(v['statistics'].get('viewCount'))} просм. · {minutes(v['contentDetails']['duration'])} мин · "
              f"{s['channelTitle']} · {s['publishedAt'][:10]} · {v['id']}")
        print("Теги:", ", ".join(s.get("tags", [])[:30]))
        print(s.get("description", "")[:3000])
        print()


def cmd_thumbs(args):
    from io import BytesIO
    from PIL import Image, ImageDraw
    out, ids = args[0], args[1:]
    vs = {v["id"]: v for v in videos(ids)}
    w, h, cols = 480, 270, 4
    rows = (len(ids) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, (h + 28) * rows), "white")
    d = ImageDraw.Draw(sheet)
    for i, vid in enumerate(ids):
        try:
            raw = urllib.request.urlopen(f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", timeout=30).read()
            im = Image.open(BytesIO(raw)).convert("RGB").resize((w, 360)).crop((0, 45, w, 315))
        except Exception:
            im = Image.new("RGB", (w, h), "grey")
        x, y = (i % cols) * w, (i // cols) * (h + 28)
        sheet.paste(im, (x, y))
        v = vs.get(vid, {})
        d.text((x + 6, y + h + 6), f"{fmt(v.get('statistics', {}).get('viewCount'))} · {v.get('snippet', {}).get('title', vid)[:60]}",
               fill="black")
    sheet.save(out, quality=88)
    print(out)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    {"search": cmd_search, "channel": cmd_channel, "video": cmd_video, "thumbs": cmd_thumbs}[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
