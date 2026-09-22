import os
import json
import base64
import datetime
import textwrap
import html
import urllib.request

USERNAME = os.getenv("GH_USERNAME")
TOKEN = os.getenv("GITHUB_TOKEN")

if not USERNAME or not TOKEN:
    raise ValueError("Missing GH_USERNAME or GITHUB_TOKEN environment variables.")

# 1. Load config.json
config_file = "config.json"
if os.path.exists(config_file):
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
else:
    config = {}

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": "GitHub-Actions-Config-Profile-Updater"
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

def load_icon_as_base64(icon_filename):
    icon_path = os.path.join("icons", icon_filename)
    if not os.path.exists(icon_path):
        if "instagram" in icon_filename:
            svg_data = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#E4405F" d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>'
            return f"data:image/svg+xml;base64,{base64.b64encode(svg_data.encode()).decode()}"
        return ""
    with open(icon_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(icon_filename)[1].lower().replace(".", "")
    mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
    return f"data:{mime};base64,{encoded}"

# 2. Fetch User Profile & Avatar
user_url = f"https://api.github.com/users/{USERNAME}"
req_user = urllib.request.Request(user_url, headers=headers)
with urllib.request.urlopen(req_user) as resp:
    user_data = json.loads(resp.read().decode())

full_name = user_data.get("name") or USERNAME
first_name = full_name.split()[0].upper()
avatar_url = user_data.get("avatar_url")
created_year = int(user_data.get("created_at", "2020")[:4])
current_year = datetime.datetime.now().year

req_avatar = urllib.request.Request(avatar_url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req_avatar) as resp:
    avatar_b64 = base64.b64encode(resp.read()).decode("utf-8")
avatar_data_uri = f"data:image/jpeg;base64,{avatar_b64}"

# 3. Fetch All Repos & Stars (Public + Private)
page = 1
total_repos = 0
total_stars = 0
while True:
    try:
        repos_url = f"https://api.github.com/user/repos?affiliation=owner&visibility=all&per_page=100&page={page}"
        req_repos = urllib.request.Request(repos_url, headers=headers)
        with urllib.request.urlopen(req_repos) as resp:
            repos = json.loads(resp.read().decode())
    except Exception:
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

# 4. Fetch Commits & Active Days Till Date (Public + Private)
total_commits = 0
active_days = 0
for year in range(created_year, current_year + 1):
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
        data = graphql_request(gql_query, {"username": USERNAME, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"})
        col = data["data"]["user"]["contributionsCollection"]
        total_commits += col["totalCommitContributions"] + col.get("restrictedContributionsCount", 0)
        for week in col["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                if day["contributionCount"] > 0:
                    active_days += 1
    except Exception:
        pass

commits_str = f"{total_commits // 1000}.{(total_commits % 1000) // 100}k+" if total_commits >= 1000 else str(total_commits)
active_days_str = f"{active_days} D"

# 5. Build Dynamic Education Items
edu_list = config.get("education", [])
edu_svg = []
if edu_list:
    line_y2 = 30 + (len(edu_list) - 1) * 36
    edu_svg.append(f'<line x1="6" y1="30" x2="6" y2="{line_y2}" stroke="#cbd5e1" stroke-width="1.5"/>')
    for i, item in enumerate(edu_list):
        cy = 30 + (i * 36)
        year = html.escape(str(item.get("year", "")))
        title = html.escape(str(item.get("title", "")))
        inst = html.escape(str(item.get("institution", "")))
        edu_svg.append(f'''
        <circle cx="6" cy="{cy}" r="3.5" fill="#3b82f6"/>
        <text x="20" y="{cy + 4}" class="body-font text-slate-900" font-size="11" font-weight="900">{year}</text>
        <text x="60" y="{cy + 4}" class="body-font text-slate-900" font-size="11" font-weight="800">{title}</text>
        <text x="60" y="{cy + 16}" class="body-font text-slate-500" font-size="10" font-weight="500">{inst}</text>
        ''')
education_markup = "\n".join(edu_svg)

# 6. Build Dynamic Skills Items (Pill Badges)
skills_list = config.get("skills", [])
skills_svg = []
positions = [
    (0, 0, 154), (162, 0, 140),
    (0, 34, 124), (132, 34, 144),
    (0, 68, 146), (154, 68, 118)
]
for i, skill in enumerate(skills_list[:6]):
    x, y, w = positions[i]
    skill_text = html.escape(skill)
    mid_x = x + (w // 2)
    skills_svg.append(f'''
    <rect x="{x}" y="{y}" width="{w}" height="26" rx="13" class="pill-bg"/>
    <text x="{mid_x}" y="{y + 17}" text-anchor="middle" class="pill-text">{skill_text}</text>
    ''')
skills_markup = "\n".join(skills_svg)

# 7. Build Dynamic Tech Stack Keycaps
tech_list = config.get("tech_stack", [])
tech_svg = []
for i, tech in enumerate(tech_list[:9]):
    row = 0 if i < 7 else 1
    col = i if row == 0 else (i - 7)
    x = col * 48
    y = row * 48
    icon_b64 = load_icon_as_base64(f"{tech}.svg")
    tech_svg.append(f'''
    <g transform="translate({x}, {y})">
      <rect width="40" height="40" fill="#ffffff" stroke="#e2e8f0" stroke-width="1" class="keycap-bg"/>
      <image href="{icon_b64}" x="8" y="8" width="24" height="24" preserveAspectRatio="xMidYMid meet"/>
    </g>
    ''')
tech_markup = "\n".join(tech_svg)

# 8. Format "Behind the Code" Paragraphs
subheading = html.escape(config.get("behind_the_code", {}).get("subheading", "FULL-STACK ENGINEER & SOFTWARE ARCHITECT"))
desc_paragraphs = config.get("behind_the_code", {}).get("description", [])
tspans = []
first_line = True
for para in desc_paragraphs:
    lines = textwrap.wrap(para, width=78)
    for i, line in enumerate(lines):
        dy = "0" if first_line else ("30" if i == 0 else "22")
        first_line = False
        tspans.append(f'<tspan x="0" dy="{dy}">{html.escape(line)}</tspan>')
description_markup = "\n".join(tspans)

# 9. Contact Info from config.json
instagram_handle = config.get("contact", {}).get("instagram", os.getenv("INSTAGRAM_HANDLE", "oneinagoogolplex._"))
email_address = config.get("contact", {}).get("email", user_data.get("email", "navneetkrgupta01@gmail.com"))

# 10. Load template and replace placeholders
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
    "{{INSTAGRAM_HANDLE}}": instagram_handle,
    "{{EMAIL}}": email_address,
    "{{BEHIND_THE_CODE_SUBHEADING}}": subheading,
    "{{BEHIND_THE_CODE_DESCRIPTION}}": description_markup,
    "{{EDUCATION_ITEMS}}": education_markup,
    "{{SKILLS_ITEMS}}": skills_markup,
    "{{TECH_STACK_ITEMS}}": tech_markup,
    "{{ICON_GITHUB}}": load_icon_as_base64("github.svg"),
    "{{ICON_GITHUB_RED}}": load_icon_as_base64("github.svg"),
    "{{ICON_INSTAGRAM}}": load_icon_as_base64("instagram.svg"),
    "{{ICON_EMAIL}}": load_icon_as_base64("email.svg")
}

for key, val in replacements.items():
    template = template.replace(key, str(val))

with open("profile.svg", "w", encoding="utf-8") as f:
    f.write(template)

print("Successfully generated profile.svg from config.json!")
