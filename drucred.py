import csv
import requests
import os
import json
import time
import sys
from collections import Counter

# Constants
STATUS_FIXED = 7
PAGE_LIMIT = 50
API_BASE_URL = "https://www.drupal.org/api-d7"

# Set dynamic cache
def get_issue_cache_dir(project_slug):
    return os.path.join("data", str(project_slug))

def get_cache_ids_path(project_slug):
    cache_dir = get_issue_cache_dir(project_slug)
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"cache_{project_slug}.json")

HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "User-Agent": "drucred/1.0 (+https://kanopi.com; jim@kanopi.com)"
}

def fetch_page(url, retries=5):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                wait = (attempt + 1) * 5
                print(f"Rate limited (429). Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"Error {resp.status_code} fetching URL: {url}")
                return None
        except Exception as e:
            print(f"Request error: {e}")
            time.sleep(3)
    return None

def get_project_metadata(project_nid):
    url = f"{API_BASE_URL}/node/{project_nid}.json"
    data = fetch_page(url)
    if data:
        title = data.get("title", f"Project {project_nid}")
        machine_name = data.get("field_project_machine_name", f"project_{project_nid}")
        return title, machine_name
    return f"Project {project_nid}", f"project_{project_nid}"

def fetch_issue_ids(project_nid, project_slug, force_refresh=False):
    cache_ids_path = get_cache_ids_path(project_slug)

    if not force_refresh and os.path.exists(cache_ids_path):
        print(f"Loading cached issue IDs from {cache_ids_path}")
        with open(cache_ids_path, "r") as f:
            return json.load(f)

    print("Fetching issue IDs from Drupal.org...")
    page = 0
    ids = []

    while True:
        url = (
            f"{API_BASE_URL}/node.json?type=project_issue"
            f"&field_project={project_nid}&field_issue_status={STATUS_FIXED}"
            f"&limit={PAGE_LIMIT}&page={page}"
        )
        data = fetch_page(url)
        if not data or not data.get("list"):
            break

        ids.extend([item["nid"] for item in data["list"]])
        print(f"Collected {len(ids)} issue IDs so far...")
        page += 1
        time.sleep(1)

    with open(cache_ids_path, "w") as f:
        json.dump(ids, f, indent=2)

    return ids

def fetch_issue_with_credit(nid, project_slug):
    issue_cache_dir = get_issue_cache_dir(project_slug)
    os.makedirs(issue_cache_dir, exist_ok=True)
    cache_file = os.path.join(issue_cache_dir, f"{nid}.json")

    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)

    url = f"{API_BASE_URL}/node/{nid}.json?drupalorg_extra_credit=1"
    data = fetch_page(url)
    if data:
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
        time.sleep(1)  # throttle
        return data
    return None

def extract_credit(issues):
    individual_counter = Counter()
    organization_counter = Counter()
    org_to_people = {}

    for issue in issues:
        credit_entries = issue.get("field_issue_credit", [])
        if not credit_entries:
            continue

        for entry in credit_entries:
            data = entry.get("data", {})
            user = data.get("username")
            orgs = data.get("field_attribute_contribution_to", [])

            if user:
                individual_counter[user] += 1

            for org in orgs:
                org_name = org.get("title")
                if org_name:
                    organization_counter[org_name] += 1
                    org_to_people.setdefault(org_name, Counter())[user] += 1

    return individual_counter, organization_counter, org_to_people

def render_mermaid_bar_chart(title, data_counter, top_n=10):
    lines = [f"%% {title}", "bar", f"    title {title}"]
    for name, count in data_counter.most_common(top_n):
        lines.append(f'    "{name}": {count}')
    return "\n".join(lines)

def main(project_nid, project_title, project_slug, force_refresh=False, top_n=10):
    print(f"Starting issue credit audit for {project_title}...")

    ids = fetch_issue_ids(project_nid, project_slug, force_refresh=force_refresh)
    print(f"Total fixed issues found: {len(ids)}")

    issues = []
    for i, nid in enumerate(ids):
        issue = fetch_issue_with_credit(nid, project_slug)
        if issue:
            issues.append(issue)
        else:
            print(f"Skipping issue nid {nid} due to fetch error.")
        if i % 10 == 0:
            print(f"Processed {i+1}/{len(ids)} issues...")

    print(f"\n✅ Successfully loaded {len(issues)} issues with credit info")

    individual_credit, org_credit, org_to_people = extract_credit(issues)
    num_with_credit = sum(1 for i in issues if i.get("field_issue_credit"))

    lines = []
    lines.append(f"# {project_title} Contributor Credit Report")
    lines.append(f"- Total fixed issues: {len(issues)}")
    lines.append(f"- Issues with credit data: {num_with_credit}\n")

    lines.append("## 📑 Table of Contents")
    lines.append("- [Top Individual Contributors](#-top-individual-contributors)")
    lines.append("- [Organizations Credited](#-organizations-credited)")
    lines.append("- [All Contributors by Organization](#-all-contributors-by-organization)")
    lines.append("- [All Contributors](#-all-contributors)")
    lines.append("")

    def section(title, counter, top_n):
        lines.append(f"## {title}")
        for name, count in counter.most_common(top_n):
            lines.append(f"- {name}: {count}")
        lines.append("")

    def chart(title, counter, top_n):
        lines.append("```mermaid")
        lines.append(render_mermaid_bar_chart(title, counter, top_n=top_n))
        lines.append("```")
        lines.append("")

    lines.append("## 👤 Top Individual Contributors")
    section("Top Contributors", individual_credit, top_n)
    chart("Top Contributors", individual_credit, top_n)

    lines.append("## 🏢 Organizations Credited")
    section("Top Credited Organizations", org_credit, top_n)
    chart("Top Organization Contributors", org_credit, top_n)

    lines.append("## 🏷️ All Contributors by Organization")
    for org in sorted(org_to_people.keys()):
        people = org_to_people[org].most_common()
        lines.append(f"### {org}")
        for person, count in people:
            lines.append(f"- {person}: {count}")
        lines.append("")

    lines.append("## 🌐 All Contributors")
    for name, count in individual_credit.most_common():
        lines.append(f"- {name}: {count}")
    lines.append("")

    # Write to markdown file
    os.makedirs("output", exist_ok=True)
    with open(f"output/drucred_{project_slug}.md", "w") as f:
        f.write("\n".join(lines))

    with open(f"output/drucred_{project_slug}.csv", "w", newline="") as csvfile:
        fieldnames = ["Username", "Organization", "Count"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        rows = []
        for org, people in org_to_people.items():
            for person, count in people.items():
                rows.append({"Username": person, "Organization": org, "Count": count})

        # Add individuals without orgs
        people_with_orgs = set(p for plist in org_to_people.values() for p in plist)
        for name, count in individual_credit.items():
            if name not in people_with_orgs:
                rows.append({"Username": name, "Organization": "", "Count": count})

        for row in sorted(rows, key=lambda x: x["Count"], reverse=True):
            writer.writerow(row)

    print(f"✅ Report written to output/drucred_{project_slug}.md and output/drucred_{project_slug}.csv")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python drucred.py <project_node_id>")
        sys.exit(1)

    try:
        project_nid = int(sys.argv[1])
    except ValueError:
        print("❌ Invalid project_node_id. Please pass a numeric node ID.")
        sys.exit(1)

    project_title, project_slug = get_project_metadata(project_nid)
    main(project_nid, project_title, project_slug, force_refresh=False, top_n=10)
