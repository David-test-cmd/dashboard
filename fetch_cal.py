#!/usr/bin/env python3
"""Stahne Google iCal a prevede nejblizsi udalosti na events.json.
ICAL_URL se bere z prostredi (GitHub secret), nikdy se necommituje."""
import os, sys, json, re, urllib.request
from datetime import datetime, timedelta, timezone

URL = os.environ.get("ICAL_URL")
if not URL:
    sys.exit("CHYBA: chybi promenna ICAL_URL")

raw = urllib.request.urlopen(URL, timeout=30).read().decode("utf-8")
# rozbalime folded radky (iCal je lamе po 75 znacich)
raw = raw.replace("\r\n ", "").replace("\n ", "")
raw = raw.replace("\r\n", "\n")

events = []
cur = None
for line in raw.split("\n"):
    if line == "BEGIN:VEVENT":
        cur = {}
    elif line == "END:VEVENT":
        if cur:
            events.append(cur)
        cur = None
    elif cur is not None:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        base = k.split(";")[0]
        if base in ("DTSTART", "DTEND"):
            cur[base] = (v.strip(), ";VALUE=DATE" in k)
        elif base in ("SUMMARY", "LOCATION"):
            cur[base] = v.strip().replace("\\,", ",").replace("\\;", ";")

PRAGUE = timezone(timedelta(hours=2))  # ponytail: CEST pausalne; v zime hodina rozdil, staci

def parse(val):
    v, allday = val
    if allday:
        d = datetime.strptime(v, "%Y%m%d")
        return d, d, True
    d = datetime.strptime(v, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    return d, d, False

today = datetime.now(PRAGUE).date()
horizon = today + timedelta(days=14)

out = []
for e in events:
    if "DTSTART" not in e or "SUMMARY" not in e:
        continue
    try:
        start, _, allday = parse(e["DTSTART"])
        end = parse(e["DTEND"])[0] if "DTEND" in e else start
    except ValueError:
        continue
    if allday:
        sday, eday = start.date(), end.date()
        sday_disp = sday
    else:
        s = start.astimezone(PRAGUE)
        sday, eday = s.date(), end.astimezone(PRAGUE).date()
        sday_disp = s
    # konec je exkluzivni u celych dnu
    last = eday if not allday else eday - timedelta(days=1)
    if last < today or sday > horizon:
        continue
    out.append({
        "date": sday.isoformat(),
        "end": last.isoformat(),
        "allday": allday,
        "time": None if allday else start.astimezone(PRAGUE).strftime("%H:%M"),
        "endtime": None if allday else end.astimezone(PRAGUE).strftime("%H:%M"),
        "title": e["SUMMARY"],
        "loc": e.get("LOCATION", ""),
    })

out.sort(key=lambda x: (x["date"], x["time"] or ""))
json.dump(out, open("events.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"Zapsano {len(out)} udalosti (od {today} do {horizon})")
