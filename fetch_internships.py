#!/usr/bin/env python3
"""Collect biomedical-engineering internships from free job APIs -> site/internships.json
Env vars (all optional, sources without keys are skipped):
  ADZUNA_APP_ID, ADZUNA_APP_KEY   free at developer.adzuna.com
  USAJOBS_KEY, USAJOBS_EMAIL      free at developer.usajobs.gov
  GREENHOUSE_BOARDS               comma list of company board tokens
The Muse needs no key.
"""
import os, re, json, datetime, urllib.request, urllib.parse

DOMAINS = ["medical device", "biomedical", "healthcare", "health tech", "digital health", "biotech",
           "pharma", "clinical", "neuro", "immunolog", "genomic", "diagnostic", "bioinformatics",
           "surgical", "therapeutic", "bioprocess", "medtech", "life science", "cell therapy", "bioengineer"]
FIELDS = ["software engineer", "mechanical engineer", "chemical engineer", "electrical engineer",
          "neuroengineer", "immunology", "materials engineer", "data science", "machine learning",
          "bioinformatics", "process engineer", "quality engineer", "regulatory", "research"]
QUERIES = [f"{f} intern {d}" for f in FIELDS[:8] for d in ("medical device", "biotech", "healthcare")] + \
          ["biomedical engineering intern", "bioengineering intern", "neuroscience engineering intern",
           "immunology research intern", "bioprocess engineering intern", "bioinformatics intern"]
KEEP = re.compile(r"intern|co-?op|student|trainee|apprentice|pathways", re.I)
TOPIC = re.compile("|".join(DOMAINS), re.I)
EXCLUDE = re.compile(r"pharmacy|pharmacist|retail|cashier|store |nurs(e|ing)|dental|sales|marketing|"
                     r"banking|insurance|human resources|\bHR\b|accounting|finance", re.I)
ENGINEERING = re.compile(r"engineer|software|developer|data|research|scien|lab|bio|chem|neuro|immun|"
                         r"mechanical|electrical|materials|quality|process|regulatory|clinical|R&D|technical|computational", re.I)
MAX_AGE_DAYS = 120
DISCIPLINES = {
 "Software / Data": r"software|developer|data scien|machine learning|\bML\b|\bAI\b|bioinformat|computational|firmware|embedded",
 "Mechanical": r"mechanical|biomechanic|manufactur|\bCAD\b|design engineer|product development",
 "Chemical / Process": r"chemical|bioprocess|process engineer|formulation|\bCMC\b|downstream|upstream",
 "Electrical": r"electrical|electronics|hardware|signal|\bRF\b|sensor|circuit",
 "Neuro": r"neuro|brain|\bBCI\b|neuromod",
 "Immunology / Bio": r"immun|antibod|cell therapy|molecular|genomic|\bPCR\b|assay|microbio|biolog",
 "Materials": r"material|polymer|biomaterial|tissue",
 "Biomedical": r"biomedical|bioengineer|clinical engineer|medical device",
 "Quality / Regulatory": r"quality|regulatory|compliance|validation",
}

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
    for q in ["biomedical engineer student", "software engineer student health", "mechanical engineer student medical", "chemical engineer student", "neuroscience student", "immunology student", "bioengineer pathways"]:
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
            [("category", "Science and Engineering"), ("category", "Software Engineering"), ("category", "Data Science"), ("category", "Healthcare"), ("level", "Internship"), ("page", p)])
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
    jobs = []
    for f in (adzuna, usajobs, muse, greenhouse):
        got = safe(f); print(f"{f.__name__}: {len(got)} raw results"); jobs += got
    cutoff = (datetime.date.today() - datetime.timedelta(days=MAX_AGE_DAYS)).isoformat()
    seen, final = set(), []
    for j in jobs:
        blob = f'{j["title"]} {j.get("text","")[:1500]}'
        if not (KEEP.search(j["title"]) and TOPIC.search(blob)): continue
        if EXCLUDE.search(j["title"]) or not ENGINEERING.search(j["title"]): continue
        if j.get("posted") and j["posted"] < cutoff: continue
        key = (j["title"].lower().strip(), j["company"].lower().strip(), j["location"].lower().strip())
        if key in seen: continue
        seen.add(key)
        j["disciplines"] = [d for d, rx in DISCIPLINES.items() if re.search(rx, blob, re.I)] or ["Biomedical"]
        j.pop("text", None); final.append(j)
    final.sort(key=lambda j: j.get("posted", ""), reverse=True)
    out = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "count": len(final), "jobs": final}
    os.makedirs("site", exist_ok=True)
    json.dump(out, open("site/internships.json", "w"), indent=1)
    print(f"Wrote {len(final)} internships")

if __name__ == "__main__": main()
