"""Builds the clickable Contributions section of the profile README.

GitHub shows SVGs as plain images, so links inside an SVG don't work. This script
draws each piece (stat tiles, section headers, repo cards, PR rows) as its own
small SVG in a light and a dark version (contrib/light, contrib/dark), wraps each
one in a link plus a <picture> that follows the visitor's theme, writes that into
README.md between the CONTRIB markers, and writes CONTRIBUTIONS.md with every repo
and PR. Runs daily from .github/workflows/contributions.yml. Standard library only.
"""
import base64
import datetime as dt
import glob
import json
import os
import re
import shutil
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "Fardin7798")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
TOP_REPOS = 3
RECENT = 4
MAX_MERGED = 3
DIR = "contrib"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
SEE_ALL = "./CONTRIBUTIONS.md"

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
THEMES = {
    "light": dict(bg="#ffffff", bd="#d1d9e0", tx="#1f2328", mu="#59636e", pu="#8250df", gr="#1a7f37", ln="#0969da"),
    "dark": dict(bg="#0d1117", bd="#3d444d", tx="#f0f6fc", mu="#9198a1", pu="#ab7df8", gr="#3fb950", ln="#4493f8"),
}
LANG = {"Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Rust": "#dea584", "Go": "#00ADD8",
        "Java": "#b07219", "Kotlin": "#A97BFF", "Dart": "#00B4AB", "C++": "#f34b7d", "C": "#555555", "C#": "#178600",
        "HTML": "#e34c26", "CSS": "#663399", "Swift": "#F05138", "Ruby": "#701516", "PHP": "#4F5D95", "Vue": "#41b883",
        "Svelte": "#ff3e00", "Shell": "#89e051", "Jupyter Notebook": "#DA5B0B", "MDX": "#fcb32c"}

# Character widths (1/1000 em) for ASCII 32..126, Helvetica/Arial metrics, used to keep text inside its box.
_R = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]
_B = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556, 333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584]

ICON_MERGE = "M5.45 5.154A4.25 4.25 0 0 0 9.25 7.5h1.378a2.251 2.251 0 1 1 0 1.5H9.25A5.734 5.734 0 0 1 5 7.123v3.505a2.25 2.25 0 1 1-1.5 0V5.372a2.25 2.25 0 1 1 1.95-.218ZM4.25 13.5a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm8.5-4.5a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5ZM5 3.25a.75.75 0 1 0 0 .005V3.25Z"
ICON_PR = "M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z"
ICON_STAR = "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"


def width(s, size, bold=False):
    t = _B if bold else _R
    return sum(t[ord(c) - 32] if 32 <= ord(c) < 127 else 600 for c in s) * size / 1000 * 1.2


def fit(s, size, maxw, bold=False):
    if width(s, size, bold) <= maxw:
        return s
    while s and width(s + "…", size, bold) > maxw:
        s = s[:-1]
    return s.rstrip() + "…"


def get(url, raw=False, tries=3):
    for i in range(tries):
        try:
            return _get(url, raw)
        except Exception:
            if i == tries - 1:
                raise
            import time
            time.sleep(2 * (i + 1))


def _get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": USER, "Accept": "application/vnd.github+json"})
    if TOKEN and "api.github.com" in url:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return data if raw else json.loads(data)


def search_url(extra=""):
    q = f"author:{USER} is:pr -user:{USER} {extra}".strip()
    return "https://github.com/search?" + urllib.parse.urlencode({"q": q, "type": "pullrequests", "s": "created", "o": "desc"})


def fetch_prs():
    items, page = [], 1
    while True:
        q = urllib.parse.quote(f"author:{USER} is:pr -user:{USER}")
        res = get(f"https://api.github.com/search/issues?q={q}&per_page=100&page={page}&sort=created&order=desc")
        items += res.get("items", [])
        if len(items) >= res.get("total_count", 0) or not res.get("items"):
            return items
        page += 1


def short(n):
    if n >= 1000:
        v = n / 1000
        return f"{v:.0f}k" if v >= 100 else f"{v:.1f}k"
    return str(n)


def day(iso):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(IST).strftime("%-d %b %Y")


def avatar(url):
    try:
        data = get(url + ("&" if "?" in url else "?") + "s=64", raw=True)
        mime = "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"
        return f"data:{mime};base64," + base64.b64encode(data).decode()
    except Exception:
        return ""


LABELS = [("a11y", "Accessibility"), ("accessib", "Accessibility"), ("feat", "Feature"), ("fix", "Fix"),
          ("docs", "Docs"), ("content", "Content"), ("perf", "Performance"), ("refactor", "Refactor"),
          ("test", "Tests"), ("chore", "Chore"), ("style", "Style")]


def label_and_title(raw):
    """'fix(menu): ask for x (note)' -> ('Fix', 'Ask for x'). Accessibility wins when the title mentions it."""
    m = re.match(r"^\s*([a-zA-Z]+)(\([^)]*\))?!?:\s*(.+)$", raw)
    prefix, title = (m.group(1).lower(), m.group(3)) if m else ("", raw)
    title = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip() or title
    title = re.sub(r"\ba11y\b", "accessibility", title)
    title = title[:1].upper() + title[1:]
    low = raw.lower()
    label = ""
    if "a11y" in low or "accessib" in low:
        label = "Accessibility"
    else:
        for key, name in LABELS:
            if prefix.startswith(key):
                label = name
                break
        if not label:
            first = title.split()[0].lower() if title.split() else ""
            if first in ("add", "offer", "support", "allow", "implement", "introduce"):
                label = "Feature"
            elif first in ("fix", "keep", "handle", "prevent", "correct", "resolve"):
                label = "Fix"
    return label, title


def svg(w, h, body, c, border=True):
    rect = (f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="6" fill="{c["bg"]}" stroke="{c["bd"]}"/>'
            if border else f'<rect width="{w}" height="{h}" fill="{c["bg"]}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{FONT}">{rect}{body}</svg>')


def T(x, y, s, size, color, weight=400, anchor="start"):
    return (f'<text x="{x:.1f}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" '
            f'text-anchor="{anchor}">{escape(str(s))}</text>')


def icon(path, x, y, color, scale=1.0):
    return f'<path transform="translate({x} {y}) scale({scale})" fill="{color}" d="{path}"/>'


def save(name, w, h, build, border=True):
    """build(c) -> svg body. Writes light + dark copies and returns a <picture> tag."""
    for theme, c in THEMES.items():
        with open(f"{DIR}/{theme}/{name}", "w", encoding="utf-8") as f:
            f.write(svg(w, h, build(c), c, border))
    return name


def pic(name, alt, attr):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{DIR}/dark/{name}" />'
            f'<img src="{DIR}/light/{name}" {attr} alt="{escape(alt)}" /></picture>')


def link(url, name, alt, attr):
    return f'<a href="{url}">{pic(name, alt, attr)}</a>'


# ---------- pieces ----------

def tile(name, value, label, color_key):
    def b(c):
        col = c[color_key] if color_key else c["tx"]
        return T(20, 46, value, 30, col, 600) + T(20, 70, label, 13, c["mu"])
    return save(name, 200, 92, b)


def header(name, title, right=""):
    def b(c):
        out = T(1, 26, title, 16, c["tx"], 600)
        if right:
            out += T(999, 26, right + " →", 14, c["ln"], 400, "end")
        return out
    return save(name, 1000, 38, b, border=False)


def repo_card(name, r):
    owner, rn = r["name"].split("/")
    owner_s = fit(owner, 13, 110)
    rn_s = fit(rn, 13, 290 - 50 - width(owner_s + " / ", 13), True)

    def b(c):
        out = f'<clipPath id="a"><circle cx="30" cy="30" r="10"/></clipPath>'
        out += (f'<image href="{r["img"]}" x="20" y="20" width="20" height="20" clip-path="url(#a)"/>' if r.get("img")
                else f'<circle cx="30" cy="30" r="10" fill="{c["bd"]}"/>')
        out += (f'<circle cx="30" cy="30" r="10" fill="none" stroke="{c["bd"]}" stroke-width="0.5"/>'
                f'<text x="48" y="35" font-size="13" fill="{c["mu"]}">{escape(owner_s)} / '
                f'<tspan fill="{c["ln"]}" font-weight="600">{escape(rn_s)}</tspan></text>')
        x = 20
        if r.get("lang"):
            out += f'<circle cx="{x+5}" cy="63" r="5" fill="{LANG.get(r["lang"], "#8b949e")}"/>'
            out += T(x + 15, 67, r["lang"], 12, c["mu"])
            x += 15 + width(r["lang"], 12) + 14
        out += icon(ICON_STAR, x, 56, c["mu"], 0.8125) + T(x + 18, 67, short(r["stars"]), 12, c["mu"])
        x += 18 + width(short(r["stars"]), 12) + 14
        out += T(x, 67, f"{r['prs']} PR{'s' if r['prs'] > 1 else ''}", 12, c["mu"])
        return out
    return save(name, 320, 88, b)


def pr_row(name, p):
    label, title = label_and_title(p["title"])
    num = f'#{p["number"]}'
    tag_w = width(label, 12) + 16 if label else 0
    tag_right = 652
    title_max = (tag_right - tag_w - 12 if label else 660) - 48 - width(" " + num, 14)
    title_s = fit(title, 14, title_max, True)
    repo_s = fit(p["repo"], 12, 190)

    def b(c):
        col = c["pu"] if p["merged"] else c["gr"]
        out = icon(ICON_MERGE if p["merged"] else ICON_PR, 18, 14, col)
        out += (f'<text x="46" y="27" font-size="14" fill="{c["tx"]}" font-weight="600">{escape(title_s)}'
                f'<tspan fill="{c["mu"]}" font-weight="400"> {num}</tspan></text>')
        if label:
            x = tag_right - tag_w
            out += (f'<rect x="{x:.1f}" y="11" width="{tag_w:.1f}" height="20" rx="10" fill="none" stroke="{c["bd"]}"/>'
                    + T(x + tag_w / 2, 25, label, 12, c["mu"], 500, "middle"))
        out += T(676, 26, repo_s, 12, c["mu"]) + T(982, 26, day(p["created_at"]), 12, c["mu"], anchor="end")
        return out
    return save(name, 1000, 42, b)


def main():
    if os.path.isdir(DIR):
        shutil.rmtree(DIR)
    for t in THEMES:
        os.makedirs(f"{DIR}/{t}", exist_ok=True)

    prs = fetch_prs()
    for p in prs:
        p["merged"] = bool((p.get("pull_request") or {}).get("merged_at"))
        p["repo"] = p["repository_url"].split("/repos/")[1]
    merged_prs = sorted([p for p in prs if p["merged"]], key=lambda p: p["created_at"], reverse=True)
    open_prs = sorted([p for p in prs if p["state"] == "open"], key=lambda p: p["created_at"], reverse=True)

    repos = {}
    for p in prs:
        r = repos.setdefault(p["repo"], {"name": p["repo"], "prs": 0, "merged": 0, "open": 0})
        r["prs"] += 1
        r["merged"] += p["merged"]
        r["open"] += p["state"] == "open"
    for r in repos.values():
        try:
            info = get(f"https://api.github.com/repos/{r['name']}")
            r["stars"] = info.get("stargazers_count", 0)
            r["lang"] = info.get("language") or ""
            r["avatar"] = info.get("owner", {}).get("avatar_url", "")
        except Exception:
            r["stars"], r["lang"], r["avatar"] = 0, "", ""
    total_stars = sum(r["stars"] for r in repos.values())
    active = [r for r in repos.values() if r["merged"] or r["open"]] or list(repos.values())
    top = sorted(active, key=lambda r: -r["stars"])[:TOP_REPOS]
    for r in top:
        r["img"] = avatar(r["avatar"]) if r["avatar"] else ""

    today = dt.datetime.now(IST).strftime("%-d %b %Y")
    md = ["## Contributions", "Fixes and features for open-source projects I use."]

    tiles = [
        ("PRs", str(len(prs)), "Pull requests", None, search_url()),
        ("merged", str(len(merged_prs)), "Merged", "pu", search_url("is:merged")),
        ("open", str(len(open_prs)), "Open", "gr", search_url("is:open")),
        ("repos", str(len(repos)), "Repositories", None, SEE_ALL + "#repos"),
        ("stars", short(total_stars), "Stars on those repos", None, SEE_ALL + "#repos"),
    ]
    md.append("<p>\n" + "\n".join(
        link(url, tile(f"stat-{key.lower()}.svg", val, lab, ck), f"{lab}: {val}", 'width="19%"')
        for key, val, lab, ck, url in tiles) + "\n</p>")

    if merged_prs:
        md.append(link(search_url("is:merged"), header("h-merged.svg", "Merged"), "Merged", 'width="100%"'))
        md.append("<br>\n".join(link(p["html_url"], pr_row(f"merged-{i}.svg", p), p["title"], 'width="100%"')
                                for i, p in enumerate(merged_prs[:MAX_MERGED])))

    md.append(link(SEE_ALL + "#repos", header("h-repos.svg", "Repositories", f"See all {len(repos)} repositories"),
                   f"Repositories: see all {len(repos)}", 'width="100%"'))
    md.append("<p>\n" + "\n".join(link(f"https://github.com/{r['name']}", repo_card(f"repo-{i}.svg", r), r["name"],
                                       'width="32%"') for i, r in enumerate(top)) + "\n</p>")

    recent = open_prs[:RECENT]
    if recent:
        md.append(link(SEE_ALL + "#pull-requests", header("h-recent.svg", "Recent", f"See all {len(prs)} pull requests"),
                       f"Recent: see all {len(prs)} pull requests", 'width="100%"'))
        md.append("<br>\n".join(link(p["html_url"], pr_row(f"recent-{i}.svg", p), p["title"], 'width="100%"')
                                for i, p in enumerate(recent)))
    md.append(f'<p align="right"><sub>Updated daily · last update {today}</sub></p>')
    section = "\n\n".join(md)

    with open("README.md", encoding="utf-8") as f:
        readme = f.read()
    block = f"<!--CONTRIB:START-->\n{section}\n<!--CONTRIB:END-->"
    readme = re.sub(r"<!--CONTRIB:START-->.*?<!--CONTRIB:END-->", lambda m: block, readme, flags=re.S)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    full = ["# Contributions\n",
            f"Pull requests by [@{USER}](https://github.com/{USER}) to other people's repositories. "
            f"Updated automatically every day. Last updated: {today}.\n",
            f"**{len(prs)}** pull requests · **{len(merged_prs)}** merged · **{len(open_prs)}** open · "
            f"**{len(repos)}** repos · **{short(total_stars)}** stars on those repos\n",
            "## Repos\n", "| Repo | Language | Stars | PRs | Merged | Open |", "|---|---|---|---|---|---|"]
    for r in sorted(repos.values(), key=lambda r: -r["stars"]):
        full.append(f"| [{r['name']}](https://github.com/{r['name']}) | {r['lang'] or '–'} | ★ {short(r['stars'])} | "
                    f"[{r['prs']}](https://github.com/{r['name']}/pulls?q=is%3Apr+author%3A{USER}) | {r['merged']} | {r['open']} |")
    full += ["\n## Pull requests\n", "| Status | Pull request | Type | Repo | Date |", "|---|---|---|---|---|"]
    for p in sorted(prs, key=lambda p: p["created_at"], reverse=True):
        st = "🟣 Merged" if p["merged"] else ("🟢 Open" if p["state"] == "open" else "⚪ Closed")
        title = p["title"].replace("|", "\\|")
        full.append(f"| {st} | [{title}]({p['html_url']}) #{p['number']} | {label_and_title(p['title'])[0] or '–'} | "
                    f"[{p['repo']}](https://github.com/{p['repo']}) | {day(p['created_at'])} |")
    full.append(f"\n[← Back to profile](https://github.com/{USER})\n")
    with open("CONTRIBUTIONS.md", "w", encoding="utf-8") as f:
        f.write("\n".join(full))
    print(f"{len(prs)} PRs, {len(merged_prs)} merged, {len(open_prs)} open, {len(repos)} repos, {total_stars} stars")


if __name__ == "__main__":
    main()
