"""Builds contributions.svg: Fardin7798's pull requests to other people's repos.

Runs daily from .github/workflows/contributions.yml. Standard library only.
"""
import base64
import datetime as dt
import json
import os
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "Fardin7798")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("OUT", "contributions.svg")
TOP_REPOS = 4
RECENT = 6


def get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": USER, "Accept": "application/vnd.github+json"})
    if TOKEN and "api.github.com" in url:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return data if raw else json.loads(data)


def fetch_prs():
    items, page = [], 1
    while True:
        q = f"author:{USER}+is:pr+-user:{USER}"
        res = get(f"https://api.github.com/search/issues?q={q}&per_page=100&page={page}&sort=created&order=desc")
        items += res.get("items", [])
        if len(items) >= res.get("total_count", 0) or not res.get("items"):
            return items
        page += 1


def short(n):
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)


def clip(s, n):
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def avatar(url):
    try:
        data = get(url + ("&" if "?" in url else "?") + "s=88", raw=True)
        mime = "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"
        return f"data:{mime};base64," + base64.b64encode(data).decode()
    except Exception:
        return ""


def main():
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

    recent = [p for p in prs if p["state"] == "open" or p["merged"]]
    recent.sort(key=lambda p: p["created_at"], reverse=True)
    recent = recent[:RECENT]

    W, X0 = 1000, 40
    F = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
    TXT, MUT, BOR, CARD = "#e6edf3", "#8b949e", "#30363d", "#161b22"
    PUR, GRN, BLU, YEL = "#a371f7", "#3fb950", "#58a6ff", "#d29922"
    o = []
    a = o.append

    def text(x, y, s, size, color=TXT, weight=400, anchor="start", baseline="auto"):
        a(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" '
          f'text-anchor="{anchor}" dominant-baseline="{baseline}">{escape(str(s))}</text>')

    text(X0, 56, "Open Source Contributions", 26, weight=700)
    a(f'<line x1="{X0}" y1="72" x2="{W-40}" y2="72" stroke="{BOR}"/>')

    bx, by = X0, 92
    for label, val, col in [("MERGED PRS", merged, PUR), ("OPEN PRS", open_, GRN),
                            ("REPOS", len(repos), BLU), ("TOTAL PRS", len(prs), "#6e7681")]:
        lw, vw = len(label) * 8.6 + 24, len(str(val)) * 8.6 + 24
        a(f'<rect x="{bx}" y="{by}" width="{lw}" height="28" fill="#555"/>')
        a(f'<rect x="{bx+lw}" y="{by}" width="{vw}" height="28" fill="{col}"/>')
        text(bx + lw / 2, by + 19, label, 11, "#fff", 700, "middle")
        text(bx + lw + vw / 2, by + 19, val, 11, "#fff", 700, "middle")
        bx += lw + vw + 10

    text(X0, 170, "Repos I've contributed to", 18, weight=700)
    cw, ch = 448, 84
    for i, r in enumerate(top):
        cx, cy = X0 + (i % 2) * (cw + 24), 186 + (i // 2) * (ch + 16)
        owner, name = r["name"].split("/")
        a(f'<a href="https://github.com/{r["name"]}"><rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="8" fill="{CARD}" stroke="{BOR}"/></a>')
        a(f'<clipPath id="c{i}"><circle cx="{cx+40}" cy="{cy+42}" r="22"/></clipPath>')
        if r["img"]:
            a(f'<image href="{r["img"]}" x="{cx+18}" y="{cy+20}" width="44" height="44" clip-path="url(#c{i})"/>')
        else:
            a(f'<circle cx="{cx+40}" cy="{cy+42}" r="22" fill="{BOR}"/>')
        a(f'<text x="{cx+76}" y="{cy+36}" font-size="13" fill="{MUT}">{escape(clip(owner, 18))} / '
          f'<tspan font-size="14" fill="{BLU}" font-weight="700">{escape(clip(name, 24))}</tspan></text>')
        text(cx + 76, cy + 66, f"★ {short(r['stars'])}", 13, YEL)
        text(cx + 76 + (len(short(r["stars"])) + 2) * 8 + 18, cy + 66, f"{r['prs']} PR{'s' if r['prs'] > 1 else ''}", 13, MUT)
        if r["merged"]:
            tag, col = f"{r['merged']} merged", PUR
        elif r["open"]:
            tag, col = "open", GRN
        else:
            tag, col = "closed", MUT
        pw = len(tag) * 8 + 22
        a(f'<rect x="{cx+cw-18-pw}" y="{cy+28}" width="{pw}" height="26" rx="13" fill="none" stroke="{col}"/>')
        text(cx + cw - 18 - pw / 2, cy + 46, tag, 12, col, 700, "middle")
    rows = (len(top) + 1) // 2
    y = 186 + rows * (ch + 16)
    more = len(repos) - len(top)
    if more > 0:
        text(X0, y + 20, f"+ {more} more repo{'s' if more > 1 else ''}", 13, MUT)
        y += 36

    text(X0, y + 36, "Recent pull requests", 18, weight=700)
    ty = y + 56
    cols = [X0, 160, 600, 835]
    th = 40 + len(recent) * 44
    a(f'<rect x="{X0}" y="{ty}" width="{W-80}" height="{th}" rx="6" fill="none" stroke="{BOR}"/>')
    a(f'<rect x="{X0+1}" y="{ty+1}" width="{W-82}" height="38" fill="{CARD}"/>')
    for x, h in zip(cols, ["Status", "Pull request", "Repo", "Date"]):
        text(x + 14, ty + 25, h, 13, weight=700)
    for i, p in enumerate(recent):
        ry = ty + 40 + i * 44
        a(f'<line x1="{X0+1}" y1="{ry}" x2="{W-41}" y2="{ry}" stroke="{BOR}"/>')
        st, col, sym = ("Merged", PUR, "◆") if p["merged"] else ("Open", GRN, "●")
        date = dt.datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")).strftime("%-d %b %Y")
        text(cols[0] + 14, ry + 27, f"{sym} {st}", 13, col, 700)
        a(f'<a href="{p["html_url"]}">')
        text(cols[1] + 14, ry + 27, clip(p["title"], 50), 13, BLU)
        a("</a>")
        text(cols[2] + 14, ry + 27, clip(p["repo"], 28), 12, MUT)
        text(cols[3] + 14, ry + 27, date, 12, MUT)
    if not recent:
        text(X0 + 14, ty + 66, "No pull requests yet.", 13, MUT)
        th = 80

    fy = ty + th + 34
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).strftime("%-d %b %Y")
    text(X0, fy, f"Last updated: {today}  ·  updates automatically every day", 12, MUT)
    H = fy + 30

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{F}">'
           f'<rect width="{W}" height="{H}" rx="12" fill="#0d1117"/>' + "".join(o) + "</svg>")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{len(prs)} PRs, {merged} merged, {open_} open, {len(repos)} repos -> {OUT}")


if __name__ == "__main__":
    main()
