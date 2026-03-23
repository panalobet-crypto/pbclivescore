"""
Run this ONCE to print all league IDs from your AllSportsAPI subscription.
Usage:  CRICKET_API_KEY=xxx python find_leagues.py [keyword]
Example: python find_leagues.py ipl
         python find_leagues.py bangladesh
"""
import sys
import os
import httpx

key = os.environ.get("CRICKET_API_KEY") or input("Enter API key: ").strip()
keyword = sys.argv[1].lower() if len(sys.argv) > 1 else ""

r = httpx.get(
    "https://apiv2.allsportsapi.com/cricket/",
    params={"met": "Leagues", "APIkey": key},
)
data = r.json()

leagues = data.get("result") or []
print(f"Total leagues in subscription: {len(leagues)}\n")
print(f"{'ID':<10} {'Year':<12} Name")
print("-" * 60)
for lg in leagues:
    name = lg.get("league_name", "")
    if keyword and keyword not in name.lower():
        continue
    print(f"{lg['league_key']:<10} {lg.get('league_year',''):<12} {name}")
