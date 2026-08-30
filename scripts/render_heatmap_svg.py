"""
Render data/contributions.json as a 53x7 animated SVG calendar.
Rounded boxes, GitHub-style green ramp, diagonal slide-down reveal via
CSS keyframes (no JS — GitHub sanitizes <script> in READMEs but plays
CSS animations and SMIL inside embedded SVGs).
"""
import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "contributions.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "contrib-heatmap.svg"

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
CELL = 11
GAP = 3
PAD = 20
COLS = 53
ROWS = 7


def build_grid(days):
    grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
    if not days:
        return grid
    from datetime import datetime

    parsed = [(datetime.fromisoformat(d["date"]), d["level"]) for d in days]
    parsed.sort(key=lambda x: x[0])
    total_days = len(parsed)
    col = COLS - 1
    idx = total_days - 1
    while idx >= 0 and col >= 0:
        date, level = parsed[idx]
        r = (date.weekday() + 1) % 7
        grid[r][col] = level
        idx -= 1
        if r == 0:
            col -= 1
    return grid


def main():
    payload = json.loads(DATA_PATH.read_text())
    grid = build_grid(payload["days"])

    width = PAD * 2 + COLS * (CELL + GAP)
    height = PAD * 2 + ROWS * (CELL + GAP)

    svg_parts = []
    svg_parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )
    svg_parts.append(f'<rect width="{width}" height="{height}" fill="#0d1117"/>')
    svg_parts.append("<style>")
    svg_parts.append(
        """
        .cell { opacity: 0; transform: translateY(-6px); animation: reveal 0.4s ease forwards; }
        @keyframes reveal { to { opacity: 1; transform: translateY(0); } }
        """
    )
    svg_parts.append("</style>")

    delay_step = 0.012
    for c in range(COLS):
        for r in range(ROWS):
            level = grid[r][c]
            if level is None:
                continue
            color = PALETTE[min(level, len(PALETTE) - 1)]
            x = PAD + c * (CELL + GAP)
            y = PAD + r * (CELL + GAP)
            delay = (c + r) * delay_step
            svg_parts.append(
                f'<rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2" ry="2" fill="{color}" style="animation-delay:{delay:.3f}s"/>'
            )

    svg_parts.append("</svg>")
    OUT_PATH.write_text("\n".join(svg_parts))
    print(f"Wrote heatmap -> {OUT_PATH}")


if __name__ == "__main__":
    main()
