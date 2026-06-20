"""
Indeed job search via Claude Code CLI with Indeed MCP connector.
Outputs indeed_jobs.json to be merged by job_search.py.
Runs as a separate step before job_search.py in GitHub Actions.
"""

import json
import os
import subprocess
import sys

SEARCH_QUERIES = [
    ("new grad AI engineer entry level", "United States"),
    ("entry level data scientist new graduate", "United States"),
    ("junior data analyst entry level", "United States"),
    ("entry level machine learning engineer", "United States"),
]

PROMPT_TEMPLATE = """Use the mcp__claude_ai_Indeed__search_jobs tool to search Indeed for jobs.

Search for: "{query}"
Location: "{location}"
Country: US
Job type: fulltime

For each job returned, extract and output ONLY a JSON array with this exact structure (no markdown, no explanation):
[
  {{
    "title": "job title",
    "company": "company name",
    "location": "city, state",
    "remote": false,
    "source": "Indeed",
    "posted": "YYYY-MM-DD or N/A",
    "url": "apply url",
    "salary": "salary range or Not listed",
    "sponsorship": "unknown"
  }}
]

Output raw JSON array only."""


def search_indeed(query: str, location: str) -> list[dict]:
    prompt = PROMPT_TEMPLATE.format(query=query, location=location)
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print(f"  Claude error: {result.stderr[:200]}")
        return []
    output = result.stdout.strip()
    # Strip markdown code fences if present
    if output.startswith("```"):
        lines = output.split("\n")
        output = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        jobs = json.loads(output)
        if isinstance(jobs, list):
            return jobs
    except json.JSONDecodeError:
        print(f"  Could not parse JSON from Claude output")
    return []


def main():
    all_jobs = []
    for query, location in SEARCH_QUERIES:
        print(f"Indeed search: {query}...")
        jobs = search_indeed(query, location)
        print(f"  Got {len(jobs)} jobs")
        all_jobs.extend(jobs)

    # Deduplicate by (title, company)
    seen = set()
    unique = []
    for j in all_jobs:
        key = (j.get("title", "").lower(), j.get("company", "").lower())
        if key not in seen:
            seen.add(key)
            unique.append(j)

    print(f"Total unique Indeed jobs: {len(unique)}")
    with open("indeed_jobs.json", "w") as f:
        json.dump(unique, f, indent=2)
    print("Saved to indeed_jobs.json")


if __name__ == "__main__":
    main()
