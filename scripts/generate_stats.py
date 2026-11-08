#!/usr/bin/env python3
"""Generate a dependency-free SVG dashboard from the GitHub GraphQL API."""
from __future__ import annotations
import datetime as dt
import html
import json
import os
import pathlib
import urllib.request

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "daminebenq")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
QUERY = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC) { totalCount }
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar { totalContributions weeks { contributionDays { contributionCount date } } }
    }
  }
}
"""

def fetch():
    now = dt.datetime.now(dt.timezone.utc)
    variables = {"login": USER, "from": (now-dt.timedelta(days=364)).isoformat(), "to": now.isoformat()}
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": QUERY, "variables": variables}).encode(), headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "profile-stats-generator"})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"): raise RuntimeError(payload["errors"])
    return payload["data"]["user"], now

def generate(user, now):
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"][-52:] for d in w["contributionDays"]]
    max_count = max([d["contributionCount"] for d in days] or [1])
    metrics = [("CONTRIBUTIONS", cal["totalContributions"]), ("PUBLIC REPOS", user["repositories"]["totalCount"]), ("PULL REQUESTS", user["pullRequests"]["totalCount"]), ("FOLLOWERS", user["followers"]["totalCount"])]
    cards=[]
    for i,(label,value) in enumerate(metrics):
        x=36+i*235
        cards.append(f'''<g transform="translate({x} 38)" class="card" style="animation-delay:{i*.12}s"><rect width="210" height="88" rx="13" fill="#111827" stroke="#26334a"/><text x="18" y="35" class="value">{value:,}</text><text x="18" y="64" class="label">{label}</text></g>''')
    # Recent 16 weeks, seven bars per week. SVG remains readable at profile width.
    recent=days[-112:]
    bars=[]
    for i,d in enumerate(recent):
        week=i//7; dow=i%7; h=max(2, round(38*d["contributionCount"]/max_count)); x=47+week*56+dow*6; y=216-h
        color="#22d3ee" if d["contributionCount"] else "#1e293b"
        bars.append(f'<rect x="{x}" y="{y}" width="4" height="{h}" rx="2" fill="{color}" opacity="{0.4 + 0.6*d["contributionCount"]/max_count:.2f}"><title>{html.escape(d["date"])}: {d["contributionCount"]} contributions</title><animate attributeName="height" from="0" to="{h}" dur=".7s" begin="{i*.008:.3f}s" fill="freeze"/><animate attributeName="y" from="216" to="{y}" dur=".7s" begin="{i*.008:.3f}s" fill="freeze"/></rect>')
    updated=now.strftime("%d %b %Y")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="265" viewBox="0 0 1000 265" role="img" aria-labelledby="title desc">
<title id="title">GitHub activity dashboard for {html.escape(USER)}</title><desc id="desc">{cal['totalContributions']} contributions in the past year, {user['repositories']['totalCount']} public repositories, {user['pullRequests']['totalCount']} pull requests, and {user['followers']['totalCount']} followers. Updated {updated}.</desc>
<style>.value{{fill:#f8fafc;font:700 29px Inter,Segoe UI,sans-serif}}.label{{fill:#94a3b8;font:600 12px Inter,Segoe UI,sans-serif;letter-spacing:1.5px}}.small{{fill:#64748b;font:12px Inter,Segoe UI,sans-serif}}.card{{opacity:0;animation:fade .6s ease forwards}}@keyframes fade{{to{{opacity:1}}}}</style>
<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#080c18"/><stop offset="1" stop-color="#0d1725"/></linearGradient></defs><rect width="1000" height="265" rx="18" fill="url(#bg)"/><g>{''.join(cards)}</g><text x="36" y="168" class="label">RECENT ACTIVITY • LAST 16 WEEKS</text><text x="964" y="168" text-anchor="end" class="small">Updated {updated}</text><line x1="36" y1="226" x2="964" y2="226" stroke="#26334a"/>{''.join(bars)}<rect x="1" y="1" width="998" height="263" rx="17" fill="none" stroke="#26334a"/></svg>'''

if __name__ == "__main__":
    user, now = fetch()
    pathlib.Path("assets/stats.svg").write_text(generate(user, now), encoding="utf-8")
