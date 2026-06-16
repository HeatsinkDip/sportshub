"""
M3U Playlist Parser for IPTV streams.
Fetches from iptv-org sports playlist + main playlist + lupael IPTV,
parses entries, and filters for World Cup broadcast channels.
"""

import asyncio
import os
import json
import re
import httpx
from typing import Optional

# ── Channel whitelist ────────────────────────────────────────────────
# Each: (search_patterns, display_name, category)
# search_patterns is a list of alternative keyword-lists — channel matches if ANY pattern matches
CHANNEL_WHITELIST = [
    # ── FIFA Live (Recommended / Featured) ──
    ([["d sports"], ["dsports"], ["d-sports"]], "D Sports", "featured"),
    ([["t sports", "hd"], ["t-sports"], ["tsports"]], "T Sports HD", "featured"),
    ([["somoy", "tv"]], "Somoy TV", "featured"),
    ([["ptv", "sports"]], "PTV Sports", "featured"),

    # ── Live Channels ──
    ([["tapmad", "hd"], ["tapmad"]], "Tapmad HD", "live"),
    ([["macao", "sport"]], "Macao Sports (FHD)", "live"),
    ([["bein", "sports", "1"], ["bein", "sport", "1"]], "beIN Sports 1 (Full HD)", "live"),
    ([["elta", "sport"]], "ELTA Sports (FHD)", "live"),
    ([["cctv", "5"]], "CCTV 5 (Full HD)", "live"),
    ([["win", "sports"]], "WIN Sports (Full HD)", "live"),
    ([["bein", "sports", "türkiye"], ["bein", "sports", "turkiye"], ["bein", "turkey"]], "beIN SPORTS Türkiye", "live"),
    ([["dazn"]], "DAZN (Full HD)", "live"),
    ([["tudn", "canal", "5"], ["tudn", "sports"]], "TUDN Sports - Canal 5 (Full HD)", "live"),
    ([["tv", "azteca", "7"], ["azteca", "7"], ["tv", "azteca"]], "TV Azteca", "live"),
    ([["telemundo"]], "Telemundo", "live"),
    ([["m6", "direct"], ["m6"]], "M6 Direct", "live"),
    ([["sports", "18"]], "Sports 18 HD", "live"),
    
    ([["tsn", "1"], ["tsn", "sports", "1"]], "TSN Sports 1", "live"),
    ([["tudn", "usa"], ["tudn"]], "TUDN", "live"),
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
    ([["cola", "tv"], ["colatv"]], "ColaTV", "live"),
    ([["trt", "1"]], "TRT 1", "live"),
    ([["fussball", "1"], ["fussball", "tv", "1"], ["fußball", "1"]], "Fussball TV 1", "featured"),
    ([["fussball", "2"], ["fussball", "tv", "2"], ["fußball", "2"]], "Fussball TV 2", "featured"),
]

# Fallback / accurate online logos for channels
CHANNEL_LOGOS = {
    "cctv_5_full_hd_": "https://upload.wikimedia.org/wikipedia/commons/d/d3/CCTVNewLogo.svg",
    "elta_sports_fhd_": "https://upload.wikimedia.org/wikipedia/commons/5/5b/ELTA_logo.svg",
    "macao_sports_fhd_": "https://static.wikia.nocookie.net/logopedia/images/2/2c/TDMSport.png",
    "colatv": "https://colatv.app/favicon.png",
}



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
                "license_type": "",
                "license_key": "",
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

            # Read EXTVLCOPT and KODIPROP lines and URL
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if next_line.startswith('#EXTVLCOPT:http-referrer='):
                    entry["referrer"] = next_line.split('=', 1)[1]
                    i += 1
                elif next_line.startswith('#EXTVLCOPT:http-user-agent='):
                    entry["user_agent"] = next_line.split('=', 1)[1]
                    i += 1
                elif next_line.startswith('#KODIPROP:'):
                    opt_part = next_line.split(':', 1)[1]
                    if '=' in opt_part:
                        k, v = opt_part.split('=', 1)
                        k = k.strip()
                        v = v.strip()
                        if 'license_type' in k:
                            entry["license_type"] = v
                        elif 'license_key' in k:
                            entry["license_key"] = v
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
                    "license_type": channel.get("license_type", ""),
                    "license_key": channel.get("license_key", ""),
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


async def fetch_single_m3u(client: httpx.AsyncClient, url: str) -> list[dict]:
    """Fetch and parse a single M3U URL with raw GitHub URL conversion."""
    raw_url = url
    if "github.com" in url:
        if "/blob/" in url:
            raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        elif "/raw/" in url:
            raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/raw/", "/")

    try:
        resp = await client.get(raw_url, timeout=15.0)
        resp.raise_for_status()
        parsed = parse_m3u(resp.text)
        print(f"[M3U] Parsed {len(parsed)} channels from {url.split('/')[-1]}")
        return parsed
    except Exception as e:
        print(f"[M3U] Error fetching {url}: {e}")
        return []


async def is_server_working(client: httpx.AsyncClient, server: dict) -> bool:
    """Validate if a stream URL is working. Private IPs and BDIX streams bypass checks."""
    url = server["url"]
    
    # 1. Skip local/BDIX URLs as they won't resolve on a public cloud server
    try:
        # Bypass validation for user-verified stream URLs to prevent them from being dropped
        user_verified_keywords = [
            "exmax.workers.dev",
            "het4444.ycn-redirect.com",
            "d1g8wgjurz8via.cloudfront.net",
            "dfr80qz435crc.cloudfront.net",
            "thebosstv.com",
            "tsports",
            "180.94.28.28",
            "zohanayaan.com",
            "t-online.de",
            "streamhostingcdn.top",
            "szyac.com",
            "msdht.app",
            "medya.trt.com.tr"
        ]
        if any(kw in url for kw in user_verified_keywords):
            return True

        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname.lower() if parsed.hostname else ""
        if (
            host == "localhost"
            or host == "127.0.0.1"
            or host.startswith("10.")
            or host.startswith("192.168.")
            or "bdix" in host
            or "bdix" in url.lower()
        ):
            return True
            
        parts = host.split(".")
        if len(parts) == 4:
            first = int(parts[0])
            second = int(parts[1])
            if first == 172 and 16 <= second <= 31:
                return True
    except Exception:
        pass

    # 2. Perform a fast GET stream request for public streams
    headers = {
        "User-Agent": server.get("user_agent") or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    }
    if server.get("referrer"):
        headers["Referer"] = server["referrer"]

    try:
        # Check connection and read the first chunk to filter out HTML error/parking pages
        async with client.stream("GET", url, headers=headers, timeout=4.0) as resp:
            if resp.status_code >= 400:
                return False
                
            content_type = resp.headers.get("content-type", "").lower()
            
            first_chunk = b""
            async for chunk in resp.aiter_bytes(chunk_size=512):
                first_chunk = chunk
                break
                
            if not first_chunk:
                return False
                
            first_chunk_text = first_chunk.decode("utf-8", errors="ignore").strip()
            
            # If it is an HLS playlist, it must start with #EXTM3U
            if ".m3u8" in url.lower() or "mpegurl" in content_type:
                return first_chunk_text.startswith("#EXTM3U")
                
            # If it is DASH, it must contain <MPD or <Period or <xml
            if ".mpd" in url.lower() or "xml" in content_type:
                return "<MPD" in first_chunk_text or "<Period" in first_chunk_text or "<xml" in first_chunk_text or "<MPD" in first_chunk_text.upper()
                
            # If it is an HTML landing page (but URL was supposed to be a stream), it's dead
            if "html" in first_chunk_text.lower() and ("<!doctype html" in first_chunk_text.lower() or "<html" in first_chunk_text.lower()):
                return False
                
            return True
    except Exception:
        return False


def apply_server_and_category_overrides(channels: list[dict]) -> list[dict]:
    """
    Applies manual user overrides to categories, server order, and server filtering.
    """
    modified_channels = []
    for chan in channels:
        # Create a copy to avoid in-place modification of mutable objects if reused
        chan_copy = dict(chan)
        cid = chan_copy["id"]
        
        # 1. PTV Sports (ptv_sports)
        # Category: featured. Keep both working servers (zohanayaan.com and second), remove only dead 119.156.228.231.
        if cid == "ptv_sports":
            chan_copy["category"] = "featured"
            filtered = [s for s in chan_copy["servers"] if "119.156.228.231" not in s["url"]]
            s_zohan = [s for s in filtered if "zohanayaan.com" in s["url"]]
            s_others = [s for s in filtered if "zohanayaan.com" not in s["url"]]
            chan_copy["servers"] = s_zohan + s_others
        
        # 2. Somoy TV (somoy_tv)
        # Category: featured. Remove bozztv, toffee, and gpcdn.net. Prioritize thebosstv.com first.
        elif cid == "somoy_tv":
            chan_copy["category"] = "featured"
            filtered_servers = [
                s for s in chan_copy["servers"] 
                if "bozztv.com" not in s["url"] and "toffee/play/somoy_tv" not in s["url"] and "gpcdn.net" not in s["url"]
            ]
            s_top = [s for s in filtered_servers if "thebosstv.com" in s["url"]]
            s_others = [s for s in filtered_servers if "thebosstv.com" not in s["url"]]
            chan_copy["servers"] = s_top + s_others
            
        # 3. beIN Sports 1 (bein_sports_1_full_hd_)
        # Category: featured (Fifa live). Make server 2 (containing "het4444.ycn-redirect.com") default.
        elif cid == "bein_sports_1_full_hd_":
            chan_copy["category"] = "featured"
            target = [s for s in chan_copy["servers"] if "het4444.ycn-redirect.com" in s["url"]]
            others = [s for s in chan_copy["servers"] if "het4444.ycn-redirect.com" not in s["url"]]
            chan_copy["servers"] = target + others
            
        # 4. Zee Bangla (zee_bangla)
        # Category: featured (Fifa live). Keep server containing ColorsHD only.
        elif cid == "zee_bangla":
            chan_copy["category"] = "featured"
            chan_copy["servers"] = [s for s in chan_copy["servers"] if "ColorsHD" in s["url"]]
            
        # 5. DAZN (dazn_full_hd_)
        # Category: featured (Fifa live). Custom URL will be made default in inject_custom_channels.
        elif cid == "dazn_full_hd_":
            chan_copy["category"] = "featured"
            
        # 6. CAZE TV (caze_tv)
        # Category: featured (Fifa live). Make server 3 (containing "dfr80qz435crc.cloudfront.net") default, remove others.
        elif cid == "caze_tv":
            chan_copy["category"] = "featured"
            chan_copy["servers"] = [s for s in chan_copy["servers"] if "dfr80qz435crc.cloudfront.net" in s["url"]]
            
        # 7. T Sports HD (t_sports_hd)
        # Category: featured. Keep only index.m3u8 and tracks-v1a1/mono.m3u8 working servers.
        elif cid == "t_sports_hd":
            chan_copy["category"] = "featured"
            s1 = [s for s in chan_copy["servers"] if "/tsports/index.m3u8" in s["url"]]
            s2 = [s for s in chan_copy["servers"] if "/tsports/tracks-v1a1/mono.m3u8" in s["url"]]
            chan_copy["servers"] = s1 + s2
            
        # 8. D Sports (d_sports)
        # Category: featured. Remove otte servers. Custom URL will be made default in inject_custom_channels.
        elif cid == "d_sports":
            chan_copy["category"] = "featured"
            chan_copy["servers"] = [
                s for s in chan_copy["servers"]
                if "otte.live.fly.ww.aiv-cdn.net" not in s["url"]
            ]
            
        elif cid in ["fussball_tv_1", "fussball_tv_2"]:
            chan_copy["category"] = "featured"

        if chan_copy["servers"]:
            modified_channels.append(chan_copy)
            
    # Sort featured first, then by name
    modified_channels.sort(key=lambda c: (0 if c["category"] == "featured" else 1, c["name"]))
    return modified_channels


# ── Custom hardcoded channels (user-verified URLs) ──────────────────
CUSTOM_CHANNEL_SERVERS = {
    # channel_id: (display_name, category, quality, [server_dicts])
    # Set all custom channels to featured (Fifa Live section)
    "win_sports_full_hd_": ("WIN Sports (Full HD)", "featured", "FHD", [
        {"url": "https://1nyaler.streamhostingcdn.top/stream/32/index.m3u8", "name": "Win Sports Custom", "quality": "FHD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),
    "cctv_5_full_hd_": ("CCTV 5 (Full HD)", "featured", "FHD", [
        {"url": "https://live12.szyac.com/live/35291799.m3u8", "name": "CCTV Custom", "quality": "FHD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),
    "elta_sports_fhd_": ("ELTA Sports (FHD)", "featured", "FHD", [
        {"url": "https://live12.szyac.com/live/22457616.m3u8", "name": "ELTA Sports Custom", "quality": "FHD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),
    "macao_sports_fhd_": ("Macao Sports (FHD)", "featured", "FHD", [
        {"url": "https://live12.szyac.com/live/09139583.m3u8", "name": "Macao Sports Custom", "quality": "FHD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),
    "dazn_full_hd_": ("DAZN (Full HD)", "featured", "FHD", [
        {"url": "https://1nyaler.streamhostingcdn.top/stream/94/index.m3u8", "name": "DAZN Custom", "quality": "FHD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),
    "d_sports": ("D Sports", "featured", "FHD", [
        {"url": "https://1nyaler.streamhostingcdn.top/stream/106/index.m3u8", "name": "D Sports Custom", "quality": "FHD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),
    "tudn": ("TUDN", "featured", "FHD", [
        {"url": "https://1nyaler.streamhostingcdn.top/stream/52/index.m3u8", "name": "TUDN Custom", "quality": "FHD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),
    "colatv": ("ColaTV", "featured", "FHD", [
        {"url": "https://live05.msdht.app/live/24561735.m3u8", "name": "ColaTV Custom", "quality": "FHD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),
    "trt_1": ("TRT 1", "featured", "FHD", [
        {"url": "https://tv-trt1.medya.trt.com.tr/master_1440.m3u8", "name": "TRT 1 Custom", "quality": "FHD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),
    "somoy_tv": ("Somoy TV", "featured", "HD", [
        {"url": "https://live.thebosstv.com:30443/dwlive/Somoy-TV/chunks.m3u8", "name": "Somoy TV Custom", "quality": "HD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),
}


def inject_custom_channels(channels: list[dict]) -> list[dict]:
    """Inject user-verified custom channel URLs as priority (first) servers."""
    for cid, (name, category, quality, servers) in CUSTOM_CHANNEL_SERVERS.items():
        existing = next((c for c in channels if c["id"] == cid), None)
        if existing:
            existing["category"] = category  # Override category (e.g., to featured/FIFA Live)
            for srv in reversed(servers):
                urls = [s["url"] for s in existing["servers"]]
                if srv["url"] in urls:
                    idx = urls.index(srv["url"])
                    existing["servers"].insert(0, existing["servers"].pop(idx))
                else:
                    existing["servers"].insert(0, srv)  # Insert as default
        else:
            channels.append({
                "id": cid,
                "name": name,
                "category": category,
                "logo": "",
                "quality": quality,
                "servers": list(servers),
            })
    # Re-sort: featured first, then by name
    channels.sort(key=lambda c: (0 if c["category"] == "featured" else 1, c["name"]))
    return channels


async def fetch_and_parse_m3u() -> list[dict]:
    """Fetch M3U playlists in parallel, filter, and validate them."""
    global _cached_channels

    all_channels = []
    urls = [
        "https://iptv-org.github.io/iptv/categories/sports.m3u",
        "https://iptv-org.github.io/iptv/index.m3u",
        "https://lupael.github.io/IPTV/running.m3u",
        "https://lupael.github.io/IPTV/world.m3u",
        "https://github.com/abusaeeidx/Mrgify-BDIX-IPTV/raw/main/playlist.m3u",
        "https://raw.githubusercontent.com/abusaeeidx/Yupptv-Playlist/refs/heads/main/playlist.m3u",
        "https://github.com/abusaeeidx/BDxTV/blob/main/playlist_s.m3u",
        "https://github.com/abusaeeidx/BDxTV/blob/main/channels_pl2.m3u",
        "https://raw.githubusercontent.com/abusaeeidx/CricHd-playlists-Auto-Update-permanent/refs/heads/main/ALL.m3u",
        "https://raw.githubusercontent.com/abusaeeidx/CricHd-playlists-Auto-Update-permanent/refs/heads/main/playlist.m3u",
        "https://github.com/sm-monirulislam/SM-Live-TV/blob/main/World_Cup.m3u",
        "https://github.com/sm-monirulislam/SM-Live-TV/blob/main/Combined_Live_TV.m3u",
        "https://github.com/sm-monirulislam/SM-Live-TV/blob/main/All_Live_HD_Sports_Channels.m3u",
        "https://raw.githubusercontent.com/sm-monirulislam/SM-Live-TV/refs/heads/main/All_Live_HD_Sports_Channels.m3u",
        "https://raw.githubusercontent.com/sm-monirulislam/SM-Live-TV/refs/heads/main/Combined_Live_TV.m3u",
        "https://raw.githubusercontent.com/sm-monirulislam/SM-Live-TV/refs/heads/main/World_Cup.m3u"
    ]

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            tasks = [fetch_single_m3u(client, url) for url in urls]
            results = await asyncio.gather(*tasks)
            for parsed in results:
                all_channels.extend(parsed)

        filtered = filter_worldcup_channels(all_channels)
        print(f"[M3U] Validating stream servers in parallel...")

        # Parallel validation of matched stream servers
        valid_channels = []
        async with httpx.AsyncClient(follow_redirects=True) as check_client:
            # Flatten all servers into a single list of checks to perform them concurrently
            server_checks = []
            for chan_idx, chan in enumerate(filtered):
                for srv_idx, srv in enumerate(chan["servers"]):
                    server_checks.append((chan_idx, srv_idx, srv))

            if server_checks:
                sem = asyncio.Semaphore(25)  # Limit concurrency to 25 to avoid socket exhaustion

                async def check_srv(srv):
                    async with sem:
                        return await is_server_working(check_client, srv)

                tasks = [check_srv(srv) for _, _, srv in server_checks]
                status_results = await asyncio.gather(*tasks)

                # Group working servers back by channel
                working_servers_by_chan = {i: [] for i in range(len(filtered))}
                for (chan_idx, srv_idx, srv), ok in zip(server_checks, status_results):
                    if ok:
                        working_servers_by_chan[chan_idx].append(srv)

                for chan_idx, chan in enumerate(filtered):
                    working_servers = working_servers_by_chan[chan_idx]
                    if working_servers:
                        chan["servers"] = working_servers
                        valid_channels.append(chan)

        _cached_channels = apply_server_and_category_overrides(valid_channels)
        _cached_channels = inject_custom_channels(_cached_channels)
        
        # Populate missing logos with accurate online URLs
        for chan in _cached_channels:
            cid = chan.get("id")
            if (not chan.get("logo") or chan.get("logo") == "") and cid in CHANNEL_LOGOS:
                chan["logo"] = CHANNEL_LOGOS[cid]

        print(f"[M3U] Total: {len(all_channels)} → {len(_cached_channels)} working channels matched")

        # Save to disk cache
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(_cached_channels, f, indent=2, ensure_ascii=False)
            print(f"[M3U] Saved {len(_cached_channels)} channels to disk cache.")
        except Exception as cache_err:
            print(f"[M3U] Error writing disk cache: {cache_err}")

    except Exception as e:
        print(f"[M3U] Error: {e}")
        if not _cached_channels:
            _cached_channels = []

    return _cached_channels


CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channels_cache.json")


def load_channels_from_disk() -> list[dict]:
    """Load cached channels from local JSON file if it exists, otherwise initialize fallback custom channels."""
    global _cached_channels
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    _cached_channels = data
                    print(f"[M3U] Loaded {len(_cached_channels)} channels from disk cache.")
                    return _cached_channels
        except Exception as e:
            print(f"[M3U] Error reading disk cache: {e}")
            
    # Fallback/Default: initialize with custom channels immediately if cache is missing
    print("[M3U] Cache file missing. Initializing cache with custom channels fallback.")
    fallback = inject_custom_channels([])
    for chan in fallback:
        cid = chan.get("id")
        if (not chan.get("logo") or chan.get("logo") == "") and cid in CHANNEL_LOGOS:
            chan["logo"] = CHANNEL_LOGOS[cid]
    _cached_channels = fallback
    return _cached_channels


def get_cached_channels() -> list[dict]:
    return _cached_channels
