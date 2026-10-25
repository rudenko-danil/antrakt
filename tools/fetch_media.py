"""Скачивает портреты (Википедия) и записи (Wikimedia Commons) по media.json,
нарезает фрагменты и кладёт их в репозиторий. Запускается из GitHub Actions."""
import json, os, subprocess, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "AntraktApp/1.0 (https://github.com/rudenko-danil/antrakt; personal learning app)"}
media = json.load(open(os.path.join(ROOT, "media.json"), encoding="utf-8"))
os.makedirs(os.path.join(ROOT, "portraits"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "audio", "real"), exist_ok=True)


def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    return data if binary else json.loads(data)


report, credits = [], {}

for key, title in media["portraits"].items():
    out = os.path.join(ROOT, "portraits", f"{key}.jpg")
    if os.path.exists(out):
        continue
    try:
        j = get("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title))
        src = (j.get("thumbnail") or {}).get("source") or (j.get("originalimage") or {}).get("source")
        raw = get(src, binary=True)
        tmp = out + ".src"
        open(tmp, "wb").write(raw)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-vf",
                        "scale=320:320:force_original_aspect_ratio=increase,crop=320:320:(iw-320)/2:0", "-q:v", "4", out], check=True)
        os.remove(tmp)
        report.append(f"portrait ok  {key}")
    except Exception as e:
        report.append(f"portrait FAIL {key}: {e}")

for track, a in media["audio"].items():
    out = os.path.join(ROOT, "audio", "real", f"{track}.mp3")
    if os.path.exists(out):
        continue
    try:
        api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url|extmetadata&titles="
               + urllib.parse.quote("File:" + a["file"]))
        pages = get(api)["query"]["pages"]
        page = next(iter(pages.values()))
        info = page["imageinfo"][0]
        src = os.path.join(ROOT, "audio", "real", f"{track}.src")
        open(src, "wb").write(get(info["url"], binary=True))
        start, dur = float(a.get("start", 0)), float(a.get("dur", 45))
        fade = 2.5
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(dur), "-i", src,
                        "-af", f"afade=t=in:d=0.3,afade=t=out:st={dur - fade}:d={fade},loudnorm=I=-16:TP=-1.5",
                        "-ac", "2", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "128k", out], check=True)
        os.remove(src)
        meta = info.get("extmetadata", {})
        credits[track] = {
            "file": a["file"],
            "artist": (meta.get("Artist") or {}).get("value", ""),
            "license": (meta.get("LicenseShortName") or {}).get("value", ""),
        }
        report.append(f"audio ok     {track}")
    except Exception as e:
        report.append(f"audio FAIL   {track}: {e}")

cpath = os.path.join(ROOT, "audio", "real", "credits.json")
old = json.load(open(cpath, encoding="utf-8")) if os.path.exists(cpath) else {}
old.update(credits)
json.dump(old, open(cpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n".join(report))
open(os.path.join(ROOT, "tools", "last_fetch.txt"), "w").write("\n".join(report) + "\n")
