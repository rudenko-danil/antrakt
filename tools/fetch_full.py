"""Скачивает полные записи (для разметки времени и нарезки) и аудит метаданных.
Результат кладётся в out/ и публикуется в ветку media-src, чтобы не раздувать сайт."""
import json, os, subprocess, urllib.parse, urllib.request, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "AntraktApp/1.0 (https://github.com/rudenko-danil/antrakt; personal learning app)"}
AUDIO_EXT = (".ogg", ".oga", ".flac", ".mp3", ".opus", ".wav", ".webm")


def get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        data = r.read()
    return data if binary else json.loads(data)


def info(title):
    api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url|size|extmetadata&titles="
           + urllib.parse.quote(title))
    page = next(iter(get(api)["query"]["pages"].values()))
    return page.get("imageinfo", [None])[0]


def search(q):
    api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search&srnamespace=6&srlimit=20&srsearch="
           + urllib.parse.quote(q))
    return [r["title"] for r in get(api)["query"]["search"] if r["title"].lower().endswith(AUDIO_EXT)]


def clean(s, n=300):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", "", s or "")).strip()[:n]


spec = json.load(open(os.path.join(ROOT, "media_full.json"), encoding="utf-8"))
log = []

for key, s in spec.get("full", {}).items():
    try:
        title = "File:" + s["file"] if "file" in s else None
        ii = info(title) if title else None
        if not ii:
            cands = search(s.get("search") or s["file"])
            log.append(f"[{key}] search candidates: " + " || ".join(cands[:10]))
            if not cands:
                raise RuntimeError("nothing found")
            title = cands[0]
            ii = info(title)
        m = ii.get("extmetadata", {})
        raw = os.path.join(OUT, key + ".src")
        open(raw, "wb").write(get(ii["url"], binary=True))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-ac", "2", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "160k",
                        os.path.join(OUT, key + ".mp3")], check=True)
        os.remove(raw)
        log.append(f"[{key}] OK {title} | {clean((m.get('Artist') or {}).get('value'), 120)} | "
                   f"{(m.get('LicenseShortName') or {}).get('value', '')} | date: {clean((m.get('DateTimeOriginal') or {}).get('value'), 60)} | "
                   f"{clean((m.get('ImageDescription') or {}).get('value'), 200)}")
    except Exception as e:
        log.append(f"[{key}] FAIL {e}")

for q in spec.get("searches", []):
    try:
        log.append(f"?? {q}: " + " || ".join(search(q)[:12]))
    except Exception as e:
        log.append(f"?? {q}: ERROR {e}")

for key, fname in spec.get("audit", {}).items():
    try:
        ii = info("File:" + fname)
        m = ii.get("extmetadata", {}) if ii else {}
        log.append(f"AUDIT [{key}] {fname} | {clean((m.get('Artist') or {}).get('value'), 120)} | "
                   f"{(m.get('LicenseShortName') or {}).get('value', '')} | date: {clean((m.get('DateTimeOriginal') or {}).get('value'), 80)} | "
                   f"{clean((m.get('ImageDescription') or {}).get('value'), 300)}")
    except Exception as e:
        log.append(f"AUDIT [{key}] ERROR {e}")

open(os.path.join(OUT, "log.txt"), "w").write("\n".join(log) + "\n")
print("\n".join(log))
