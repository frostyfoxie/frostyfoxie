import os
import json
import base64
import datetime
import textwrap
import html
import collections
import urllib.request

USERNAME = os.getenv("GH_USERNAME")
TOKEN = os.getenv("GITHUB_TOKEN")

if not USERNAME or not TOKEN:
    raise ValueError("Missing GH_USERNAME or GITHUB_TOKEN environment variables.")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
ICONS_DIR = os.path.join(REPO_ROOT, "icons")

config_file = os.path.join(REPO_ROOT, "config.json")
if os.path.exists(config_file):
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
else:
    config = {}

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": "GitHub-Actions-Animated-Profile-Updater"
}

def load_icon_as_base64(name_or_filename):
    clean_name = os.path.splitext(name_or_filename)[0].lower().strip()
    if os.path.exists(ICONS_DIR):
        actual_files = os.listdir(ICONS_DIR)
        file_map = {f.lower(): f for f in actual_files}
        for ext in [".svg", ".png", ".webp", ".jpg", ".jpeg"]:
            candidate = f"{clean_name}{ext}"
            if candidate in file_map:
                found_file = file_map[candidate]
                file_path = os.path.join(ICONS_DIR, found_file)
                with open(file_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                mime = "image/svg+xml" if ext == ".svg" else f"image/{ext.replace('.', '')}"
                return f"data:{mime};base64,{encoded}"

    try:
        cdn_url = f"https://cdn.simpleicons.org/{clean_name}"
        req = urllib.request.Request(cdn_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                svg_data = resp.read()
                b64 = base64.b64encode(svg_data).decode("utf-8")
                return f"data:image/svg+xml;base64,{b64}"
    except Exception:
        pass

    if "instagram" in clean_name:
        fallback = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#E4405F" d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>'
        return f"data:image/svg+xml;base64,{base64.b64encode(fallback.encode()).decode()}"
    return ""

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

# 1. Fetch User Data
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

# 2. Fetch Repos & Stars
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

# 3. Fetch All-Time Commits & Contribution Calendar
total_commits = 0
active_days = 0
last_year_weeks = []

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
                weekday
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
        weeks = col["contributionCalendar"]["weeks"]
        for week in weeks:
            for day in week["contributionDays"]:
                if day["contributionCount"] > 0:
                    active_days += 1
        if year == current_year:
            last_year_weeks = weeks
    except Exception:
        pass

commits_str = f"{total_commits // 1000}.{(total_commits % 1000) // 100}k+" if total_commits >= 1000 else str(total_commits)
active_days_str = f"{active_days} D"

# 4. PERFECT SNAKE ARCADE PATHFINDING & GROWING LOGIC
def build_arcade_snake(weeks_data):
    if not weeks_data: return ""
    
    weeks_to_show = weeks_data[-53:] if len(weeks_data) >= 53 else weeks_data
    
    BOX_SIZE = 11.0
    STEP = 14.0
    COLS, ROWS = len(weeks_to_show), 7
    
    colors = {0: "#ebedf0", 1: "#9be9a8", 2: "#40c463", 3: "#30a14e", 4: "#216e39"}
    
    # 1. Group targets exactly by their color level (Eat Level 1 -> 2 -> 3 -> 4)
    level_targets = {1: [], 2: [], 3: [], 4: []}
    grid_matrix = {}
    
    for c, week in enumerate(weeks_to_show):
        for day in week.get("contributionDays", []):
            r = day.get("weekday", 0)
            count = day.get("contributionCount", 0)
            level = 0 if count == 0 else (1 if count <= 2 else (2 if count <= 5 else (3 if count <= 9 else 4)))
            grid_matrix[(c, r)] = colors[level]
            if level > 0:
                level_targets[level].append((c, r))

    # Breadth-First-Search for strictly grid-bound movement
    def bfs_path(start, goal):
        queue = collections.deque([[start]])
        visited = {start}
        while queue:
            path = queue.popleft()
            curr = path[-1]
            if curr == goal: return path
            for dc, dr in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
                nc, nr = curr[0] + dc, curr[1] + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS and (nc, nr) not in visited:
                    visited.add((nc, nr))
                    queue.append(path + [(nc, nr)])
        return [start, goal]

    # 2. Build Path eating lightest to darkest
    circuit_cells = []
    curr = (0, 0)
    food_eat_steps = {}  # { (c, r) : step_number_when_eaten }
    
    ordered_targets = []
    for lvl in [1, 2, 3, 4]:
        targets = level_targets[lvl]
        while targets:
            closest = min(targets, key=lambda t: abs(t[0]-curr[0]) + abs(t[1]-curr[1]))
            ordered_targets.append(closest)
            sub_path = bfs_path(curr, closest)
            circuit_cells.extend(sub_path[:-1])
            curr = closest
            targets.remove(closest)
            food_eat_steps[closest] = len(circuit_cells)
    
    # Loop back to start
    circuit_cells.extend(bfs_path(curr, (0, 0)))
    
    # If 0 commits, do a patrol loop
    if not circuit_cells:
        for c in range(COLS): circuit_cells.append((c, 0))
        for r in range(1, ROWS): circuit_cells.append((COLS-1, r))
        for c in range(COLS-2, -1, -1): circuit_cells.append((c, ROWS-1))
        for r in range(ROWS-2, -1, -1): circuit_cells.append((0, r))

    TOTAL_STEPS = len(circuit_cells)
    DURATION = max(10.0, TOTAL_STEPS * 0.12) # Speed multiplier

    # Convert cells to true SVG coordinates
    path_d_segments = [f"M {circuit_cells[0][0]*STEP + BOX_SIZE/2:.1f} {circuit_cells[0][1]*STEP + BOX_SIZE/2:.1f}"]
    for cell in circuit_cells[1:]:
        path_d_segments.append(f"L {cell[0]*STEP + BOX_SIZE/2:.1f} {cell[1]*STEP + BOX_SIZE/2:.1f}")
    path_d_segments.append("Z")
    full_snake_track = " ".join(path_d_segments)

    # 3. Draw Grid Cells (They clear to gray exactly when head reaches them)
    grid_svg = []
    for c in range(COLS):
        for r in range(ROWS):
            x, y = c * STEP, r * STEP
            base_col = grid_matrix.get((c, r), "#ebedf0")
            
            if (c, r) in food_eat_steps:
                eat_frac = food_eat_steps[(c, r)] / TOTAL_STEPS
                # Values logic: Stays color -> Turns Empty at eat_frac -> Stays Empty
                t1 = max(0.0001, eat_frac)
                t2 = min(0.9998, eat_frac + 0.0001)
                grid_svg.append(f'''
                <rect x="{x:.1f}" y="{y:.1f}" width="{BOX_SIZE}" height="{BOX_SIZE}" rx="2.5" fill="#ebedf0">
                  <animate attributeName="fill" values="{base_col};{base_col};#ebedf0;#ebedf0;{base_col}" 
                           keyTimes="0;{t1:.4f};{t2:.4f};0.9999;1" dur="{DURATION:.1f}s" repeatCount="indefinite"/>
                </rect>
                ''')
            else:
                grid_svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{BOX_SIZE}" height="{BOX_SIZE}" rx="2.5" fill="{base_col}"/>')

    # 4. Generate Snake Body (Head leads at t=0, Body tails with delays, New Tail parts spawn on eat)
    dt = DURATION / TOTAL_STEPS
    snake_parts_svg = []

    # New segments that spawn out of thin air when a commit is eaten
    for food_idx, target in enumerate(ordered_targets):
        seg_num = 3 + food_idx
        eat_frac = food_eat_steps[target] / TOTAL_STEPS
        t1, t2 = max(0.0001, eat_frac), min(0.9998, eat_frac + 0.0001)
        # Alternate purple tones for a cool segmented look
        grow_color = "#d8b4fe" if food_idx % 2 == 0 else "#c084fc"
        
        snake_parts_svg.append(f'''
        <g>
          <animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;{t1:.4f};{t2:.4f};0.9999;1" dur="{DURATION:.1f}s" repeatCount="indefinite"/>
          <rect x="-4.5" y="-4.5" width="9" height="9" rx="2.5" fill="{grow_color}">
            <animateMotion path="{full_snake_track}" begin="{seg_num * 0.12}s" dur="{DURATION:.1f}s" repeatCount="indefinite" calcMode="linear"/>
          </rect>
        </g>
        ''')

    # Initial snake (Head + 2 Body parts)
    snake_parts_svg.append(f'''
    <rect x="-4.5" y="-4.5" width="9" height="9" rx="2.5" fill="#a855f7">
      <animateMotion path="{full_snake_track}" begin="0.24s" dur="{DURATION:.1f}s" repeatCount="indefinite" calcMode="linear"/>
    </rect>
    <rect x="-5" y="-5" width="10" height="10" rx="3" fill="#9333ea">
      <animateMotion path="{full_snake_track}" begin="0.12s" dur="{DURATION:.1f}s" repeatCount="indefinite" calcMode="linear"/>
    </rect>
    <!-- Dark Purple Forward-facing Head -->
    <rect x="-5.5" y="-5.5" width="11" height="11" rx="3.5" fill="#6b21a8">
      <animateMotion path="{full_snake_track}" begin="0s" dur="{DURATION:.1f}s" repeatCount="indefinite" calcMode="linear"/>
    </rect>
    ''')

    return f'''
    <g id="contribGrid">
      {"".join(grid_svg)}
      <path id="snakeTrack" d="{full_snake_track}" fill="none" stroke="transparent"/>
      {"".join(snake_parts_svg)}
    </g>
    '''

contribution_snake_markup = build_arcade_snake(last_year_weeks)

# 5. Dynamic Education
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

# 6. Dynamic Skills
skills_list = config.get("skills", [])
skills_svg = []
positions = [
    (0, 0, 154), (162, 0, 140),
    (0, 34, 124), (132, 34, 144),
    (0, 68, 146), (154, 68, 118)
]
for i, skill in enumerate(skills_list[:6]):
    x, y, w = positions[i]
    mid_x = x + (w // 2)
    skills_svg.append(f'''
    <rect x="{x}" y="{y}" width="{w}" height="26" rx="13" class="pill-bg"/>
    <text x="{mid_x}" y="{y + 17}" text-anchor="middle" class="pill-text">{html.escape(skill)}</text>
    ''')
skills_markup = "\n".join(skills_svg)

# 7. Dynamic Tech Stack
tech_list = config.get("tech_stack", [])
tech_svg = []
for i, tech in enumerate(tech_list[:14]):
    row = i // 7
    col = i % 7
    x = col * 48
    y = row * 48
    icon_b64 = load_icon_as_base64(tech)
    tech_svg.append(f'''
    <g transform="translate({x}, {y})">
      <rect width="40" height="40" fill="#ffffff" stroke="#e2e8f0" stroke-width="1" class="keycap-bg"/>
      <image href="{icon_b64}" x="8" y="8" width="24" height="24" preserveAspectRatio="xMidYMid meet"/>
    </g>
    ''')
tech_markup = "\n".join(tech_svg)

# 8. Behind the Code Text
subheading = html.escape(config.get("behind_the_code", {}).get("subheading", "FULL-STACK ENGINEER & SOFTWARE ARCHITECT"))
desc_paragraphs = config.get("behind_the_code", {}).get("description", [])
tspans = []
first_line = True
for para in desc_paragraphs:
    for i, line in enumerate(textwrap.wrap(para, width=78)):
        dy = "0" if first_line else ("30" if i == 0 else "22")
        first_line = False
        tspans.append(f'<tspan x="0" dy="{dy}">{html.escape(line)}</tspan>')
description_markup = "\n".join(tspans)

# 9. Contact Info
instagram_handle = config.get("contact", {}).get("instagram", "oneinagoogolplex._")
email_address = config.get("contact", {}).get("email", user_data.get("email", "navneetkrgupta01@gmail.com"))

icon_github = load_icon_as_base64("github")
icon_instagram = load_icon_as_base64("instagram")
icon_email = load_icon_as_base64("email")

# 10. Replace Placeholders in template.svg
template_path = os.path.join(REPO_ROOT, "template.svg")
with open(template_path, "r", encoding="utf-8") as f:
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
    "{{CONTRIBUTION_SNAKE_SECTION}}": contribution_snake_markup,
    "{{ICON_GITHUB}}": icon_github,
    "{{ICON_GITHUB_RED}}": icon_github,
    "{{ICON_INSTAGRAM}}": icon_instagram,
    "{{ICON_EMAIL}}": icon_email
}

for key, val in replacements.items():
    template = template.replace(key, str(val))

output_path = os.path.join(REPO_ROOT, "profile.svg")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(template)

print(f"🎉 Generated perfect arcade eating snake animation at {output_path}!")
