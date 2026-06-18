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
    # ── FIFA Live — Top 13 Priority Channels (always featured) ──
    ([["t sports", "hd"], ["t-sports"], ["tsports"]], "T Sports HD", "featured"),
    ([["ptv", "sports"]], "PTV Sports", "featured"),
    ([["fox", "5"]], "Fox 5", "featured"),
    ([["trt", "1"]], "TRT 1", "featured"),
    ([["bein", "sports", "1"], ["bein", "sport", "1"]], "beIN Sports 1 (Full HD)", "featured"),
    ([["somoy", "tv"]], "Somoy TV", "featured"),
    ([["m6", "direct"], ["m6"]], "M6 Direct", "featured"),
    ([["zee", "bangla"]], "Zee Bangla", "featured"),
    ([["caze", "tv"]], "CAZE TV", "featured"),
    ([["cola", "tv"], ["colatv"]], "ColaTV", "featured"),
    ([["dazn"]], "DAZN (Full HD)", "featured"),
    ([["d sports"], ["dsports"], ["d-sports"]], "D Sports", "featured"),
    # Telemundo does NOT stream FIFA World Cup — moved to live
    ([["telemundo"]], "Telemundo", "live"),

    # ── Other Live Channels ──
    ([["tapmad", "hd"], ["tapmad"]], "Tapmad HD", "live"),
    # CCTV 5, ELTA Sports, Macao Sports promoted to featured (FIFA WC broadcast)
    ([["macao", "sport"]], "Macao Sports (FHD)", "live"),
    ([["elta", "sport"]], "ELTA Sports (FHD)", "live"),
    ([["cctv", "5"]], "CCTV 5 (Full HD)", "live"),
    ([["win", "sports"]], "WIN Sports (Full HD)", "live"),
    ([["bein", "sports", "türkiye"], ["bein", "sports", "turkiye"], ["bein", "turkey"]], "beIN SPORTS Türkiye", "live"),
    ([["tudn", "canal", "5"], ["tudn", "sports"]], "TUDN Sports - Canal 5 (Full HD)", "live"),
    ([["tv", "azteca", "7"], ["azteca", "7"], ["tv", "azteca"]], "TV Azteca", "live"),
    ([["sports", "18"]], "Sports 18 HD", "live"),
    
    ([["tsn", "1"], ["tsn", "sports", "1"]], "TSN Sports 1", "live"),
    ([["tudn", "usa"], ["tudn"]], "TUDN", "live"),
    ([["gazi", "tv"], ["gtv"]], "Gazi TV HD", "live"),
    ([["fox", "sports", "1"], ["fox", "sport"]], "FOX Sports 1", "live"),
    ([["bioscope"]], "BIOSCOPE+", "live"),
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
    ([["fussball", "1"], ["fussball", "tv", "1"], ["fußball", "1"]], "Fussball TV 1", "featured"),
    ([["fussball", "2"], ["fussball", "tv", "2"], ["fußball", "2"]], "Fussball TV 2", "featured"),
]

# ── Logo fallbacks — only applied when M3U has no logo for this channel ──
# Only use URLs that are confirmed working. Don't invent imgur paths.
CHANNEL_LOGOS: dict[str, str] = {
    # Custom/Featured channel logos with verified working URLs:
    "fox_5":                  "https://upload.wikimedia.org/wikipedia/commons/c/c0/Fox_Broadcasting_Company_logo_%282019%29.svg",
    "m6_direct":              "https://upload.wikimedia.org/wikipedia/commons/a/a6/M6_logo.svg",
    "macao_sports_fhd_":      "https://static.wikia.nocookie.net/logopedia/images/2/2c/TDMSport.png",
    "caze_tv":                "https://upload.wikimedia.org/wikipedia/pt/2/22/Logotipo_da_Caz%C3%A9TV.png",
    "zee_bangla":             "https://upload.wikimedia.org/wikipedia/commons/5/5f/Zee_Bangla_logo.png",
    "bein_sports_1_full_hd_": "https://upload.wikimedia.org/wikipedia/commons/d/d4/BeIN_Sports_logo_%28horizontal_version%29.svg",
    "bein_sports_2":          "https://upload.wikimedia.org/wikipedia/commons/d/d4/BeIN_Sports_logo_%28horizontal_version%29.svg",
    "sony_ten_1_hd":          "https://upload.wikimedia.org/wikipedia/commons/2/23/Sony_Sports_Network_Logo.png",
    "sony_ten_2_hd":          "https://upload.wikimedia.org/wikipedia/commons/2/23/Sony_Sports_Network_Logo.png",
    "supersport":             "https://upload.wikimedia.org/wikipedia/commons/a/a0/SuperSport_Albania.svg",

    # Standard/M3U fallbacks:
    "t_sports_hd":            "https://i.imgur.com/2JzlorD.png",
    "ptv_sports":             "https://i.imgur.com/CPm6GHA.png",
    "somoy_tv":               "https://i.imgur.com/i54AQic.png",
    "win_sports_full_hd_":    "https://i.imgur.com/DuSSrHV.png",
    "d_sports":               "https://i.imgur.com/2PoEm1x.png",
    "gazi_tv_hd":             "https://i.imgur.com/b0Wx7pE.png",
    "universo":               "https://i.imgur.com/RZ8pIKe.png",
    "yes_tv_hd":              "https://i.imgur.com/3CDxatu.png",
    "elta_sports_fhd_":       "https://upload.wikimedia.org/wikipedia/commons/5/5b/ELTA_logo.svg",
    "colatv":                 "https://colatv.app/favicon.png",
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
        parsed = await asyncio.to_thread(parse_m3u, resp.text)
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
            "180.94.28.28",
            "zohanayaan.com",
            "t-online.de",
            "streamhostingcdn.top",
            "szyac.com",
            "msdht.app",
            "medya.trt.com.tr",
            "trtcanlitv-lh.akamaihd.net",
            "egmdispatch.com",
            "cltvlv.com",
            "liveplay.myqcloud.com",   # CCTV 5 official CDN
            "tdm.mma.gov.mo",          # Macao Sports official
            "elt.gr",                  # ELTA Sports official
            "somoytv.com",             # Somoy TV official
            "tsports.com.bd",          # T Sports official
            "aynaott.com",             # aynaott fallback streams
            "198.195.239.50",          # BDIX: T Sports / PTV Sports live server
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
        
        # Dynamically rewrite raw MPEG-TS (.ts) streams to HLS (.m3u8) for Xtream Codes servers
        for s in chan_copy["servers"]:
            if s["url"].endswith(".ts") and ("rgkkw.live" in s["url"] or "starhub.pro" in s["url"] or "v3v3v.xyz" in s["url"]):
                s["url"] = s["url"][:-3] + ".m3u8"
        
        # 1. PTV Sports (ptv_sports)
        # Category: featured. Keep only verified working servers and sort them as requested.
        if cid == "ptv_sports":
            chan_copy["category"] = "featured"
            servers = [
                s for s in chan_copy["servers"]
                if "cdn9.zohanayaan.com" not in s["url"]
                and "cdn2.zohanayaan.com" not in s["url"]
                and "119.156.228.231" not in s["url"]
            ]
            
            # Find specific servers to reorder:
            # - s5 (Server 5): contains "180.94.28.28:8097" or "PTV-Sports"
            # - s6 (Server 6): contains "zohanayaan.com"
            # - s1 (Server 1): contains "198.195.239.50:8095" or "/ptv/"
            s5 = next((s for s in servers if "180.94.28.28:8097" in s["url"] or "PTV-Sports" in s["url"]), None)
            s6 = next((s for s in servers if "zohanayaan.com" in s["url"]), None)
            s1 = next((s for s in servers if "198.195.239.50:8095" in s["url"] or "/ptv/" in s["url"]), None)
            
            ordered = []
            if s5:
                ordered.append(s5)
            if s6:
                ordered.append(s6)
            if s1:
                ordered.append(s1)
                
            placed = {id(s) for s in ordered}
            for s in servers:
                if id(s) not in placed:
                    ordered.append(s)
                    
            for idx, s in enumerate(ordered):
                s["name"] = f"PTV Sports Server {idx + 1}"
                
            chan_copy["servers"] = ordered
        
        # 2. Somoy TV (somoy_tv)
        # Category: featured. Keep only the first working server (custom stream injected via CUSTOM_CHANNEL_SERVERS).
        # thebosstv.com only works locally — use stream.somoytv.com (official) as priority.
        elif cid == "somoy_tv":
            chan_copy["category"] = "featured"
            # Prioritize official stream; keep at most 2 servers
            chan_copy["servers"] = chan_copy["servers"][:2]
            
        # 3. beIN Sports 1 (bein_sports_1_full_hd_)
        # Category: featured (Fifa live). Make custom direct stream default, then ycn-redirect, then others.
        elif cid == "bein_sports_1_full_hd_":
            chan_copy["category"] = "featured"
            custom = [s for s in chan_copy["servers"] if "streamhostingcdn.top/stream/23" in s["url"]]
            target = [s for s in chan_copy["servers"] if "het4444.ycn-redirect.com" in s["url"]]
            others = [s for s in chan_copy["servers"] if "streamhostingcdn.top/stream/23" not in s["url"] and "het4444.ycn-redirect.com" not in s["url"]]
            chan_copy["servers"] = custom + target + others
            
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
        # Category: featured.
        # Priority: BDIX streams first (/tsports/ path or 198.195.239.50), then non-BDIX fallbacks.
        # NOTE: BDIX streams only work for users on BDIX-connected ISPs (BD local peering).
        #       Non-BDIX users will fall through to the next available server automatically.
        elif cid == "t_sports_hd":
            chan_copy["category"] = "featured"
            bdix_servers = [s for s in chan_copy["servers"] if "/tsports/" in s["url"] or "198.195.239.50" in s["url"]]
            other_servers = [s for s in chan_copy["servers"] if "/tsports/" not in s["url"] and "198.195.239.50" not in s["url"]]
            chan_copy["servers"] = bdix_servers + other_servers
            
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

        # 9. Fox 5 (fox_5) — Priority FIFA channel
        elif cid == "fox_5":
            chan_copy["category"] = "featured"

        # 10. Telemundo — NOT streaming FIFA WC, keep as live
        elif cid == "telemundo":
            chan_copy["category"] = "live"

        # 11. M6 Direct (m6_direct) — Priority FIFA channel
        # Keep only Server 2 (working), Server 1 is broken
        elif cid == "m6_direct":
            chan_copy["category"] = "featured"
            # Remove broken server 1 (test.946985.filegear-sg.me)
            chan_copy["servers"] = [
                s for s in chan_copy["servers"]
                if "946985.filegear" not in s["url"]
            ]

        # 12. Zee Bangla (zee_bangla) — Priority FIFA channel
        # (already set above via server filter, but ensure category is featured)
        # elif handled above already

        if chan_copy["servers"]:
            modified_channels.append(chan_copy)
            
    # Sort featured first, then by name
    modified_channels.sort(key=lambda c: (0 if c["category"] == "featured" else 1, c["name"]))
    return modified_channels


# ── Custom hardcoded channels (user-verified URLs) ──────────────────
CUSTOM_CHANNEL_SERVERS = {
    # channel_id: (display_name, category, quality, [server_dicts])
    # Server list order matters: first server is tried first by the player.
    # BDIX servers (198.195.x.x, 180.94.x.x) only work for BDIX-ISP users.
    # Non-BDIX fallbacks let other users still watch.

    # ── T Sports HD: BDIX servers work locally. Official stream as fallback for production. ──
    "t_sports_hd": ("T Sports HD", "featured", "FHD", [
        {"url": "http://198.195.239.50:8095/tsports/index.m3u8", "name": "T Sports Server 1 (BDIX)", "quality": "FHD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
        {"url": "http://198.195.239.50:8095/tsports/tracks-v1a1/mono.m3u8", "name": "T Sports Server 2 (Direct BDIX)", "quality": "FHD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
        {"url": "https://live.tsports.com.bd/live/tsports/index.m3u8", "name": "T Sports Official", "quality": "HD", "referrer": "https://tsports.com.bd/", "user_agent": "", "license_type": "", "license_key": ""},
        {"url": "https://tvsen7.aynaott.com/tsports-hd/index.m3u8", "name": "T Sports HD", "quality": "HD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),

    # ── PTV Sports: BDIX servers work locally, official stream for production. ──
    # Token-based URLs (zohanayaan.com, 180.94.28.28:8097) expire — removed.
    "ptv_sports": ("PTV Sports", "featured", "FHD", [
        {"url": "http://198.195.239.50:8095/ptv/index.m3u8", "name": "PTV Sports Server 1 (BDIX)", "quality": "FHD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
        {"url": "http://180.94.28.28/ptv/index.m3u8", "name": "PTV Sports Server 2 (BDIX)", "quality": "FHD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
        {"url": "https://tvsen7.aynaott.com/ptvsports-hd/index.m3u8", "name": "PTV Sports HD", "quality": "HD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),

    "win_sports_full_hd_": ("WIN Sports (Full HD)", "live", "FHD", [
        {"url": "https://1nyaler.streamhostingcdn.top/stream/32/index.m3u8", "name": "Win Sports", "quality": "SD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),

    # ── beIN Sports 1: Servers 1, 2, 4 confirmed working. 3, 5, 6, 7 removed. ──
    "bein_sports_1_full_hd_": ("beIN Sports 1 (Full HD)", "featured", "FHD", [
        {"url": "https://1nyaler.streamhostingcdn.top/stream/23/index.m3u8", "name": "beIN Sports 1 Server 1", "quality": "SD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
        {"url": "http://het4444.ycn-redirect.com/live/610303030/index.m3u8?t=XgTsAjb1QkrYQQnjbPWlsw&e=1781176238", "name": "beIN Sports 1 Server 2", "quality": "SD", "referrer": "", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "license_type": "", "license_key": ""},
        {"url": "https://cdn-uw2-prod.tsv2.amagi.tv/linear/amg02873-kravemedia-mtrspt1-distrotv/playlist.m3u8", "name": "beIN Sports 1 Server 4", "quality": "SD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),

    "fox_5": ("Fox 5", "featured", "HD", [
        {"url": "http://84.17.50.102/fox/index.m3u8", "name": "Fox 5 Custom", "quality": "HD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),

    # ── CCTV 5: Dead custom server (74.91.26.218) replaced with official CDN ──
    "cctv_5_full_hd_": ("CCTV 5 (Full HD)", "live", "HD", [
        {"url": "https://cctvwbndali.liveplay.myqcloud.com/cctv/cctv5hd/index.m3u8", "name": "CCTV 5 HD", "quality": "HD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
        {"url": "https://cctvwbndali.liveplay.myqcloud.com/cctv/cctv5/index.m3u8", "name": "CCTV 5", "quality": "SD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),

    # ── ELTA Sports: Dead custom server (74.91.26.218) replaced with official web TV ──
    "elta_sports_fhd_": ("ELTA Sports (FHD)", "live", "HD", [
        {"url": "https://elta-webtv-live.elt.gr/elta/master.m3u8", "name": "ELTA Sports Live", "quality": "HD", "referrer": "https://www.elt.gr/", "user_agent": "", "license_type": "", "license_key": ""},
    ]),

    # ── Macao Sports: Dead custom server (74.91.26.218) replaced with official TDM stream ──
    "macao_sports_fhd_": ("Macao Sports (FHD)", "live", "FHD", [
        {"url": "https://tdm.mma.gov.mo/live/sport-hd/index.m3u8", "name": "TDM Macao Sport HD", "quality": "FHD", "referrer": "https://www.tdm.com.mo/", "user_agent": "", "license_type": "", "license_key": ""},
    ]),

    # ── DAZN: Only Server 1 streams WC. Servers 2, 3, 4 removed. ──
    "dazn_full_hd_": ("DAZN (Full HD)", "featured", "FHD", [
        {"url": "https://1nyaler.streamhostingcdn.top/stream/94/index.m3u8", "name": "DAZN Server 1", "quality": "SD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
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

    # ── TRT 1: master_1440 not responding; replaced with working URLs + referrer ──
    "trt_1": ("TRT 1", "featured", "FHD", [
        {"url": "https://tv-trt1.medya.trt.com.tr/master.m3u8", "name": "TRT 1 (1080p)", "quality": "FHD", "referrer": "https://www.trt1.com.tr/", "user_agent": "", "license_type": "", "license_key": ""},
        {"url": "https://trtcanlitv-lh.akamaihd.net/i/TRTTV1_1@181842/master.m3u8", "name": "TRT 1 Akamai", "quality": "HD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),

    # ── Somoy TV: thebosstv.com only works locally. Official stream for production. ──
    "somoy_tv": ("Somoy TV", "featured", "HD", [
        {"url": "https://owrcovcrpy.gpcdn.net/bpk-tv/1702/output/index.m3u8", "name": "Somoy TV GPCDN", "quality": "HD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
        {"url": "https://bozztv.com/rongo/rongo-somoy/index.m3u8", "name": "Somoy TV Rongo", "quality": "HD", "referrer": "", "user_agent": "", "license_type": "", "license_key": ""},
    ]),
}

# ── Backup mirror servers for auto-healing when stream URLs go offline ──
# NOTE: Dead IP servers (74.91.26.218, 198.204.240.250) have been removed.
# These mirrors are probed only if the primary custom stream goes down.
MIRROR_SERVERS = {
    "cctv_5_full_hd_": [
        ("CCTV 5 HD Mirror", "https://cctvwbndali.liveplay.myqcloud.com/cctv/cctv5hd/index.m3u8"),
        ("CCTV 5 SD Mirror", "https://cctvwbndali.liveplay.myqcloud.com/cctv/cctv5/index.m3u8"),
    ],
    "macao_sports_fhd_": [
        ("Macao Sports Mirror", "https://tdm.mma.gov.mo/live/sport-hd/index.m3u8"),
    ],
    "elta_sports_fhd_": [
        ("ELTA Sports Mirror", "https://elta-webtv-live.elt.gr/elta/master.m3u8"),
    ],
    "somoy_tv": [
        ("Somoy TV Mirror", "https://stream.somoytv.com/live/somoytv.stream/playlist.m3u8"),
    ],
    "t_sports_hd": [
        ("T Sports Official Mirror", "https://live.tsports.com.bd/live/tsports/index.m3u8"),
        ("T Sports HD Mirror", "https://tvsen7.aynaott.com/tsports-hd/index.m3u8"),
    ],
    "trt_1": [
        ("TRT 1 Akamai Mirror", "https://trtcanlitv-lh.akamaihd.net/i/TRTTV1_1@181842/master.m3u8"),
    ],
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


async def fetch_live_colatv_servers(client: httpx.AsyncClient) -> list[dict]:
    """Fetch live match stream URLs from ColaTV API."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Origin": "https://colatv.app",
        "Referer": "https://colatv.app/"
    }
    servers = []
    try:
        r = await client.get("https://api.cltvlv.com/api/matches", headers=headers, timeout=8.0)
        if r.status_code == 200:
            data = r.json()
            matches_dict = data.get("data", {})
            for match_key, match_info in matches_dict.items():
                video_url = match_info.get("videoUrl")
                if video_url:
                    home = match_info.get("homeTeamName", "Home")
                    away = match_info.get("awayTeamName", "Away")
                    servers.append({
                        "url": video_url,
                        "name": f"ColaTV - {home} vs {away}",
                        "quality": "FHD",
                        "referrer": "",
                        "user_agent": "",
                        "license_type": "",
                        "license_key": ""
                    })
    except Exception as e:
        print(f"[ColaTV API] Error: {e}")
    return servers


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

        filtered = await asyncio.to_thread(filter_worldcup_channels, all_channels)
        
        # 1. Inject custom channels first so they can be validated and auto-healed in parallel
        channels_to_validate = inject_custom_channels(filtered)

        print(f"[M3U] Validating stream servers in parallel...")

        # Parallel validation of matched stream servers
        valid_channels = []
        async with httpx.AsyncClient(follow_redirects=True) as check_client:
            # 2. Dynamically fetch latest ColaTV streams from API inside the active client context
            colatv_api_servers = await fetch_live_colatv_servers(check_client)
            if colatv_api_servers:
                colatv_chan = next((c for c in channels_to_validate if c["id"] == "colatv"), None)
                if colatv_chan:
                    colatv_chan["servers"] = colatv_api_servers + colatv_chan["servers"]
                else:
                    channels_to_validate.append({
                        "id": "colatv",
                        "name": "ColaTV",
                        "category": "featured",
                        "logo": "",
                        "quality": "FHD",
                        "servers": colatv_api_servers
                    })

            # Flatten all servers into a single list of checks to perform them concurrently
            # Flatten all servers into a single list of checks to perform them concurrently
            server_checks = []
            for chan_idx, chan in enumerate(channels_to_validate):
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
                working_servers_by_chan = {i: [] for i in range(len(channels_to_validate))}
                for (chan_idx, srv_idx, srv), ok in zip(server_checks, status_results):
                    if ok:
                        working_servers_by_chan[chan_idx].append(srv)

                for chan_idx, chan in enumerate(channels_to_validate):
                    working_servers = working_servers_by_chan[chan_idx]
                    cid = chan["id"]
                    
                    # Auto-Healing: If mirror channel is down, check backup mirrors!
                    if not working_servers and cid in MIRROR_SERVERS:
                        print(f"[Auto-Healing] Channel '{chan['name']}' has 0 working streams. Probing backup mirrors...")
                        for m_name, m_url in MIRROR_SERVERS[cid]:
                            mirror_srv = {
                                "url": m_url,
                                "name": m_name,
                                "quality": chan.get("quality", "FHD"),
                                "referrer": "",
                                "user_agent": "",
                                "license_type": "",
                                "license_key": ""
                            }
                            if await is_server_working(check_client, mirror_srv):
                                print(f"[Auto-Healing] Found working mirror for '{chan['name']}': {m_url}")
                                working_servers.append(mirror_srv)
                                break
                                
                    if working_servers:
                        chan["servers"] = working_servers
                        valid_channels.append(chan)

        _cached_channels = apply_server_and_category_overrides(valid_channels)
        
        # Fill missing or broken logos with confirmed fallback URLs
        for chan in _cached_channels:
            cid = chan.get("id")
            logo = chan.get("logo", "")
            is_broken = not logo or "ftpbdlive.com" in logo or "sunplex.net" in logo or "Fox_Broadcasting_Company_logo_2019.svg" in logo or "M6_Music" in logo
            if (is_broken or cid in ["fox_5", "m6_direct", "macao_sports_fhd_", "caze_tv", "zee_bangla", "bein_sports_1_full_hd_", "bein_sports_2", "sony_ten_1_hd", "sony_ten_2_hd", "supersport"]) and cid in CHANNEL_LOGOS:
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
                    # Apply logo fixes here too to ensure logos are updated dynamically
                    for chan in _cached_channels:
                        cid = chan.get("id")
                        logo = chan.get("logo", "")
                        is_broken = not logo or "ftpbdlive.com" in logo or "sunplex.net" in logo or "Fox_Broadcasting_Company_logo_2019.svg" in logo or "M6_Music" in logo
                        if (is_broken or cid in ["fox_5", "m6_direct", "macao_sports_fhd_", "caze_tv", "zee_bangla", "bein_sports_1_full_hd_", "bein_sports_2", "sony_ten_1_hd", "sony_ten_2_hd", "supersport"]) and cid in CHANNEL_LOGOS:
                            chan["logo"] = CHANNEL_LOGOS[cid]
                    print(f"[M3U] Loaded {len(_cached_channels)} channels from disk cache.")
                    return _cached_channels
        except Exception as e:
            print(f"[M3U] Error reading disk cache: {e}")
            
    # Fallback/Default: initialize with custom channels immediately if cache is missing
    print("[M3U] Cache file missing. Initializing cache with custom channels fallback.")
    fallback = inject_custom_channels([])
    for chan in fallback:
        cid = chan.get("id")
        logo = chan.get("logo", "")
        is_broken = not logo or "ftpbdlive.com" in logo or "sunplex.net" in logo or "Fox_Broadcasting_Company_logo_2019.svg" in logo or "M6_Music" in logo
        if (is_broken or cid in ["fox_5", "m6_direct", "macao_sports_fhd_", "caze_tv", "zee_bangla", "bein_sports_1_full_hd_", "bein_sports_2", "sony_ten_1_hd", "sony_ten_2_hd", "supersport"]) and cid in CHANNEL_LOGOS:
            chan["logo"] = CHANNEL_LOGOS[cid]
    _cached_channels = fallback
    return _cached_channels


def get_cached_channels() -> list[dict]:
    return _cached_channels
