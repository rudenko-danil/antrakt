"""Картинки для уроков и историй: главное изображение статьи Википедии или файл Commons.
Берём только файлы с Commons (свободные лицензии), сжимаем до 760 px, пишем images/credits.json."""
import json, os, re, subprocess, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "images")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "AntraktApp/1.0 (https://github.com/rudenko-danil/antrakt; personal learning app)"}


def get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        d = r.read()
    return d if binary else json.loads(d)


def clean(s, n=160):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", "", s or "")).strip()[:n]


spec = json.load(open(os.path.join(ROOT, "images.json"), encoding="utf-8"))
cp = os.path.join(OUT, "credits.json")
credits = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
log = []
for key, s in spec.items():
    out = os.path.join(OUT, key + ".jpg")
    if os.path.exists(out) and key in credits:
        continue
    try:
        if "file" in s:
            fname = s["file"]
        else:
            lang = s.get("lang", "en")
            j = get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(s["wiki"].replace(" ", "_")))
            src = (j.get("originalimage") or j.get("thumbnail") or {}).get("source", "")
            if "/wikipedia/commons/" not in src:
                raise RuntimeError("lead image is not on Commons: " + src[:80])
            fname = urllib.parse.unquote(src.split("/")[-1])
        api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=900&titles="
               + urllib.parse.quote("File:" + fname))
        page = next(iter(get(api)["query"]["pages"].values()))
        ii = page["imageinfo"][0]
        m = ii.get("extmetadata", {})
        raw = out + ".src"
        open(raw, "wb").write(get(ii.get("thumburl") or ii["url"], binary=True))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-vf", "scale='min(760,iw)':-2", "-q:v", "5", out], check=True)
        os.remove(raw)
        credits[key] = {"file": fname, "author": clean((m.get("Artist") or {}).get("value")),
                        "license": (m.get("LicenseShortName") or {}).get("value", ""), "desc": clean((m.get("ImageDescription") or {}).get("value"), 200)}
        log.append(f"OK   {key}: {fname} | {credits[key]['license']} | {credits[key]['author'][:60]}")
    except Exception as e:
        log.append(f"FAIL {key}: {e}")
json.dump(credits, open(cp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(os.path.join(ROOT, "tools", "images_log.txt"), "w").write("\n".join(log) + "\n")
print("\n".join(log))
