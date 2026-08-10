#!/usr/bin/env python3
"""
generate_stats.py
Fetches live data from the GitHub API and generates two animated SVG cards:
  assets/generated/stats.svg     — repo count, stars, contributions, followers
  assets/generated/languages.svg — top languages with animated progress bars

Run automatically via GitHub Actions every 6 hours, or trigger manually.
"""

import os
import requests
from collections import defaultdict
from datetime import datetime

USERNAME = "RudraChintalwar"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}
GRAPHQL_URL = "https://api.github.com/graphql"

# ── Language colours matching GitHub's palette ─────────────────────────────
LANG_COLORS = {
    "Python":           "#3572A5",
    "JavaScript":       "#F1E05A",
    "TypeScript":       "#3178C6",
    "HTML":             "#E34C26",
    "CSS":              "#563D7C",
    "C++":              "#F34B7D",
    "C":                "#555555",
    "Jupyter Notebook": "#DA5B0B",
    "Shell":            "#89E051",
    "Dockerfile":       "#384D54",
    "YAML":             "#CB171E",
}


def gh_get(path):
    r = requests.get(f"https://api.github.com/{path}", headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def graphql_query(q):
    r = requests.post(GRAPHQL_URL, headers=HEADERS, json={"query": q}, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_data():
    user = gh_get(f"users/{USERNAME}")

    # Paginate repos
    repos, page = [], 1
    while True:
        batch = gh_get(
            f"users/{USERNAME}/repos?per_page=100&page={page}&type=owner"
        )
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    # Aggregate from repo metadata (no extra API calls)
    lang_counts = defaultdict(int)
    total_stars = 0
    for r in repos:
        if r.get("fork"):
            continue
        total_stars += r.get("stargazers_count", 0)
        if r.get("language"):
            lang_counts[r["language"]] += 1

    # Contributions via GraphQL
    gql = graphql_query(f"""
    {{
      user(login: "{USERNAME}") {{
        contributionsCollection {{
          contributionCalendar {{ totalContributions }}
        }}
      }}
    }}
    """)
    try:
        total_contrib = (
            gql["data"]["user"]
            ["contributionsCollection"]["contributionCalendar"]
            ["totalContributions"]
        )
    except (KeyError, TypeError):
        total_contrib = 0

    # Language percentages
    total_repos_w_lang = sum(lang_counts.values()) or 1
    top_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:6]
    languages = [
        {
            "name": name,
            "pct": round((cnt / total_repos_w_lang) * 100, 1),
        }
        for name, cnt in top_langs
    ]

    return {
        "public_repos":  user.get("public_repos", 0),
        "followers":     user.get("followers", 0),
        "total_stars":   total_stars,
        "total_contrib": total_contrib,
        "languages":     languages,
    }


# ── SVG generators ─────────────────────────────────────────────────────────

def make_stats_svg(d):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"""<svg viewBox="0 0 860 178" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="GitHub stats for RudraChintalwar">
  <defs>
    <pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="0.5" fill="#1C1C1C"/>
    </pattern>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <linearGradient id="topBar" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%"   stop-color="#38BDF8"/>
      <stop offset="50%"  stop-color="#A855F7"/>
      <stop offset="100%" stop-color="#22C55E"/>
    </linearGradient>
  </defs>

  <rect width="860" height="178" fill="#0A0A0A" rx="10"/>
  <rect width="860" height="178" fill="url(#dots)" rx="10" opacity="0.5"/>
  <rect x="1" y="1" width="858" height="176" fill="none" stroke="#1F1F23" stroke-width="1" rx="9"/>
  <rect x="0" y="0" width="860" height="3" fill="url(#topBar)" rx="1"/>

  <text x="22" y="25" font-family="'SFMono-Regular',Consolas,monospace" font-size="9" letter-spacing="2.5" fill="#3F3F46">GITHUB.STATS</text>
  <circle cx="826" cy="19" r="3.5" fill="#22C55E">
    <animate attributeName="opacity" values="1;0.2;1" dur="2s" repeatCount="indefinite"/>
  </circle>
  <text x="834" y="23" font-family="'SFMono-Regular',Consolas,monospace" font-size="8" letter-spacing="1" fill="#27272A">LIVE</text>
  <line x1="22" y1="33" x2="838" y2="33" stroke="#1A1A1A" stroke-width="1"/>

  <!-- REPOS -->
  <text x="107" y="92" text-anchor="middle" font-family="'Helvetica Neue',Arial,sans-serif" font-size="44" font-weight="800" fill="#F5F5F5" filter="url(#glow)">{d['public_repos']}</text>
  <text x="107" y="118" text-anchor="middle" font-family="'SFMono-Regular',Consolas,monospace" font-size="8" letter-spacing="2" fill="#52525B">PUBLIC REPOS</text>
  <line x1="215" y1="42" x2="215" y2="138" stroke="#1A1A1A" stroke-width="1"/>

  <!-- STARS -->
  <text x="322" y="92" text-anchor="middle" font-family="'Helvetica Neue',Arial,sans-serif" font-size="44" font-weight="800" fill="#F5F5F5" filter="url(#glow)">{d['total_stars']}</text>
  <text x="322" y="118" text-anchor="middle" font-family="'SFMono-Regular',Consolas,monospace" font-size="8" letter-spacing="2" fill="#52525B">TOTAL STARS</text>
  <line x1="430" y1="42" x2="430" y2="138" stroke="#1A1A1A" stroke-width="1"/>

  <!-- CONTRIBUTIONS -->
  <text x="537" y="88" text-anchor="middle" font-family="'Helvetica Neue',Arial,sans-serif" font-size="38" font-weight="800" fill="#38BDF8" filter="url(#glow)">{d['total_contrib']}</text>
  <text x="537" y="110" text-anchor="middle" font-family="'SFMono-Regular',Consolas,monospace" font-size="8" letter-spacing="2" fill="#52525B">CONTRIBUTIONS</text>
  <text x="537" y="124" text-anchor="middle" font-family="'SFMono-Regular',Consolas,monospace" font-size="7" letter-spacing="1" fill="#27272A">THIS YEAR</text>
  <line x1="645" y1="42" x2="645" y2="138" stroke="#1A1A1A" stroke-width="1"/>

  <!-- FOLLOWERS -->
  <text x="752" y="92" text-anchor="middle" font-family="'Helvetica Neue',Arial,sans-serif" font-size="44" font-weight="800" fill="#F5F5F5" filter="url(#glow)">{d['followers']}</text>
  <text x="752" y="118" text-anchor="middle" font-family="'SFMono-Regular',Consolas,monospace" font-size="8" letter-spacing="2" fill="#52525B">FOLLOWERS</text>

  <line x1="22" y1="146" x2="838" y2="146" stroke="#1A1A1A" stroke-width="1"/>
  <text x="22" y="163" font-family="'SFMono-Regular',Consolas,monospace" font-size="7" fill="#27272A">// auto-generated · {ts}</text>
  <text x="838" y="163" text-anchor="end" font-family="'SFMono-Regular',Consolas,monospace" font-size="7" fill="#27272A">RudraChintalwar · GitHub</text>
</svg>"""


def make_langs_svg(d):
    langs = d["languages"]
    if not langs:
        langs = [{"name": "Python", "pct": 100}]

    row_h = 44
    h = 52 + len(langs) * row_h + 28
    bars = ""

    for i, lang in enumerate(langs):
        y      = 48 + i * row_h
        color  = LANG_COLORS.get(lang["name"], "#71717A")
        bar_w  = int((lang["pct"] / 100) * 350)
        delay  = f"{i * 0.15:.2f}s"

        bars += f"""
  <text x="20" y="{y + 14}" font-family="'SFMono-Regular',Consolas,monospace" font-size="10.5" fill="#A1A1AA">{lang['name']}</text>
  <text x="410" y="{y + 14}" text-anchor="end" font-family="'SFMono-Regular',Consolas,monospace" font-size="10.5" fill="#52525B">{lang['pct']}%</text>
  <rect x="20" y="{y + 20}" width="390" height="7" rx="3.5" fill="#1A1A1A"/>
  <rect x="20" y="{y + 20}" width="0" height="7" rx="3.5" fill="{color}" opacity="0.9">
    <animate attributeName="width" from="0" to="{bar_w}" begin="{delay}" dur="0.8s" fill="freeze" calcMode="spline" keySplines="0.25 0.46 0.45 0.94" keyTimes="0;1"/>
  </rect>"""

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return f"""<svg viewBox="0 0 430 {h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Top languages for RudraChintalwar">
  <defs>
    <pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="0.5" fill="#1C1C1C"/>
    </pattern>
    <linearGradient id="topBar" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#A855F7"/>
      <stop offset="100%" stop-color="#38BDF8"/>
    </linearGradient>
  </defs>

  <rect width="430" height="{h}" fill="#0A0A0A" rx="10"/>
  <rect width="430" height="{h}" fill="url(#dots)" rx="10" opacity="0.5"/>
  <rect x="1" y="1" width="428" height="{h-2}" fill="none" stroke="#1F1F23" stroke-width="1" rx="9"/>
  <rect x="0" y="0" width="430" height="3" fill="url(#topBar)" rx="1"/>

  <text x="20" y="26" font-family="'SFMono-Regular',Consolas,monospace" font-size="9" letter-spacing="2.5" fill="#3F3F46">TOP.LANGUAGES</text>
  <circle cx="400" cy="20" r="3.5" fill="#A855F7">
    <animate attributeName="opacity" values="1;0.2;1" dur="2.5s" repeatCount="indefinite"/>
  </circle>
  <line x1="20" y1="35" x2="410" y2="35" stroke="#1A1A1A" stroke-width="1"/>
  {bars}
  <line x1="20" y1="{h - 20}" x2="410" y2="{h - 20}" stroke="#1A1A1A" stroke-width="1"/>
  <text x="20" y="{h - 7}" font-family="'SFMono-Regular',Consolas,monospace" font-size="7" fill="#27272A">// auto-generated · {ts}</text>
</svg>"""


def main():
    print(f"[stats] fetching data for {USERNAME}…")
    d = fetch_data()
    print(f"[stats] repos={d['public_repos']} stars={d['total_stars']} contrib={d['total_contrib']} followers={d['followers']}")
    print(f"[stats] languages={[l['name'] for l in d['languages']]}")

    os.makedirs("assets/generated", exist_ok=True)

    with open("assets/generated/stats.svg", "w", encoding="utf-8") as f:
        f.write(make_stats_svg(d))
    print("[stats] ✓ assets/generated/stats.svg")

    with open("assets/generated/languages.svg", "w", encoding="utf-8") as f:
        f.write(make_langs_svg(d))
    print("[stats] ✓ assets/generated/languages.svg")


if __name__ == "__main__":
    main()
