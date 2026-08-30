"""
Fetch real GitHub contribution calendar data — no token, no GraphQL API.
GitHub serves the calendar as public HTML at /users/<username>/contributions.
"""
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = "Fardin7798"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "contributions.json"


def fetch_days(username: str):
    url = f"https://github.com/users/{username}/contributions"
    resp = requests.get(url, headers={"User-Agent": "profile-readme-bot/1.0"}, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    days = []
    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        # fallback selector used on newer markup
        cells = soup.select("[data-date]")

    for cell in cells:
        date = cell.get("data-date")
        level = cell.get("data-level")
        count = cell.get("data-count") or cell.get("aria-label", "")
        if date is None:
            continue
        if level is None:
            # derive rough level from aria-label text if data-level missing
            m = re.search(r"(\d+)\s+contribution", count or "")
            n = int(m.group(1)) if m else 0
            level = 0 if n == 0 else min(4, (n // 3) + 1)
        days.append({"date": date, "level": int(level)})

    days.sort(key=lambda d: d["date"])
    return days


def derive_stats(days):
    current_streak = 0
    for d in reversed(days):
        if d["level"] > 0:
            current_streak += 1
        else:
            break

    longest_streak = 0
    running = 0
    for d in days:
        if d["level"] > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0

    total = sum(1 for d in days if d["level"] > 0)
    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "active_days": total,
    }


def main():
    days = fetch_days(USERNAME)
    if not days:
        print("No contribution data found — GitHub markup may have changed.", file=sys.stderr)
        sys.exit(1)

    payload = {
        "username": USERNAME,
        "days": days,
        "stats": derive_stats(days),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(days)} days -> {OUT_PATH}")


if __name__ == "__main__":
    main()
