import os
import re
import json
import base64
import urllib.request

USERNAME = os.getenv("GH_USERNAME")
TOKEN = os.getenv("GITHUB_TOKEN")

if not USERNAME or not TOKEN:
    raise ValueError("Missing GH_USERNAME or GITHUB_TOKEN environment variables.")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": "GitHub-Actions-Profile-Updater"
}

# 1. Fetch User Profile Data from REST API
user_url = f"https://api.github.com/users/{USERNAME}"
req = urllib.request.Request(user_url, headers=headers)
with urllib.request.urlopen(req) as resp:
    user_data = json.loads(resp.read().decode())

full_name = user_data.get("name") or USERNAME
first_name = full_name.split()[0].upper()
location = user_data.get("location") or "San Francisco, CA"
repos_count = str(user_data.get("public_repos", 0))
avatar_url = user_data.get("avatar_url")
email = user_data.get("email") or f"{USERNAME}@users.noreply.github.com"

# 2. Download Avatar and encode to Base64 (prevents GitHub Camo proxy issues)
req_avatar = urllib.request.Request(avatar_url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req_avatar) as resp:
    avatar_b64 = base64.b64encode(resp.read()).decode("utf-8")
avatar_data_uri = f"data:image/jpeg;base64,{avatar_b64}"

# 3. Fetch Stars across all public repos
repos_url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100"
req_repos = urllib.request.Request(repos_url, headers=headers)
with urllib.request.urlopen(req_repos) as resp:
    repos = json.loads(resp.read().decode())
total_stars = sum(r.get("stargazers_count", 0) for r in repos)
stars_str = f"{total_stars}+" if total_stars >= 100 else str(total_stars)

# 4. Fetch Commits & Active Days via GraphQL API
graphql_query = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
          }
        }
      }
    }
  }
}
"""
req_gql = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": graphql_query, "variables": {"username": USERNAME}}).encode("utf-8"),
    headers=headers
)
with urllib.request.urlopen(req_gql) as resp:
    gql_data = json.loads(resp.read().decode())

collection = gql_data["data"]["user"]["contributionsCollection"]
total_commits = collection["totalCommitContributions"]
commits_str = f"{total_commits // 1000}.{ (total_commits % 1000) // 100 }k+" if total_commits >= 1000 else str(total_commits)

# Calculate active days (days with at least 1 contribution)
active_days = 0
for week in collection["contributionCalendar"]["weeks"]:
    for day in week["contributionDays"]:
        if day["contributionCount"] > 0:
            active_days += 1
active_days_str = f"{active_days} D"

# 5. Replace placeholders in template.svg
with open("template.svg", "r", encoding="utf-8") as f:
    template = f.read()

replacements = {
    "{{NAME}}": first_name,
    "{{USERNAME}}": USERNAME,
    "{{AVATAR_DATA_URI}}": avatar_data_uri,
    "{{COMMITS}}": commits_str,
    "{{REPOS}}": repos_count,
    "{{ACTIVE_DAYS}}": active_days_str,
    "{{STARS}}": stars_str,
    "{{LOCATION}}": location,
    "{{EMAIL}}": email,
}

for key, val in replacements.items():
    template = template.replace(key, str(val))

# Save output
with open("profile.svg", "w", encoding="utf-8") as f:
    f.write(template)

print(f"Successfully generated profile.svg for {USERNAME}!")
