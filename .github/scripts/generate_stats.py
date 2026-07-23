#!/usr/bin/env python3
"""Generate dependency-free SVG cards from GitHub's public REST API."""

from __future__ import annotations

import html
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

API = "https://api.github.com"
USERNAME = os.environ.get("PROFILE_USERNAME", "").strip()
TOKEN = os.environ.get("GH_TOKEN", "").strip()
OUTPUT = Path("assets")

if not USERNAME:
    raise SystemExit("PROFILE_USERNAME is missing")

OUTPUT.mkdir(parents=True, exist_ok=True)


def request_json(url: str, *, retry_without_token: bool = True) -> tuple[Any, dict[str, str]]:
    """Fetch JSON; retry public endpoints anonymously if token access is restricted."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": f"{USERNAME}-profile-stats-workflow",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body, dict(response.headers.items())
    except urllib.error.HTTPError as error:
        if TOKEN and retry_without_token and error.code in {401, 403, 404}:
            public_headers = {k: v for k, v in headers.items() if k != "Authorization"}
            public_request = urllib.request.Request(url, headers=public_headers)
            with urllib.request.urlopen(public_request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
                return body, dict(response.headers.items())
        message = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed ({error.code}): {message}") from error


def get_all_repositories() -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {
                "type": "owner",
                "sort": "updated",
                "direction": "desc",
                "per_page": 100,
                "page": page,
            }
        )
        batch, _ = request_json(f"{API}/users/{urllib.parse.quote(USERNAME)}/repos?{query}")
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected repositories response from GitHub")
        repos.extend(batch)
        if len(batch) < 100:
            return repos
        page += 1


def get_language_totals(repos: list[dict[str, Any]]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    # Forks are excluded so copied code does not dominate the language chart.
    owned = [repo for repo in repos if not repo.get("fork") and not repo.get("archived")]
    for index, repo in enumerate(owned, start=1):
        url = repo.get("languages_url")
        if not url:
            continue
        try:
            languages, _ = request_json(str(url))
        except Exception as exc:  # One unavailable repository must not break the whole profile.
            print(f"Warning: skipped languages for {repo.get('full_name')}: {exc}")
            continue
        if isinstance(languages, dict):
            for language, amount in languages.items():
                if isinstance(amount, int) and amount > 0:
                    totals[str(language)] += amount
        if index % 20 == 0:
            time.sleep(0.15)
    return dict(totals)


def compact_number(number: int) -> str:
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M".replace(".0M", "M")
    if number >= 1_000:
        return f"{number / 1_000:.1f}k".replace(".0k", "k")
    return str(number)


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def write_stats_card(user: dict[str, Any], repos: list[dict[str, Any]]) -> None:
    stars = sum(int(repo.get("stargazers_count") or 0) for repo in repos)
    forks = sum(int(repo.get("forks_count") or 0) for repo in repos)
    metrics = [
        ("Public Repositories", int(user.get("public_repos") or len(repos)), "▣"),
        ("Followers", int(user.get("followers") or 0), "●"),
        ("Total Stars", stars, "★"),
        ("Repository Forks", forks, "⑂"),
    ]
    display_name = user.get("name") or user.get("login") or USERNAME
    login = user.get("login") or USERNAME

    metric_svg = []
    positions = [(28, 92), (255, 92), (28, 146), (255, 146)]
    for (label, value, icon), (x, y) in zip(metrics, positions):
        metric_svg.append(
            f'<text x="{x}" y="{y}" class="icon">{escape(icon)}</text>'
            f'<text x="{x + 24}" y="{y}" class="value">{escape(compact_number(value))}</text>'
            f'<text x="{x + 92}" y="{y}" class="label">{escape(label)}</text>'
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-label="Public GitHub Overview for {escape(login)}">
  <title>Public GitHub Overview for {escape(login)}</title>
  <style>
    .bg {{ fill: #1a1b27; stroke: #30363d; stroke-width: 1; }}
    .title {{ fill: #70a5fd; font: 700 20px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; }}
    .subtitle {{ fill: #38bdae; font: 400 12px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; }}
    .value {{ fill: #bf91f3; font: 700 17px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; }}
    .label {{ fill: #c9d1d9; font: 400 13px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; }}
    .icon {{ fill: #70a5fd; font: 700 17px -apple-system,BlinkMacSystemFont,'Segoe UI Symbol','Segoe UI',sans-serif; }}
    .note {{ fill: #8b949e; font: 400 10px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; }}
  </style>
  <rect class="bg" x="0.5" y="0.5" rx="10" width="494" height="194"/>
  <text x="25" y="36" class="title">{escape(display_name)}</text>
  <text x="25" y="57" class="subtitle">@{escape(login)} · Public GitHub Overview</text>
  {''.join(metric_svg)}
  <text x="25" y="180" class="note">Generated directly from GitHub public repository data</text>
</svg>
'''
    (OUTPUT / "github-stats.svg").write_text(svg, encoding="utf-8")


LANGUAGE_COLORS = {
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Python": "#3572A5",
    "C#": "#178600",
    "C++": "#f34b7d",
    "C": "#555555",
    "Java": "#b07219",
    "PHP": "#4F5D95",
    "Shell": "#89e051",
    "Dart": "#00B4AB",
    "Kotlin": "#A97BFF",
    "Swift": "#F05138",
    "Ruby": "#701516",
    "Go": "#00ADD8",
    "Vue": "#41b883",
}
FALLBACK_COLORS = ["#70a5fd", "#bf91f3", "#38bdae", "#ff7b72", "#f2cc60", "#a5d6ff"]


def write_languages_card(language_totals: dict[str, int]) -> None:
    ordered = sorted(language_totals.items(), key=lambda item: item[1], reverse=True)[:6]
    total = sum(amount for _, amount in ordered)
    if total <= 0:
        ordered = [("No language data", 1)]
        total = 1

    bar_x, bar_y, bar_width = 25.0, 62.0, 445.0
    current_x = bar_x
    bar_parts = []
    rows = []

    for index, (language, amount) in enumerate(ordered):
        percent = (amount / total) * 100
        width = bar_width * amount / total
        color = LANGUAGE_COLORS.get(language, FALLBACK_COLORS[index % len(FALLBACK_COLORS)])
        rx = 5 if index in {0, len(ordered) - 1} else 0
        bar_parts.append(
            f'<rect x="{current_x:.2f}" y="{bar_y}" width="{max(width, 1):.2f}" height="9" rx="{rx}" fill="{color}"/>'
        )
        current_x += width

        column = index % 2
        row = index // 2
        x = 27 + column * 228
        y = 101 + row * 28
        rows.append(
            f'<circle cx="{x + 5}" cy="{y - 4}" r="5" fill="{color}"/>'
            f'<text x="{x + 17}" y="{y}" class="lang">{escape(language)}</text>'
            f'<text x="{x + 190}" y="{y}" text-anchor="end" class="percent">{percent:.1f}%</text>'
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-label="Most Used Languages for {escape(USERNAME)}">
  <title>Most Used Languages for {escape(USERNAME)}</title>
  <style>
    .bg {{ fill: #1a1b27; stroke: #30363d; stroke-width: 1; }}
    .title {{ fill: #70a5fd; font: 700 20px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; }}
    .lang {{ fill: #c9d1d9; font: 500 12px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; }}
    .percent {{ fill: #38bdae; font: 500 11px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; }}
    .note {{ fill: #8b949e; font: 400 10px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; }}
  </style>
  <rect class="bg" x="0.5" y="0.5" rx="10" width="494" height="194"/>
  <text x="25" y="36" class="title">Most Used Languages</text>
  {''.join(bar_parts)}
  {''.join(rows)}
  <text x="25" y="181" class="note">Calculated from non-fork, non-archived public repositories</text>
</svg>
'''
    (OUTPUT / "top-languages.svg").write_text(svg, encoding="utf-8")


def main() -> None:
    user, _ = request_json(f"{API}/users/{urllib.parse.quote(USERNAME)}")
    if not isinstance(user, dict):
        raise RuntimeError("Unexpected user response from GitHub")
    repos = get_all_repositories()
    languages = get_language_totals(repos)
    write_stats_card(user, repos)
    write_languages_card(languages)
    print(f"Generated cards for {USERNAME} from {len(repos)} public repositories.")


if __name__ == "__main__":
    main()
