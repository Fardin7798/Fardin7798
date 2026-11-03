"""Builds the clickable Open Source Contributions section of the profile README.

GitHub shows SVGs as plain images, so links inside an SVG don't work. This script
draws each piece (badges, repo cards, PR rows, buttons) as its own small SVG in
contrib/, wraps each one in a link in README.md between the CONTRIB markers, and
writes CONTRIBUTIONS.md with every repo and PR. Runs daily from
.github/workflows/contributions.yml. Standard library only.
"""
import base64
import datetime as dt
import glob
import json
import os
import re
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "Fardin7798")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
TOP_REPOS = 4
RECENT = 6
DIR = "contrib"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
TXT, MUT, BOR, CARD, BG = "#e6edf3", "#8b949e", "#30363d", "#161b22", "#0d1117"
PUR, GRN, BLU, YEL, RED = "#a371f7", "#3fb950", "#58a6ff", "#d29922", "#f85149"


def get(url, raw=False):
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
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)


def clip(s, n):
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def day(iso):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(IST).strftime("%-d %b %Y")


def avatar(url):
    try:
        data = get(url + ("&" if "?" in url else "?") + "s=88", raw=True)
        mime = "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"
        return f"data:{mime};base64," + base64.b64encode(data).decode()
    except Exception:
        return ""


def T(x, y, s, size, color=TXT, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" '
            f'text-anchor="{anchor}">{escape(str(s))}</text>')


def save(name, w, h, body, bg=True):
    rect = f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="8" fill="{CARD}" stroke="{BOR}"/>' if bg else ""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
           f'font-family="{FONT}">{rect}{body}</svg>')
    with open(f"{DIR}/{name}", "w", encoding="utf-8") as f:
        f.write(svg)
    return f"{DIR}/{name}"


def heading(name, title, right=""):
    body = f'<rect width="1000" height="56" rx="8" fill="{BG}"/>' + T(4, 38, title, 22, weight=700)
    if right:
        body += T(996, 38, right, 13, MUT, anchor="end")
    return save(name, 1000, 56, body, bg=False)


def badge(name, label, val, col):
    lw, vw = len(label) * 8.6 + 24, len(str(val)) * 8.6 + 24
    w = int(lw + vw)
    body = (f'<clipPath id="r"><rect width="{w}" height="28" rx="4"/></clipPath><g clip-path="url(#r)">'
            f'<rect width="{lw}" height="28" fill="#555"/><rect x="{lw}" width="{vw}" height="28" fill="{col}"/></g>'
            + T(lw / 2, 19, label, 11, "#fff", 700, "middle") + T(lw + vw / 2, 19, val, 11, "#fff", 700, "middle"))
    return save(name, w, 28, body, bg=False), w


def repo_card(name, r):
    w, h = 490, 84
    owner, rn = r["name"].split("/")
    body = f'<clipPath id="c"><circle cx="40" cy="42" r="22"/></clipPath>'
    body += (f'<image href="{r["img"]}" x="18" y="20" width="44" height="44" clip-path="url(#c)"/>' if r.get("img")
             else f'<circle cx="40" cy="42" r="22" fill="{BOR}"/>')
    body += (f'<text x="76" y="36" font-size="13" fill="{MUT}">{escape(clip(owner, 16))} / '
             f'<tspan font-size="14" fill="{BLU}" font-weight="700">{escape(clip(rn, 22))}</tspan></text>')
    body += T(76, 64, f"★ {short(r['stars'])}", 13, YEL)
    body += T(76 + (len(short(r["stars"])) + 2) * 8 + 18, 64, f"{r['prs']} PR{'s' if r['prs'] > 1 else ''}", 13, MUT)
    tag, col = (f"{r['merged']} merged", PUR) if r["merged"] else (("open", GRN) if r["open"] else ("closed", MUT))
    pw = len(tag) * 8 + 22
    body += f'<rect x="{w-18-pw}" y="28" width="{pw}" height="26" rx="13" fill="none" stroke="{col}"/>'
    body += T(w - 18 - pw / 2, 46, tag, 12, col, 700, "middle")
    return save(name, w, h, body)


def pr_row(name, p):
    w, h = 1000, 48
    st, col, sym = ("Merged", PUR, "◆") if p["merged"] else (("Open", GRN, "●") if p["state"] == "open" else ("Closed", RED, "✕"))
    body = (T(18, 30, f"{sym} {st}", 13, col, 700) + T(140, 30, clip(p["title"], 54), 13, BLU)
            + T(610, 30, clip(p["repo"], 30), 12, MUT) + T(982, 30, day(p["created_at"]), 12, MUT, anchor="end"))
    return save(name, w, h, body)


def button(name, label):
    w = int(len(label) * 8 + 40)
    body = T(w / 2, 23, label, 13, BLU, 700, "middle")
    return save(name, w, 36, body), w


def main():
    os.makedirs(DIR, exist_ok=True)
    for f in glob.glob(f"{DIR}/*.svg"):
        os.remove(f)

    prs = fetch_prs()
    for p in prs:
        p["merged"] = bool((p.get("pull_request") or {}).get("merged_at"))
        p["repo"] = p["repository_url"].split("/repos/")[1]
    merged = sum(p["merged"] for p in prs)
    open_ = sum(p["state"] == "open" for p in prs)

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
            r["avatar"] = info.get("owner", {}).get("avatar_url", "")
        except Exception:
            r["stars"], r["avatar"] = 0, ""
    active = [r for r in repos.values() if r["merged"] or r["open"]] or list(repos.values())
    top = sorted(active, key=lambda r: -r["stars"])[:TOP_REPOS]
    for r in top:
        r["img"] = avatar(r["avatar"]) if r["avatar"] else ""

    recent = sorted([p for p in prs if p["state"] == "open" or p["merged"]],
                    key=lambda p: p["created_at"], reverse=True)[:RECENT]
    today = dt.datetime.now(IST).strftime("%-d %b %Y")
    see_all = "./CONTRIBUTIONS.md"

    md = []
    md.append(f'<img src="{heading("title.svg", "Open Source Contributions")}" width="100%" alt="Open Source Contributions" />')
    links = []
    for i, (label, val, col, url) in enumerate([
            ("MERGED PRS", merged, PUR, search_url("is:merged")),
            ("OPEN PRS", open_, GRN, search_url("is:open")),
            ("REPOS", len(repos), BLU, see_all),
            ("TOTAL PRS", len(prs), "#6e7681", search_url())]):
        path, w = badge(f"badge-{i}.svg", label, val, col)
        links.append(f'<a href="{url}"><img src="{path}" height="28" alt="{label}: {val}" /></a>')
    md.append("<p>\n" + "\n".join(links) + "\n</p>")

    more = len(repos) - len(top)
    md.append(f'<img src="{heading("repos-title.svg", "Repos I have contributed to", f"{len(repos)} repos")}" width="100%" alt="Repos I have contributed to" />')
    cards = []
    for i, r in enumerate(top):
        cards.append(f'<a href="https://github.com/{r["name"]}/pulls?q=is%3Apr+author%3A{USER}">'
                     f'<img src="{repo_card(f"repo-{i}.svg", r)}" width="49%" alt="{escape(r["name"])}" /></a>')
    md.append("<p>\n" + "\n".join(cards) + "\n</p>")
    bpath, _ = button("see-all-repos.svg", f"See all {len(repos)} repos →" if more > 0 else "See all repos →")
    md.append(f'<a href="{see_all}#repos"><img src="{bpath}" height="36" alt="See all repos" /></a>')

    md.append(f'<img src="{heading("prs-title.svg", "Recent pull requests", f"{len(prs)} total")}" width="100%" alt="Recent pull requests" />')
    rows = []
    for i, p in enumerate(recent):
        rows.append(f'<a href="{p["html_url"]}"><img src="{pr_row(f"pr-{i}.svg", p)}" width="100%" alt="{escape(p["title"])}" /></a>')
    md.append("\n".join(rows) if rows else "_No pull requests yet._")
    bpath, _ = button("see-all-prs.svg", f"See all {len(prs)} pull requests →")
    md.append(f'<a href="{see_all}#pull-requests"><img src="{bpath}" height="36" alt="See all pull requests" /></a>')
    md.append(f"<sub>Last updated: {today} · updates automatically every day</sub>")
    section = "\n\n".join(md)

    with open("README.md", encoding="utf-8") as f:
        readme = f.read()
    block = f"<!--CONTRIB:START-->\n{section}\n<!--CONTRIB:END-->"
    if "<!--CONTRIB:START-->" in readme:
        readme = re.sub(r"<!--CONTRIB:START-->.*?<!--CONTRIB:END-->", lambda m: block, readme, flags=re.S)
    else:
        readme = re.sub(r'\n*<img src="\./contributions\.svg"[^>]*/>\n*', "\n", readme).rstrip() + "\n\n" + block + "\n"
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    full = [f"# Open Source Contributions\n",
            f"Pull requests by [@{USER}](https://github.com/{USER}) to other people's repositories. "
            f"Updated automatically every day. Last updated: {today}.\n",
            f"**{merged}** merged · **{open_}** open · **{len(prs)}** total · **{len(repos)}** repos\n",
            "## Repos\n", "| Repo | Stars | PRs | Merged | Open |", "|---|---|---|---|---|"]
    for r in sorted(repos.values(), key=lambda r: -r["stars"]):
        full.append(f"| [{r['name']}](https://github.com/{r['name']}) | ★ {short(r['stars'])} | "
                    f"[{r['prs']}](https://github.com/{r['name']}/pulls?q=is%3Apr+author%3A{USER}) | {r['merged']} | {r['open']} |")
    full += ["\n## Pull requests\n", "| Status | Pull request | Repo | Date |", "|---|---|---|---|"]
    for p in sorted(prs, key=lambda p: p["created_at"], reverse=True):
        st = "🟣 Merged" if p["merged"] else ("🟢 Open" if p["state"] == "open" else "🔴 Closed")
        title = p["title"].replace("|", "\\|")
        full.append(f"| {st} | [{title}]({p['html_url']}) | [{p['repo']}](https://github.com/{p['repo']}) | {day(p['created_at'])} |")
    full.append(f"\n[← Back to profile](https://github.com/{USER})\n")
    with open("CONTRIBUTIONS.md", "w", encoding="utf-8") as f:
        f.write("\n".join(full))
    print(f"{len(prs)} PRs, {merged} merged, {open_} open, {len(repos)} repos")


if __name__ == "__main__":
    main()
