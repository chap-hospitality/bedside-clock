"""Fetch latest PM2.5 for all Air4Thai (PCD) stations and write a small air.json.

Runs on GitHub Actions so the phone never calls Air4Thai directly
(Air4Thai is HTTP-only / no CORS, which an HTTPS page on iOS 10 cannot use).
"""
import json
import sys
import time
import urllib.request

URLS = [
    "http://air4thai.pcd.go.th/services/getNewAQI_JSON.php",
    "https://air4thai.pcd.go.th/services/getNewAQI_JSON.php",
]


def fetch():
    last = None
    for url in URLS:
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "bedside-clock/1.0"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read().decode("utf-8-sig")), url
            except Exception as e:  # noqa: BLE001
                last = e
                print(f"fail {url} try {attempt + 1}: {e}", file=sys.stderr)
                time.sleep(5)
    raise SystemExit(f"Air4Thai unreachable: {last}")


def num(v):
    try:
        f = float(v)
        return f if f >= 0 else None
    except (TypeError, ValueError):
        return None


def main():
    data, used = fetch()
    out = []
    for s in data.get("stations", []):
        last = s.get("AQILast") or {}
        pm = num((last.get("PM25") or {}).get("value"))
        lat, lon = num(s.get("lat")), num(s.get("long"))
        if pm is None or lat is None or lon is None:
            continue
        out.append({
            "id": s.get("stationID"),
            "n": s.get("nameTH") or s.get("nameEN"),
            "a": s.get("areaTH") or s.get("areaEN"),
            "lat": round(lat, 4), "lon": round(lon, 4),
            "pm": pm,
            "t": f"{last.get('date', '')} {last.get('time', '')}".strip(),
        })
    if not out:
        print(json.dumps(data, ensure_ascii=False)[:1500], file=sys.stderr)
        raise SystemExit("No stations with PM2.5 in response")
    with open("air.json", "w", encoding="utf-8") as f:
        json.dump({"src": "Air4Thai (PCD)", "fetched": int(time.time()), "stations": out},
                  f, ensure_ascii=False, separators=(",", ":"))
    print(f"OK {len(out)} stations from {used}")


if __name__ == "__main__":
    main()
