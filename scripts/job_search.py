"""
Daily job search: New Grad AI Engineer / Data Scientist / Data Analyst roles
Sources: Indeed, LinkedIn, JobRight.ai (via JSearch API on RapidAPI)
Sends digest email via Gmail SMTP
"""

import os
import smtplib
import requests
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

RAPIDAPI_KEY = os.environ["RAPIDAPI_KEY"].strip()
EMAIL_TO = os.environ["EMAIL_TO"].strip()
EMAIL_FROM = os.environ["EMAIL_FROM"].strip()
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"].strip()
LOCATION = os.environ.get("JOB_LOCATION", "United States").strip()

SEARCH_QUERIES = [
    "new grad AI engineer entry level",
    "entry level data scientist new graduate",
    "junior data analyst new grad",
]

JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
}


def search_jobs(query: str, location: str) -> list[dict]:
    params = {
        "query": f"{query} in {location}",
        "page": "1",
        "num_pages": "2",
        "date_posted": "today",
        "employment_types": "FULLTIME",
    }
    try:
        resp = requests.get(JSEARCH_URL, headers=JSEARCH_HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
    except Exception as e:
        print(f"Error searching '{query}': {e}")
        return []


def format_job(job: dict) -> dict:
    return {
        "title": job.get("job_title", "N/A"),
        "company": job.get("employer_name", "N/A"),
        "location": (job.get("job_city") or "") + (", " + (job.get("job_state") or "") if job.get("job_state") else ""),
        "remote": job.get("job_is_remote", False),
        "source": job.get("job_publisher", "N/A"),
        "posted": job.get("job_posted_at_datetime_utc", "")[:10] if job.get("job_posted_at_datetime_utc") else "N/A",
        "url": job.get("job_apply_link", "#"),
        "salary": _format_salary(job),
    }


def _format_salary(job: dict) -> str:
    min_s = job.get("job_min_salary")
    max_s = job.get("job_max_salary")
    period = job.get("job_salary_period", "")
    if min_s and max_s:
        return f"${int(min_s):,} - ${int(max_s):,} {period}"
    if min_s:
        return f"${int(min_s):,}+ {period}"
    return "Not listed"


def deduplicate(jobs: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for job in jobs:
        key = (job["title"].lower(), job["company"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def build_email_html(jobs: list[dict]) -> str:
    today = date.today().strftime("%B %d, %Y")
    rows = ""
    for j in jobs:
        remote_badge = '<span style="color:#22c55e;font-weight:bold;">[REMOTE]</span> ' if j["remote"] else ""
        loc = "Remote" if j["remote"] else (j["location"] or "N/A")
        rows += f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">
            <a href="{j['url']}" style="font-weight:bold;color:#4f46e5;text-decoration:none;">{remote_badge}{j['title']}</a><br>
            <span style="color:#374151;">{j['company']}</span> &nbsp;|&nbsp;
            <span style="color:#6b7280;">{loc}</span> &nbsp;|&nbsp;
            <span style="color:#6b7280;">💰 {j['salary']}</span><br>
            <span style="font-size:12px;color:#9ca3af;">via {j['source']} &nbsp;·&nbsp; Posted: {j['posted']}</span>
          </td>
        </tr>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;padding:20px;">
      <h2 style="color:#4f46e5;">🎯 Daily Job Digest — {today}</h2>
      <p style="color:#6b7280;">New Grad roles: AI Engineer · Data Scientist · Data Analyst<br>
      Location: <strong>{LOCATION}</strong> &nbsp;·&nbsp; <strong>{len(jobs)} jobs found</strong></p>
      <table style="width:100%;border-collapse:collapse;">{rows}</table>
      <p style="color:#9ca3af;font-size:12px;margin-top:20px;">
        Sources: Indeed · LinkedIn · Glassdoor · JobRight.ai (via JSearch API)<br>
        Automated by Claude Code + GitHub Actions
      </p>
    </body></html>"""


def send_email(subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, GMAIL_APP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    print(f"Email sent to {EMAIL_TO}")


def main():
    print(f"Searching jobs for location: {LOCATION}")
    all_jobs = []

    for query in SEARCH_QUERIES:
        print(f"Searching: {query}...")
        results = search_jobs(query, LOCATION)
        formatted = [format_job(j) for j in results]
        all_jobs.extend(formatted)
        print(f"  Found {len(formatted)} results")

    unique_jobs = deduplicate(all_jobs)
    print(f"Total unique jobs: {len(unique_jobs)}")

    if not unique_jobs:
        print("No jobs found today — skipping email.")
        return

    today = date.today().strftime("%b %d")
    subject = f"[Job Digest {today}] {len(unique_jobs)} New Grad AI/DS/DA Roles"
    html = build_email_html(unique_jobs)
    send_email(subject, html)


if __name__ == "__main__":
    main()
