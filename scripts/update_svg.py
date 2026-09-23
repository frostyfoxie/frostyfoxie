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

# --- LOADS YOUR EXACT UPLOADED ICONS ---
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
                print(f"Loaded your icon from icons/{found_file}")
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

# =================================================================
# 2. FETCH ALL-TIME COMMITS & ALL-TIME ACTIVE DAYS ACROSS ALL YEARS
# =================================================================
total_commits = 0
active_dates = set()

# Discover all active contribution years reported by GitHub GraphQL
years_to_check = set(range(created_year, current_year + 1))
try:
    years_query = """
    query($username: String!) {
      user(login: $username) {
        contributionsCollection {
          contributionYears
        }
      }
    }
    """
    years_data = graphql_request(years_query, {"username": USERNAME})
    contrib_years = years_data.get("data", {}).get("user", {}).get("contributionsCollection", {}).get("contributionYears", [])
    if contrib_years:
        years_to_check.update(contrib_years)
except Exception as e:
    print(f"Notice: Could not fetch contributionYears directly ({e}), checking from account creation year.")

for year in sorted(years_to_check):
    gql_query = """
    query($username: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $username) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          restrictedContributionsCount
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    try:
        data = graphql_request(gql_query, {
            "username": USERNAME,
            "from": f"{year}-01-01T00:00:00Z",
            "to": f"{year}-12-31T23:59:59Z"
        })
        col = data["data"]["user"]["contributionsCollection"]
        total_commits += col.get("totalCommitContributions", 0) + col.get("restrictedContributionsCount", 0)

        # Collect every date with commits/contributions across this year
        cal = col.get("contributionCalendar", {})
        for week in cal.get("weeks", []):
            for day in week.get("contributionDays", []):
                if day.get("contributionCount", 0) > 0 and "date" in day:
                    active_dates.add(day["date"])
    except Exception as e:
        print(f"Warning: Could not fetch contributions for year {year}: {e}")

commits_str = f"{total_commits // 1000}.{(total_commits % 1000) // 100}k+" if total_commits >= 1000 else str(total_commits)

# =================================================================
# 3. FETCH EXACT LAST 365 DAYS GRID FOR ANIMATED SNAKE
# =================================================================
gql_grid = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            date
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

# Include any dates from the rolling 365-day calendar to ensure none are missed
for week in recent_weeks:
    for day in week.get("contributionDays", []):
        if day.get("contributionCount", 0) > 0 and "date" in day:
            active_dates.add(day["date"])

total_active_days = len(active_dates)
active_days_str = f"{total_active_days} D"

# 4. Fetch Repos & Stars
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

# =================================================================
# 5. SMOOTH LINEAR ARCADE SNAKE (Solid Color, 7x7px Tail, Smooth Glide)
# =================================================================
def build_arcade_snake(weeks_data):
    if not weeks_data:
        return ""
    
    COLS = 53
    ROWS = 7
    BOX_SIZE = 11.0
    STEP = 14.0
    SNAKE_LEN = 4
    SOLID_SNAKE_COLOR = "#8a2be2"  # Clean solid arcade purple
    
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
                if curr == goal:
                    return path
                for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
                    nx, ny = curr[0] + dx, curr[1] + dy
                    if 0 <= nx < COLS and 0 <= ny < ROWS:
                        if (nx, ny) not in visited and (nx, ny) not in obstacles:
                            visited.add((nx, ny))
                            queue.append(path + [(nx, ny)])
            return None

        body_obs = set(snake_body[:-1])
        higher_obs = set()
        for lvl in range(current_level + 1, 5):
            higher_obs.update(all_targets[lvl])
        
        p = bfs(body_obs | higher_obs)
        if p: return p
        p = bfs(body_obs)
        if p: return p
        p = bfs(set())
        if p: return p
        return [start, goal]

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
                snake.pop()
                if step == closest_target:
                    eat_ticks[step] = tick
                    targets[current_level].remove(step)

    # Roam around if idle to fill up ~300 ticks
    min_ticks = 300
    corners = [(0, 0), (COLS - 1, 0), (COLS - 1, ROWS - 1), (0, ROWS - 1)]
    while tick < min_ticks:
        valid_corners = [c for c in corners if c != snake[0]]
        goal = random.choice(valid_corners)
        path = get_path(snake[0], goal, snake, 5, targets)
        for step in path[1:]:
            tick += 1
            simulation_moves.append(step)
            snake.insert(0, step)
            snake.pop()
            if tick >= min_ticks:
                break

    TOTAL_TICKS = len(simulation_moves)
    DURATION = max(24.0, TOTAL_TICKS * 0.11)

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

    # Fixed 4-Block Snake: Head (11x11px) -> Tail (strictly 7x7px)
    snake_parts_svg = []

    for K in range(SNAKE_LEN):
        size = 11.0 - (K * (4.0 / (SNAKE_LEN - 1)))
        offset = (11.0 - size) / 2.0
        rx = round(size * 0.25, 1)

        x_vals = []
        y_vals = []
        for t in range(TOTAL_TICKS):
            pos = simulation_moves[max(0, t - K)]
            x_vals.append(f"{(pos[0] * STEP + offset):.1f}")
            y_vals.append(f"{(pos[1] * STEP + offset):.1f}")
            
        x_str = ";".join(x_vals)
        y_str = ";".join(y_vals)

        snake_parts_svg.append(f'''
        <rect width="{size:.1f}" height="{size:.1f}" rx="{rx}" fill="{SOLID_SNAKE_COLOR}">
          <animate attributeName="x" values="{x_str}" dur="{DURATION:.1f}s" repeatCount="indefinite" calcMode="linear"/>
          <animate attributeName="y" values="{y_str}" dur="{DURATION:.1f}s" repeatCount="indefinite" calcMode="linear"/>
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

# 6. Dynamic Education — wrapped and clipped so user text never escapes the card
edu_list = config.get("education", [])
edu_svg = []
MAX_EDU_ITEMS = 5
def wrap_svg_text(text, width=34, max_lines=2):
    words = str(text).split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    lines = lines[:max_lines]
    if len(words) > 0 and len(lines) == max_lines and " ".join(lines) != str(text):
        lines[-1] = lines[-1][:max(1, width - 1)].rstrip() + "…"
    return [html.escape(line) for line in lines]

if edu_list:
    visible_items = edu_list[:MAX_EDU_ITEMS]
    line_y2 = 30 + (len(visible_items) - 1) * 52
    edu_svg.append(f'<line x1="6" y1="30" x2="6" y2="{line_y2}" stroke="#cbd5e1" stroke-width="1.5"/>')
    for i, item in enumerate(visible_items):
        cy = 30 + (i * 52)
        year = html.escape(str(item.get("year", "")))[:12]
        title_lines = wrap_svg_text(item.get("title", ""), width=28, max_lines=2)
        inst_lines = wrap_svg_text(item.get("institution", ""), width=32, max_lines=1)
        edu_svg.append(f'<circle cx="6" cy="{cy}" r="3.5" fill="#3b82f6"/>')
        edu_svg.append(f'<text x="20" y="{cy + 4}" class="body-font text-slate-900" font-size="10.5" font-weight="900">{year}</text>')
        for line_idx, line in enumerate(title_lines):
            edu_svg.append(f'<text x="60" y="{cy + 4 + line_idx * 12}" class="body-font text-slate-900" font-size="10.5" font-weight="800">{line}</text>')
        inst_y = cy + 17 + (len(title_lines) - 1) * 12
        edu_svg.append(f'<text x="60" y="{inst_y}" class="body-font text-slate-500" font-size="9.2" font-weight="500">{inst_lines[0] if inst_lines else ""}</text>')
education_markup = "\n".join(edu_svg)

# =================================================================
# 7. DYNAMIC SKILLS (ADAPTIVE WIDTH & FLUID ROW WRAPPING)
# =================================================================
def estimate_text_width(text, font_size=11.5):
    narrow = set("ijlItf'r!;:.,| /\\-()[]{}")
    wide = set("mwMW@%&#+=")
    w = 0.0
    for ch in text:
        if ch in narrow:
            w += font_size * 0.38
        elif ch in wide:
            w += font_size * 0.90
        elif ch.isupper() or ch.isdigit():
            w += font_size * 0.68
        else:
            w += font_size * 0.56
    return w

def get_pill_width(text, font_size=11.5):
    # 12px padding on each side gives 24px total padding
    text_w = estimate_text_width(text, font_size=font_size)
    return max(48, round(text_w + 24))

skills_list = config.get("skills", [])
skills_svg = []

ROW_HEIGHT = 26
ROW_STEP = 34       # 26px pill height + 8px gap between rows
COL_GAP = 8         # 8px horizontal gap between pills
MAX_ROW_WIDTH = 310 # Maximum content width allowed inside the card
MAX_ROWS = 3        # Up to 3 rows (y=0, 34, 68) to fit perfectly within the glass card

curr_x = 0
curr_y = 0
row_count = 1

for skill in skills_list:
    pill_w = get_pill_width(skill)
    pill_w = min(pill_w, MAX_ROW_WIDTH)
    
    # Wrap to next row if this pill exceeds the available row width
    if curr_x > 0 and (curr_x + pill_w > MAX_ROW_WIDTH):
        if row_count >= MAX_ROWS:
            break
        curr_y += ROW_STEP
        curr_x = 0
        row_count += 1
        
    mid_x = curr_x + (pill_w / 2.0)
    skills_svg.append(f'''    <rect x="{curr_x}" y="{curr_y}" width="{pill_w}" height="{ROW_HEIGHT}" rx="13" class="pill-bg"/>
    <text x="{mid_x:.1f}" y="{curr_y + 17}" text-anchor="middle" class="pill-text">{html.escape(skill)}</text>''')
    
    curr_x += pill_w + COL_GAP

skills_markup = "\n".join(skills_svg)

# 8. Dynamic Tech Stack
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

# 9. Behind the Code Text
subheading = html.escape(config.get("behind_the_code", {}).get("subheading", "STUDENT · WEB DEV · AI DEV · CURIOUS MIND"))
desc_paragraphs = config.get("behind_the_code", {}).get("description", [])
tspans = []
first_line = True
for para in desc_paragraphs:
    for i, line in enumerate(textwrap.wrap(para, width=78)):
        dy = "0" if first_line else ("30" if i == 0 else "22")
        first_line = False
        tspans.append(f'<tspan x="0" dy="{dy}">{html.escape(line)}</tspan>')
description_markup = "\n".join(tspans)

# 10. Contact Info & User's Uploaded Icons
instagram_handle = config.get("contact", {}).get("instagram", "oneinagoogolplex._")
email_address = config.get("contact", {}).get("email", user_data.get("email", "navneetkrgupta01@gmail.com"))

icon_github = load_icon_as_base64("github")
icon_instagram = load_icon_as_base64("instagram")
icon_email = load_icon_as_base64("email")

# 11. Generate Main profile.svg
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
    "{{BEHIND_THE_CODE_SUBHEADING}}": subheading,
    "{{BEHIND_THE_CODE_DESCRIPTION}}": description_markup,
    "{{EDUCATION_ITEMS}}": education_markup,
    "{{SKILLS_ITEMS}}": skills_markup,
    "{{TECH_STACK_ITEMS}}": tech_markup,
    "{{CONTRIBUTION_SNAKE_SECTION}}": contribution_snake_markup,
    "{{ICON_GITHUB}}": icon_github,
    "{{ICON_GITHUB_RED}}": icon_github
}

for key, val in replacements.items():
    template = template.replace(key, str(val))

output_path = os.path.join(REPO_ROOT, "profile.svg")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(template)

print(f"Generated profile.svg (height: 948px)")

# =================================================================
# 12. GENERATE THE 3 BUTTON SVGs (SEAMLESS 286px WIDTH)
# =================================================================
def generate_button_svg(filename, icon_b64, label, font_size="11.5px"):
    btn_svg = f'''<svg width="286" height="64" viewBox="0 0 286 64" xmlns="http://www.w3.org/2000/svg">
<defs>
  <filter id="glassShadow" x="-50%" y="-50%" width="200%" height="200%">
    <feDropShadow dx="0" dy="6" stdDeviation="10" flood-color="#0f172a" flood-opacity="0.04" />
  </filter>
  <filter id="buttonShadow" x="-50%" y="-50%" width="200%" height="200%">
    <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.04" />
  </filter>
</defs>
<style>
  .glass-card {{
    fill: rgba(255, 255, 255, 0.75);
    stroke: rgba(255, 255, 255, 0.9);
    stroke-width: 1.2;
    filter: url(#glassShadow);
  }}
  .footer-btn {{
    fill: #ffffff;
    stroke: #e2e8f0;
    stroke-width: 1;
    filter: url(#buttonShadow);
    transition: all 0.2s ease;
    cursor: pointer;
  }}
  svg:hover .footer-btn {{
    fill: #f8fafc;
    stroke: #cbd5e1;
  }}
  .btn-text {{
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    font-size: {font_size};
    font-weight: 700;
    fill: #1e293b;
  }}
</style>

<!-- Canvas Base Background -->
<rect width="100%" height="100%" fill="#f8fafc" />

<!-- Glass Card Container -->
<rect x="4" y="4" width="278" height="56" rx="16" class="glass-card" />

<!-- Inner White Button Pill -->
<rect x="12" y="11" width="262" height="42" rx="13" class="footer-btn" />

<!-- Uploaded Icon -->
<image href="{icon_b64}" x="22" y="21" width="22" height="22" preserveAspectRatio="xMidYMid meet" />

<!-- Label -->
<text x="54" y="37" class="btn-text">{label}</text>
</svg>'''
    
    file_path = os.path.join(REPO_ROOT, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(btn_svg)
    print(f"Generated {filename}")

# 1. Instagram
generate_button_svg(
    filename="btn_instagram.svg",
    icon_b64=icon_instagram,
    label=f"@{instagram_handle}",
    font_size="11.5px"
)

# 2. Email
generate_button_svg(
    filename="btn_email.svg",
    icon_b64=icon_email,
    label=email_address,
    font_size="10.5px"
)

# 3. GitHub
generate_button_svg(
    filename="btn_github.svg",
    icon_b64=icon_github,
    label=f"github.com/{USERNAME}",
    font_size="11.5px"
)
