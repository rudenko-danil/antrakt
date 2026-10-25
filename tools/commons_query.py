"""Листинг аудиофайлов в категориях Commons — помогает выбрать запись. Пишет tools/query_results.txt."""
import json, os, urllib.parse, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "AntraktApp/1.0 (https://github.com/rudenko-danil/antrakt)"}
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r: return json.loads(r.read())
qs = json.load(open(os.path.join(ROOT, "media.json"), encoding="utf-8")).get("queries", [])
out = []
for cat in qs:
    out.append(f"== {cat}")
    url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=categorymembers&gcmtype=file&gcmlimit=100"
           "&prop=imageinfo&iiprop=size|mime|extmetadata&gcmtitle=" + urllib.parse.quote(cat))
    try:
        pages = get(url).get("query", {}).get("pages", {})
        for p in pages.values():
            ii = (p.get("imageinfo") or [{}])[0]
            if not ii.get("mime", "").startswith(("audio", "application/ogg", "video")): continue
            m = ii.get("extmetadata", {})
            art = (m.get("Artist") or {}).get("value", "")[:120].replace("\n", " ")
            desc = (m.get("ImageDescription") or {}).get("value", "")[:160].replace("\n", " ")
            out.append(f"{p['title']} | {ii.get('duration', '')} | {art} | {desc}")
    except Exception as e:
        out.append(f"ERROR {e}")
open(os.path.join(ROOT, "tools", "query_results.txt"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
