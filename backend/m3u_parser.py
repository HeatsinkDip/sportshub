"""
M3U Playlist Parser for IPTV streams.
Fetches from iptv-org sports playlist + main playlist + lupael IPTV,
parses entries, and filters for World Cup broadcast channels.
"""

import re
import httpx
from typing import Optional

# ── Channel whitelist ────────────────────────────────────────────────
# Each: (search_patterns, display_name, category)
# search_patterns is a list of alternative keyword-lists — channel matches if ANY pattern matches
CHANNEL_WHITELIST = [
    # ── FIFA Live (Recommended / Featured) ──
    ([["tapmad", "hd"], ["tapmad"]], "Tapmad HD", "featured"),
    ([["macao", "sport"]], "Macao Sports (FHD)", "featured"),
    ([["bein", "sports", "1"], ["bein", "sport", "1"]], "beIN Sports 1 (Full HD)", "featured"),
    ([["elta", "sport"]], "ELTA Sports (FHD)", "featured"),
    ([["cctv", "5"]], "CCTV 5 (Full HD)", "featured"),
    ([["win", "sports"]], "WIN Sports (Full HD)", "featured"),
    ([["bein", "sports", "türkiye"], ["bein", "sports", "turkiye"], ["bein", "turkey"]], "beIN SPORTS Türkiye", "featured"),
    ([["dazn"]], "DAZN (Full HD)", "featured"),
    ([["d sports"], ["dsports"], ["d-sports"]], "D Sports", "featured"),
    ([["tudn", "canal", "5"], ["tudn", "sports"]], "TUDN Sports - Canal 5 (Full HD)", "featured"),
    ([["tv", "azteca", "7"], ["azteca", "7"], ["tv", "azteca"]], "TV Azteca", "featured"),
    ([["telemundo"]], "Telemundo", "featured"),
    ([["m6", "direct"], ["m6"]], "M6 Direct", "featured"),
    ([["t sports", "hd"], ["t-sports"], ["tsports"]], "T Sports HD", "featured"),
    ([["sports", "18"]], "Sports 18 HD", "featured"),

    # ── Live Channels ──
    ([["fussball"], ["fußball"]], "Fussball.tv1", "live"),
    ([["tsn", "1"], ["tsn", "sports", "1"]], "TSN Sports 1", "live"),
    ([["tudn", "usa"], ["tudn"]], "TUDN", "live"),
    ([["somoy", "tv"]], "Somoy TV", "live"),
    ([["ptv", "sports"]], "PTV Sports", "live"),
    ([["gazi", "tv"], ["gtv"]], "Gazi TV HD", "live"),
    ([["fox", "sports", "1"], ["fox", "sport"]], "FOX Sports 1", "live"),
    ([["bioscope"]], "BIOSCOPE+", "live"),
    ([["caze", "tv"]], "CAZE TV", "live"),
    ([["universo"]], "Universo", "live"),
    ([["bein", "sport", "2"], ["bein", "2"]], "beIN Sports 2", "live"),
    ([["tipik"]], "TIPIK FR", "live"),
    ([["fifa"]], "FIFA TV", "live"),
    ([["supersport"]], "SuperSport", "live"),
    ([["sport", "tv", "1"]], "Sport TV 1", "live"),
    ([["sky", "sport"]], "Sky Sports", "live"),
    ([["espn"]], "ESPN", "live"),
    ([["rtve", "teledeporte"], ["teledeporte"]], "Teledeporte", "live"),
    ([["yes", "tv"]], "YES TV HD", "live"),
    ([["sony", "ten", "1"]], "Sony TEN 1 HD", "live"),
    ([["sony", "ten", "2"]], "Sony TEN 2 HD", "live"),
    ([["sony", "ten", "3"]], "Sony TEN 3", "live"),
    ([["sony", "six"]], "Sony SIX", "live"),
    ([["skynet", "sport"]], "Skynet Sports HD", "live"),
    ([["zee", "bangla"]], "Zee Bangla", "live"),
]


def _normalize(text: str) -> str:
    """Lowercase, strip extra whitespace, remove special chars for matching."""
    text = text.lower().strip()
    # Insert space between English/digits and non-English/non-digits to separate them as words
    text = re.sub(r'([a-zA-Z0-9])([^a-zA-Z0-9\s])', r'\1 \2', text)
    text = re.sub(r'([^a-zA-Z0-9\s])([a-zA-Z0-9])', r'\1 \2', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def _channel_matches(channel_name: str, patterns: list[list[str]]) -> bool:
    """Check if channel_name matches ANY of the keyword patterns using word boundaries."""
    normalized = _normalize(channel_name)
    
    for keyword_list in patterns:
        match_all = True
        for kw in keyword_list:
            norm_kw = _normalize(kw)
            kw_words = norm_kw.split()
            if not kw_words:
                match_all = False
                break
            for word in kw_words:
                pattern = r'\b' + re.escape(word) + r'\b'
                if not re.search(pattern, normalized):
                    match_all = False
                    break
            if not match_all:
                break
        if match_all:
            return True
    return False


def parse_m3u(content: str) -> list[dict]:
    """
    Parse M3U content into a list of channel entries.
    Each entry: {name, logo, group, tvg_id, url, referrer, user_agent, quality}
    """
    entries = []
    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('#EXTINF:'):
            entry = {
                "name": "",
                "logo": "",
                "group": "",
                "tvg_id": "",
                "url": "",
                "referrer": "",
                "user_agent": "",
                "quality": "SD",
            }

            # Extract attributes
            for attr, key in [
                (r'tvg-id="([^"]*)"', "tvg_id"),
                (r'tvg-name="([^"]*)"', "tvg_id"),  # also use tvg-name
                (r'tvg-logo="([^"]*)"', "logo"),
                (r'group-title="([^"]*)"', "group"),
                (r'http-referrer="([^"]*)"', "referrer"),
                (r'http-user-agent="([^"]*)"', "user_agent"),
            ]:
                match = re.search(attr, line)
                if match:
                    entry[key] = match.group(1)

            # Extract channel name (after the last comma)
            name_match = re.search(r',(.+)$', line)
            if name_match:
                entry["name"] = name_match.group(1).strip()

            # Determine quality from name
            name_lower = entry["name"].lower()
            if any(q in name_lower for q in ["1080p", "full hd", "fhd"]):
                entry["quality"] = "FHD"
            elif any(q in name_lower for q in ["720p", "hd"]):
                entry["quality"] = "HD"
            elif any(q in name_lower for q in ["4k", "2160p", "uhd"]):
                entry["quality"] = "4K"
            else:
                entry["quality"] = "SD"

            # Read EXTVLCOPT lines and URL
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if next_line.startswith('#EXTVLCOPT:http-referrer='):
                    entry["referrer"] = next_line.split('=', 1)[1]
                    i += 1
                elif next_line.startswith('#EXTVLCOPT:http-user-agent='):
                    entry["user_agent"] = next_line.split('=', 1)[1]
                    i += 1
                elif next_line.startswith('#'):
                    i += 1
                else:
                    break

            # URL line
            if i < len(lines):
                url_line = lines[i].strip()
                if url_line and not url_line.startswith('#'):
                    entry["url"] = url_line
                    entries.append(entry)

        i += 1

    return entries


def filter_worldcup_channels(all_channels: list[dict]) -> list[dict]:
    """Filter and group channels matching our World Cup whitelist."""
    grouped: dict[str, dict] = {}

    for channel in all_channels:
        for patterns, display_name, category in CHANNEL_WHITELIST:
            if _channel_matches(channel["name"], patterns):
                key = display_name

                if key not in grouped:
                    grouped[key] = {
                        "id": _normalize(display_name).replace(" ", "_"),
                        "name": display_name,
                        "category": category,
                        "logo": channel["logo"],
                        "quality": channel["quality"],
                        "servers": [],
                    }

                # Add this stream as a server
                server = {
                    "url": channel["url"],
                    "name": channel["name"],
                    "quality": channel["quality"],
                    "referrer": channel["referrer"],
                    "user_agent": channel["user_agent"],
                }

                existing_urls = [s["url"] for s in grouped[key]["servers"]]
                if channel["url"] not in existing_urls:
                    grouped[key]["servers"].append(server)

                # Prefer logo
                if channel["logo"] and not grouped[key]["logo"]:
                    grouped[key]["logo"] = channel["logo"]

                # Upgrade quality
                qr = {"SD": 0, "HD": 1, "FHD": 2, "4K": 3}
                if qr.get(channel["quality"], 0) > qr.get(grouped[key]["quality"], 0):
                    grouped[key]["quality"] = channel["quality"]

                break

    # Sort: featured first, then by name
    result = list(grouped.values())
    result.sort(key=lambda c: (0 if c["category"] == "featured" else 1, c["name"]))
    return result


# ── Global cache ─────────────────────────────────────────────────────
_cached_channels: list[dict] = []


async def fetch_and_parse_m3u() -> list[dict]:
    """Fetch M3U playlists (sports + main + lupael) and return filtered World Cup channels."""
    global _cached_channels

    all_channels = []
    urls = [
        "https://iptv-org.github.io/iptv/categories/sports.m3u",
        "https://iptv-org.github.io/iptv/index.m3u",
        "https://lupael.github.io/IPTV/running.m3u",
        "https://lupael.github.io/IPTV/world.m3u",
        "https://github.com/abusaeeidx/Mrgify-BDIX-IPTV/raw/main/playlist.m3u",
    ]

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            for url in urls:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    parsed = parse_m3u(resp.text)
                    all_channels.extend(parsed)
                    print(f"[M3U] Parsed {len(parsed)} channels from {url.split('/')[-1]}")
                except Exception as e:
                    print(f"[M3U] Error fetching {url}: {e}")

        _cached_channels = filter_worldcup_channels(all_channels)
        print(f"[M3U] Total: {len(all_channels)} → {len(_cached_channels)} World Cup channels matched")

    except Exception as e:
        print(f"[M3U] Error: {e}")
        if not _cached_channels:
            _cached_channels = []

    return _cached_channels


def get_cached_channels() -> list[dict]:
    return _cached_channels
