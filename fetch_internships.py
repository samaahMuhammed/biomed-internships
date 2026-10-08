#!/usr/bin/env python3
"""Collect biomedical-engineering internships from free job APIs -> site/internships.json
Env vars (all optional, sources without keys are skipped):
  ADZUNA_APP_ID, ADZUNA_APP_KEY   free at developer.adzuna.com
  USAJOBS_KEY, USAJOBS_EMAIL      free at developer.usajobs.gov
  GREENHOUSE_BOARDS               comma list of company board tokens
The Muse needs no key.
"""
import os, re, json, datetime, urllib.request, urllib.parse

QUERIES = ["biomedical engineering intern", "biomedical engineer internship",
           "medical device intern", "bioengineering intern", "biomedical co-op"]
KEEP = re.compile(r"intern|co-?op|student|trainee|apprentice|pathways", re.I)
TOPIC = re.compile(r"biomed|bioengineer|bio-engineer|medical device|biomechanic|biotech|"
                   r"clinical engineer|tissue|biomaterial|medtech|prosthe|orthop|neuro.?engineer|"
                   r"regulatory|biosignal|imaging", re.I)

def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "biomed-interns/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def safe(fn):
    try: return fn()
    except Exception as e:
        print(f"[skip] {fn.__name__}: {e}"); return []

def adzuna():
    i, k = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not (i and k): return []
    out = []
    for q in QUERIES:
        u = ("https://api.adzuna.com/v1/api/jobs/us/search/1?" + urllib.parse.urlencode(
            {"app_id": i, "app_key": k, "what": q, "results_per_page": 50, "max_days_old": 45}))
        for j in get(u).get("results", []):
            out.append(dict(title=j["title"], company=j.get("company", {}).get("display_name", ""),
                location=j.get("location", {}).get("display_name", ""), url=j["redirect_url"],
                posted=j.get("created", "")[:10], source="Adzuna", text=j.get("description", "")))
    return out

def usajobs():
    k, e = os.getenv("USAJOBS_KEY"), os.getenv("USAJOBS_EMAIL")
    if not (k and e): return []
    out = []
    for q in ["biomedical engineer student", "biomedical engineering intern", "bioengineer pathways"]:
        u = "https://data.usajobs.gov/api/search?" + urllib.parse.urlencode({"Keyword": q, "ResultsPerPage": 50})
        d = get(u, {"Host": "data.usajobs.gov", "User-Agent": e, "Authorization-Key": k})
        for it in d["SearchResult"]["SearchResultItems"]:
            m = it["MatchedObjectDescriptor"]
            out.append(dict(title=m["PositionTitle"], company=m["OrganizationName"],
                location=m["PositionLocationDisplay"], url=m["PositionURI"],
                posted=m["PublicationStartDate"][:10], deadline=m.get("ApplicationCloseDate", "")[:10],
                source="USAJOBS", text=m["PositionTitle"]))
    return out

def muse():
    out = []
    for p in range(0, 5):
        u = "https://www.themuse.com/api/public/jobs?" + urllib.parse.urlencode(
            [("category", "Science and Engineering"), ("category", "Healthcare"), ("level", "Internship"), ("page", p)])
        for j in get(u).get("results", []):
            out.append(dict(title=j["name"], company=j["company"]["name"],
                location=", ".join(l["name"] for l in j.get("locations", [])),
                url=j["refs"]["landing_page"], posted=j["publication_date"][:10],
                source="The Muse", text=re.sub("<[^>]+>", " ", j.get("contents", ""))))
    return out

def greenhouse():
    out = []
    for b in filter(None, os.getenv("GREENHOUSE_BOARDS", "").split(",")):
        for j in get(f"https://boards-api.greenhouse.io/v1/boards/{b.strip()}/jobs").get("jobs", []):
            out.append(dict(title=j["title"], company=b.strip().title(), location=j.get("location", {}).get("name", ""),
                url=j["absolute_url"], posted=j.get("updated_at", "")[:10], source="Greenhouse", text=j["title"]))
    return out

def main():
    jobs = [j for f in (adzuna, usajobs, muse, greenhouse) for j in safe(f)]
    seen, final = set(), []
    for j in jobs:
        blob = f'{j["title"]} {j.get("text","")[:1500]}'
        if not (KEEP.search(j["title"]) and TOPIC.search(blob)): continue
        key = (j["title"].lower().strip(), j["company"].lower().strip(), j["location"].lower().strip())
        if key in seen: continue
        seen.add(key); j.pop("text", None); final.append(j)
    final.sort(key=lambda j: j.get("posted", ""), reverse=True)
    out = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "count": len(final), "jobs": final}
    os.makedirs("site", exist_ok=True)
    json.dump(out, open("site/internships.json", "w"), indent=1)
    print(f"Wrote {len(final)} internships")

if __name__ == "__main__": main()
