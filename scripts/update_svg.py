import os
import json
import base64
import datetime
import textwrap
import html
import collections
import urllib.request
import random

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

# 1. User Info & Avatar
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
    avatar_data_uri = f"data:image/jpeg;base64,{base64.b64encode(resp.read()).decode('utf-8')}"

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
    if not repos: break
    total_repos += len(repos)
    total_stars += sum(r.get("stargazers_count", 0) for r in repos)
    page += 1

stars_str = f"{total_stars}+" if total_stars >= 100 else str(total_stars)

# 3. All-Time Commits & Exact 365-Day Grid
total_commits = 0
active_days = 0

for year in range(created_year, current_year + 1):
    gql_query = """
    query($username: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $username) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          restrictedContributionsCount
        }
      }
    }
    """
    try:
        data = graphql_request(gql_query, {"username": USERNAME, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"})
        col = data["data"]["user"]["contributionsCollection"]
        total_commits += col["totalCommitContributions"] + col.get("restrictedContributionsCount", 0)
    except Exception:
        pass

commits_str = f"{total_commits // 1000}.{(total_commits % 1000) // 100}k+" if total_commits >= 1000 else str(total_commits)

gql_grid = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            contributionCount
            contributionLevel
            weekday
          }
        }
      }
    }
  }
}
"""
grid_data = graphql_request(gql_grid, {"username": USERNAME})
recent_weeks = grid_data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

for week in recent_weeks:
    for day in week["contributionDays"]:
        if day["contributionCount"] > 0:
            active_days += 1
active_days_str = f"{active_days} D"

# 4. STRICT PLATANE ARCADE SNAKE (Exact Grid Constraints, 4-Block Length)
def build_arcade_snake(weeks_data):
    if not weeks_data:
        return ""
    
    COLS = 53
    ROWS = 7
    BOX_SIZE = 11.0
    STEP = 14.0
    SNAKE_LEN = 4
    
    colors = {
        "NONE": "#ebedf0",
        "FIRST_QUARTILE": "#9be9a8",
        "SECOND_QUARTILE": "#40c463",
        "THIRD_QUARTILE": "#30a14e",
        "FOURTH_QUARTILE": "#216e39"
    }
    level_map = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

    grid_matrix = {}
    targets = {1: [], 2: [], 3: [], 4: []}
    
    for c, week in enumerate(weeks_data[-COLS:]):
        for day in week.get("contributionDays", []):
            r = day.get("weekday", 0)
            lvl_str = day.get("contributionLevel", "NONE")
            lvl = level_map[lvl_str]
            grid_matrix[(c, r)] = lvl_str
            if lvl > 0:
                targets[lvl].append((c, r))

    def get_path(start, goal, snake_body, current_level, all_targets):
        def bfs(obstacles):
            queue = collections.deque([[start]])
            visited = {start}
            while queue:
                path = queue.popleft()
                curr = path[-1]
                if curr == goal: return path
                for dx, dy in [(1,0), (0,1), (-1,0), (0,-1)]:
                    nx, ny = curr[0] + dx, curr[1] + dy
                    # STRICTLY STAY INSIDE THE GRID (No exiting borders)
                    if 0 <= nx < COLS and 0 <= ny < ROWS:
                        if (nx, ny) not in visited and (nx, ny) not in obstacles:
                            visited.add((nx, ny))
                            queue.append(path + [(nx, ny)])
            return None

        # The body is a solid wall (except the last tail piece which moves away)
        body_obs = set(snake_body[:-1])
        
        # Pass 1: Avoid body AND un-eaten darker blocks
        higher_obs = set()
        for lvl in range(current_level + 1, 5):
            higher_obs.update(all_targets[lvl])
        
        p = bfs(body_obs | higher_obs)
        if p: return p
        
        # Pass 2: Ignore higher blocks if trapped, but avoid body
        p = bfs(body_obs)
        if p: return p
        
        # Pass 3: Ghost through everything if truly trapped
        p = bfs(set())
        if p: return p
        
        return [start, goal]

    # Snake starts curled at top left (0,0)
    start_pos = (0, 0)
    snake = [start_pos for _ in range(SNAKE_LEN)]
    simulation_moves = [start_pos]
    eat_ticks = {}
    tick = 0

    # Hunt Levels 1 -> 2 -> 3 -> 4
    for current_level in [1, 2, 3, 4]:
        while targets[current_level]:
            head = snake[0]
            closest_target = min(targets[current_level], key=lambda t: abs(t[0]-head[0]) + abs(t[1]-head[1]))
            path = get_path(head, closest_target, snake, current_level, targets)

            for step in path[1:]:
                tick += 1
                simulation_moves.append(step)
                snake.insert(0, step)
                snake.pop() # Always keep length = 4
                if step == closest_target:
                    eat_ticks[step] = tick
                    targets[current_level].remove(step)

    # Roam to fill animation duration (~300 ticks)
    min_ticks = 300
    corners = [(0,0), (COLS-1,0), (COLS-1,ROWS-1), (0,ROWS-1)]
    while tick < min_ticks:
        # Don't pick current position as goal
        valid_corners = [c for c in corners if c != snake[0]]
        goal = random.choice(valid_corners)
        path = get_path(snake[0], goal, snake, 5, targets)
        for step in path[1:]:
            tick += 1
            simulation_moves.append(step)
            snake.insert(0, step)
            snake.pop()
            if tick >= min_ticks: break

    TOTAL_TICKS = len(simulation_moves)
    DURATION = max(24.0, TOTAL_TICKS * 0.1)

    # Output Background Grid
    grid_svg = []
    for c in range(COLS):
        for r in range(ROWS):
            x = c * STEP
            y = r * STEP
            lvl_str = grid_matrix.get((c, r), "NONE")
            base_col = colors[lvl_str]
            
            if (c, r) in eat_ticks:
                eat_frac = eat_ticks[(c, r)] / TOTAL_TICKS
                grid_svg.append(f'''
                <rect x="{x:.1f}" y="{y:.1f}" width="{BOX_SIZE}" height="{BOX_SIZE}" rx="2.5" fill="{base_col}">
                  <animate attributeName="fill" values="{base_col};{base_col};#ebedf0;#ebedf0;{base_col}"
                           keyTimes="0;{eat_frac:.4f};{eat_frac + 0.001:.4f};0.99;1" dur="{DURATION:.1f}s" repeatCount="indefinite" />
                </rect>
                ''')
            else:
                grid_svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{BOX_SIZE}" height="{BOX_SIZE}" rx="2.5" fill="{base_col}"/>')

    # Output Fixed-Length 4-Block Snake (Gradient + Shrinking)
    snake_parts_svg = []
    def rgb_to_hex(r, g, b): return f"#{r:02x}{g:02x}{b:02x}"
    r1, g1, b1 = 76, 29, 149   # Head (Dark Purple)
    r2, g2, b2 = 216, 180, 254 # Tail (Light Purple)

    for K in range(SNAKE_LEN):
        ratio = K / (SNAKE_LEN - 1)
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        color = rgb_to_hex(r, g, b)
        
        # Shrink sizes: 11px (head) down to 5px (tail)
        size = 11.0 - (ratio * 6.0)
        offset = (11.0 - size) / 2.0
        
        x_vals = []
        y_vals = []
        for t in range(TOTAL_TICKS):
            # No exiting the grid. The tail is locked behind the head perfectly.
            # At t=0, all parts are at simulation_moves[0]. They unfurl naturally.
            pos = simulation_moves[max(0, t - K)]
            x_vals.append(f"{(pos[0] * STEP + offset):.1f}")
            y_vals.append(f"{(pos[1] * STEP + offset):.1f}")
            
        x_str = ";".join(x_vals)
        y_str = ";".join(y_vals)

        snake_parts_svg.append(f'''
        <rect width="{size:.1f}" height="{size:.1f}" rx="{size/3:.1f}" fill="{color}">
          <animate attributeName="x" values="{x_str}" dur="{DURATION:.1f}s" repeatCount="indefinite" calcMode="discrete"/>
          <animate attributeName="y" values="{y_str}" dur="{DURATION:.1f}s" repeatCount="indefinite" calcMode="discrete"/>
        </rect>
        ''')

    snake_parts_svg.reverse()

    return f'''
    <g id="contribGrid">
      {"".join(grid_svg)}
      {"".join(snake_parts_svg)}
    </g>
    '''

contribution_snake_markup = build_arcade_snake(recent_weeks)

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
positions = [(0, 0, 154), (162, 0, 140), (0, 34, 124), (132, 34, 144), (0, 68, 146), (154, 68, 118)]
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

print(f"🎉 SUCCESS! Flawless Platane Engine Generated.")
