# Biomedical Engineering Internships (auto-updating)
1. Create a GitHub repo, push this folder.
2. Settings > Pages > Source: **GitHub Actions**.
3. Settings > Secrets > add (all free): ADZUNA_APP_ID, ADZUNA_APP_KEY (developer.adzuna.com),
   USAJOBS_KEY, USAJOBS_EMAIL (developer.usajobs.gov). Optional variable GREENHOUSE_BOARDS (e.g. `companyA,companyB`).
4. Actions > Daily update > Run workflow. It then reruns every day at 11:00 UTC.
Local test: `python fetch_internships.py && cd site && python -m http.server`
