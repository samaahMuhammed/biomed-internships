#!/usr/bin/env python3
"""Tailor your resume (and draft a cover letter) for internships in site/internships.json.
Setup:  pip install anthropic requests beautifulsoup4
        export ANTHROPIC_API_KEY=...        (console.anthropic.com)
Usage:  python tailor.py resume.md --pick          # choose from the list
        python tailor.py resume.md --index 3       # job #3 in the list
        python tailor.py resume.md --top 5 --major Mechanical   # newest 5 matches
Output: applications/<company>-<title>/resume.md + cover_letter.md + apply_link.txt
"""
import sys, os, re, json, argparse
import anthropic, requests
from bs4 import BeautifulSoup

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
RULES = """You tailor resumes. Hard rules:
- Use ONLY facts in the candidate's resume. Never invent jobs, skills, degrees, metrics or dates.
- Reorder, reword and emphasize existing content to match the job's keywords and requirements.
- Keep it to one page, same section structure, plain markdown.
- After the resume, output a line '---COVER---' then a 3-paragraph cover letter (no fabricated claims).
- After that, a line '---GAPS---' then a short bullet list of job requirements the resume does not show."""

def job_text(url):
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        t = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
        return t[:8000]
    except Exception as e:
        return ""

def tailor(resume, job):
    desc = job_text(job["url"]) or job["title"]
    msg = f"RESUME:\n{resume}\n\nJOB: {job['title']} at {job['company']} ({job['location']})\nDESCRIPTION:\n{desc}"
    out = anthropic.Anthropic().messages.create(model=MODEL, max_tokens=3000, system=RULES,
        messages=[{"role": "user", "content": msg}]).content[0].text
    res, _, rest = out.partition("---COVER---")
    cover, _, gaps = rest.partition("---GAPS---")
    d = "applications/" + re.sub(r"[^a-z0-9]+", "-", f"{job['company']}-{job['title']}".lower())[:70]
    os.makedirs(d, exist_ok=True)
    open(f"{d}/resume.md", "w").write(res.strip())
    open(f"{d}/cover_letter.md", "w").write(cover.strip())
    open(f"{d}/apply_link.txt", "w").write(f"{job['url']}\n\nGaps to review:\n{gaps.strip()}\n")
    print("saved", d)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("resume")
    ap.add_argument("--pick", action="store_true"); ap.add_argument("--index", type=int)
    ap.add_argument("--top", type=int); ap.add_argument("--major")
    a = ap.parse_args()
    resume = open(a.resume).read()
    jobs = json.load(open("site/internships.json"))["jobs"]
    if a.major: jobs = [j for j in jobs if a.major in j.get("disciplines", [])]
    if a.pick:
        for i, j in enumerate(jobs[:60]): print(i, j["title"], "|", j["company"], "|", j["location"])
        a.index = int(input("Job #: "))
    sel = [jobs[a.index]] if a.index is not None else jobs[: a.top or 1]
    for j in sel: tailor(resume, j)

if __name__ == "__main__": main()
