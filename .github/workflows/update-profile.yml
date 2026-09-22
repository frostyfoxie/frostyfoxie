import os
import re
import json
import base64
import datetime
import urllib.request

USERNAME = os.getenv("GH_USERNAME")
TOKEN = os.getenv("GITHUB_TOKEN")
INSTAGRAM_HANDLE = os.getenv("INSTAGRAM_HANDLE", "your_instagram")

if not USERNAME or not TOKEN:
    raise ValueError("Missing GH_USERNAME or GITHUB_TOKEN.")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": "GitHub-Actions-AllTime-Profile-Updater"
}

def graphql_request(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

# 1. Fetch User Profile Data & Account Creation Year
user_url = f"https://api.github.com/users/{USERNAME}"
req_user = urllib.request.Request(user_url, headers=headers)
with urllib.request.urlopen(req_user) as resp:
    user_data = json.loads(resp.read().decode())

full_name = user_data.get("name") or USERNAME
first_name = full_name.split()[0].upper()
avatar_url = user_data.get("avatar_url")
email = user_data.get("email") or f"{USERNAME}@users.noreply.github.com"
created_year = int(user_data.get("created_at", "2020")[:4])
current_year = datetime.datetime.now().year

# 2. Download Avatar and Encode to Base64
req_avatar = urllib.request.Request(avatar_url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req_avatar) as resp:
    avatar_b64 = base64.b64encode(resp.read()).decode("utf-8")
avatar_data_uri = f"data:image/jpeg;base64,{avatar_b64}"

# 3. Fetch ALL Repos (Public + Private) & All Stars
page = 1
total_repos = 0
total_stars = 0

while True:
    # 'user/repos' with affiliation=owner fetches both public & private repos owned by the authenticated token
    repos_url = f"https://api.github.com/user/repos?affiliation=owner&visibility=all&per_page=100&page={page}"
    try:
        req_repos = urllib.request.Request(repos_url, headers=headers)
        with urllib.request.urlopen(req_repos) as resp:
            repos = json.loads(resp.read().decode())
    except Exception:
        # Fallback if token lacks private scope
        repos_url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}"
        req_repos = urllib.request.Request(repos_url, headers=headers)
        with urllib.request.urlopen(req_repos) as resp:
            repos = json.loads(resp.read().decode())

    if not repos:
        break
    total_repos += len(repos)
    total_stars += sum(r.get("stargazers_count", 0) for r in repos)
    page += 1

stars_str = f"{total_stars}+" if total_stars >= 100 else str(total_stars)

# 4. Fetch Every Single Commit Till Date & All-Time Active Days (Public + Private)
total_commits = 0
active_days = 0

for year in range(created_year, current_year + 1):
    from_date = f"{year}-01-01T00:00:00Z"
    to_date = f"{year}-12-31T23:59:59Z"

    gql_query = """
    query($username: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $username) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          restrictedContributionsCount
          contributionCalendar {
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
    try:
        data = graphql_request(gql_query, {"username": USERNAME, "from": from_date, "to": to_date})
        collection = data["data"]["user"]["contributionsCollection"]
        # Public commits + Private commits (restrictedContributionsCount)
        commits_in_year = collection["totalCommitContributions"] + collection.get("restrictedContributionsCount", 0)
        total_commits += commits_in_year

        # Count active days in this year
        for week in collection["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                if day["contributionCount"] > 0:
                    active_days += 1
    except Exception as e:
        print(f"Warning fetching year {year}: {e}")

commits_str = f"{total_commits // 1000}.{(total_commits % 1000) // 100}k+" if total_commits >= 1000 else str(total_commits)
active_days_str = f"{active_days} D"

# 5. Helper to load and Base64 encode icons (with fallbacks)
def load_icon_as_base64(icon_filename):
    icon_path = os.path.join("icons", icon_filename)
    if not os.path.exists(icon_path):
        # Default inline Instagram SVG if not uploaded yet
        if "instagram" in icon_filename:
            svg_data = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#E4405F" d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>'
            return f"data:image/svg+xml;base64,{base64.b64encode(svg_data.encode()).decode()}"
        return ""
    with open(icon_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(icon_filename)[1].lower().replace(".", "")
    mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
    return f"data:{mime};base64,{encoded}"

# 6. Read template and inject values
with open("template.svg", "r", encoding="utf-8") as f:
    template = f.read()

replacements = {
    "{{NAME}}": first_name,
    "{{USERNAME}}": USERNAME,
    "{{AVATAR_DATA_URI}}": avatar_data_uri,
    "{{COMMITS}}": commits_str,
    "{{REPOS}}": str(total_repos),
    "{{ACTIVE_DAYS}}": active_days_str,
    "{{STARS}}": stars_str,
    "{{INSTAGRAM_HANDLE}}": INSTAGRAM_HANDLE,
    "{{EMAIL}}": email,
    "{{ICON_VERCEL}}": load_icon_as_base64("vercel.svg"),
    "{{ICON_SUPABASE}}": load_icon_as_base64("supabase.svg"),
    "{{ICON_HUGGINGFACE}}": load_icon_as_base64("huggingface.svg"),
    "{{ICON_GITHUB}}": load_icon_as_base64("github.svg"),
    "{{ICON_CLAUDE}}": load_icon_as_base64("claude.svg"),
    "{{ICON_GEMINI}}": load_icon_as_base64("gemini.svg"),
    "{{ICON_PYTHON}}": load_icon_as_base64("python.svg"),
    "{{ICON_TYPESCRIPT}}": load_icon_as_base64("typescript.svg"),
    "{{ICON_FIREBASE}}": load_icon_as_base64("firebase.svg"),
    "{{ICON_INSTAGRAM}}": load_icon_as_base64("instagram.svg"),
    "{{ICON_EMAIL}}": load_icon_as_base64("email.svg"),
    "{{ICON_GITHUB_RED}}": load_icon_as_base64("github.svg"),
}

for key, val in replacements.items():
    template = template.replace(key, str(val))

with open("profile.svg", "w", encoding="utf-8") as f:
    f.write(template)

print(f"Successfully generated profile.svg with all-time stats ({commits_str} commits across all years)!")
