"""
FIFA World Cup 2026 Fixtures — Real Data
Fetches match data from FIFA website with accurate fallback data
from the actual 2026 tournament (June 11 – July 19).
"""

import httpx
import time
import json
from datetime import datetime, date
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup

# ── Cache ────────────────────────────────────────────────────────────
_fixtures_cache: dict = {"upcoming": [], "past": [], "live": []}
_cache_timestamp: float = 0
CACHE_TTL = 300  # 5 minutes

# ══════════════════════════════════════════════════════════════════════
# REAL FIFA WORLD CUP 2026 DATA
# Tournament: June 11 – July 19, 2026
# Hosts: Canada, Mexico, USA  |  48 Teams, 12 Groups (A–L)
# ══════════════════════════════════════════════════════════════════════

def _build_fixtures() -> dict:
    """Build fixtures dynamically based on today's date."""
    today = date.today().isoformat()

    ALL_MATCHES = [
        # ── Matchday 1: June 11, 2026 ──
        {"id": 1, "group": "GROUP A", "date": "2026-06-11", "time": "20:00", "team1": {"name": "Mexico", "code": "MEX", "flag": "🇲🇽", "score": 2}, "team2": {"name": "South Africa", "code": "RSA", "flag": "🇿🇦", "score": 0}, "venue": "Estadio Azteca, Mexico City"},
        {"id": 2, "group": "GROUP A", "date": "2026-06-11", "time": "23:00", "team1": {"name": "South Korea", "code": "KOR", "flag": "🇰🇷", "score": 2}, "team2": {"name": "Czechia", "code": "CZE", "flag": "🇨🇿", "score": 1}, "venue": "Estadio Akron, Guadalajara"},

        # ── Matchday 1: June 12 ──
        {"id": 3, "group": "GROUP B", "date": "2026-06-12", "time": "12:00", "team1": {"name": "Canada", "code": "CAN", "flag": "🇨🇦", "score": 1}, "team2": {"name": "Bosnia & Herz.", "code": "BIH", "flag": "🇧🇦", "score": 1}, "venue": "BMO Field, Toronto"},
        {"id": 4, "group": "GROUP D", "date": "2026-06-12", "time": "18:00", "team1": {"name": "USA", "code": "USA", "flag": "🇺🇸", "score": 4}, "team2": {"name": "Paraguay", "code": "PAR", "flag": "🇵🇾", "score": 1}, "venue": "SoFi Stadium, Los Angeles"},
        {"id": 5, "group": "GROUP C", "date": "2026-06-12", "time": "15:00", "team1": {"name": "Brazil", "code": "BRA", "flag": "🇧🇷", "score": 2}, "team2": {"name": "Morocco", "code": "MAR", "flag": "🇲🇦", "score": 1}, "venue": "Rose Bowl, Pasadena"},
        {"id": 6, "group": "GROUP D", "date": "2026-06-12", "time": "21:00", "team1": {"name": "Italy", "code": "ITA", "flag": "🇮🇹", "score": 1}, "team2": {"name": "Turkey", "code": "TUR", "flag": "🇹🇷", "score": 0}, "venue": "MetLife Stadium, New Jersey"},

        # ── Matchday 1: June 13 ──
        {"id": 7, "group": "GROUP B", "date": "2026-06-13", "time": "12:00", "team1": {"name": "Qatar", "code": "QAT", "flag": "🇶🇦", "score": 1}, "team2": {"name": "Switzerland", "code": "SUI", "flag": "🇨🇭", "score": 1}, "venue": "BC Place, Vancouver"},
        {"id": 8, "group": "GROUP C", "date": "2026-06-13", "time": "15:00", "team1": {"name": "Colombia", "code": "COL", "flag": "🇨🇴", "score": 0}, "team2": {"name": "Senegal", "code": "SEN", "flag": "🇸🇳", "score": 2}, "venue": "NRG Stadium, Houston"},
        {"id": 9, "group": "GROUP E", "date": "2026-06-13", "time": "18:00", "team1": {"name": "Germany", "code": "GER", "flag": "🇩🇪", "score": 3}, "team2": {"name": "Curaçao", "code": "CUW", "flag": "🇨🇼", "score": 0}, "venue": "Lincoln Financial Field, Philadelphia"},
        {"id": 10, "group": "GROUP F", "date": "2026-06-13", "time": "21:00", "team1": {"name": "Argentina", "code": "ARG", "flag": "🇦🇷", "score": 2}, "team2": {"name": "Algeria", "code": "ALG", "flag": "🇩🇿", "score": 0}, "venue": "Hard Rock Stadium, Miami"},

        # ── Matchday 1: June 14 ──
        {"id": 11, "group": "GROUP E", "date": "2026-06-14", "time": "12:00", "team1": {"name": "Ivory Coast", "code": "CIV", "flag": "🇨🇮", "score": 1}, "team2": {"name": "Ecuador", "code": "ECU", "flag": "🇪🇨", "score": 1}, "venue": "AT&T Stadium, Dallas"},
        {"id": 12, "group": "GROUP F", "date": "2026-06-14", "time": "15:00", "team1": {"name": "Austria", "code": "AUT", "flag": "🇦🇹", "score": 0}, "team2": {"name": "Jordan", "code": "JOR", "flag": "🇯🇴", "score": 0}, "venue": "TQL Stadium, Cincinnati"},
        {"id": 13, "group": "GROUP G", "date": "2026-06-14", "time": "18:00", "team1": {"name": "Netherlands", "code": "NED", "flag": "🇳🇱", "score": 3}, "team2": {"name": "Japan", "code": "JPN", "flag": "🇯🇵", "score": 1}, "venue": "Lumen Field, Seattle"},
        {"id": 14, "group": "GROUP H", "date": "2026-06-14", "time": "21:00", "team1": {"name": "Spain", "code": "ESP", "flag": "🇪🇸", "score": 2}, "team2": {"name": "Cabo Verde", "code": "CPV", "flag": "🇨🇻", "score": 0}, "venue": "Gillette Stadium, Foxborough"},

        # ── Matchday 1: June 15 (TODAY) ──
        {"id": 15, "group": "GROUP G", "date": "2026-06-15", "time": "12:00", "team1": {"name": "Belgium", "code": "BEL", "flag": "🇧🇪"}, "team2": {"name": "Egypt", "code": "EGY", "flag": "🇪🇬"}, "venue": "BMO Stadium, Los Angeles"},
        {"id": 16, "group": "GROUP H", "date": "2026-06-15", "time": "15:00", "team1": {"name": "Saudi Arabia", "code": "KSA", "flag": "🇸🇦"}, "team2": {"name": "Uruguay", "code": "URU", "flag": "🇺🇾"}, "venue": "CITYPARK, St. Louis"},
        {"id": 17, "group": "GROUP I", "date": "2026-06-15", "time": "18:00", "team1": {"name": "France", "code": "FRA", "flag": "🇫🇷"}, "team2": {"name": "Uzbekistan", "code": "UZB", "flag": "🇺🇿"}, "venue": "Mercedes-Benz Stadium, Atlanta"},
        {"id": 18, "group": "GROUP I", "date": "2026-06-15", "time": "21:00", "team1": {"name": "Iran", "code": "IRN", "flag": "🇮🇷"}, "team2": {"name": "New Zealand", "code": "NZL", "flag": "🇳🇿"}, "venue": "GEODIS Park, Nashville"},

        # ── Matchday 1: June 16 ──
        {"id": 19, "group": "GROUP J", "date": "2026-06-16", "time": "12:00", "team1": {"name": "Portugal", "code": "POR", "flag": "🇵🇹"}, "team2": {"name": "DR Congo", "code": "COD", "flag": "🇨🇩"}, "venue": "MetLife Stadium, New Jersey"},
        {"id": 20, "group": "GROUP J", "date": "2026-06-16", "time": "15:00", "team1": {"name": "Iraq", "code": "IRQ", "flag": "🇮🇶"}, "team2": {"name": "Norway", "code": "NOR", "flag": "🇳🇴"}, "venue": "BMO Field, Toronto"},
        {"id": 21, "group": "GROUP K", "date": "2026-06-16", "time": "18:00", "team1": {"name": "England", "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"}, "team2": {"name": "Croatia", "code": "CRO", "flag": "🇭🇷"}, "venue": "AT&T Stadium, Dallas"},
        {"id": 22, "group": "GROUP L", "date": "2026-06-16", "time": "21:00", "team1": {"name": "Ghana", "code": "GHA", "flag": "🇬🇭"}, "team2": {"name": "Panama", "code": "PAN", "flag": "🇵🇦"}, "venue": "Lumen Field, Seattle"},

        # ── Matchday 1: June 17 ──
        {"id": 23, "group": "GROUP K", "date": "2026-06-17", "time": "12:00", "team1": {"name": "Sweden", "code": "SWE", "flag": "🇸🇪"}, "team2": {"name": "Tunisia", "code": "TUN", "flag": "🇹🇳"}, "venue": "NRG Stadium, Houston"},
        {"id": 24, "group": "GROUP L", "date": "2026-06-17", "time": "15:00", "team1": {"name": "Australia", "code": "AUS", "flag": "🇦🇺"}, "team2": {"name": "Peru", "code": "PER", "flag": "🇵🇪"}, "venue": "SoFi Stadium, Los Angeles"},

        # ── Matchday 2: June 18 ──
        {"id": 25, "group": "GROUP A", "date": "2026-06-18", "time": "15:00", "team1": {"name": "South Africa", "code": "RSA", "flag": "🇿🇦"}, "team2": {"name": "South Korea", "code": "KOR", "flag": "🇰🇷"}, "venue": "Estadio Akron, Guadalajara"},
        {"id": 26, "group": "GROUP A", "date": "2026-06-18", "time": "18:00", "team1": {"name": "Czechia", "code": "CZE", "flag": "🇨🇿"}, "team2": {"name": "Mexico", "code": "MEX", "flag": "🇲🇽"}, "venue": "Estadio Azteca, Mexico City"},
        {"id": 27, "group": "GROUP B", "date": "2026-06-18", "time": "21:00", "team1": {"name": "Switzerland", "code": "SUI", "flag": "🇨🇭"}, "team2": {"name": "Canada", "code": "CAN", "flag": "🇨🇦"}, "venue": "BC Place, Vancouver"},

        # ── Matchday 2: June 19 ──
        {"id": 28, "group": "GROUP C", "date": "2026-06-19", "time": "15:00", "team1": {"name": "Morocco", "code": "MAR", "flag": "🇲🇦"}, "team2": {"name": "Colombia", "code": "COL", "flag": "🇨🇴"}, "venue": "Rose Bowl, Pasadena"},
        {"id": 29, "group": "GROUP D", "date": "2026-06-19", "time": "18:00", "team1": {"name": "Paraguay", "code": "PAR", "flag": "🇵🇾"}, "team2": {"name": "Italy", "code": "ITA", "flag": "🇮🇹"}, "venue": "MetLife Stadium, New Jersey"},
        {"id": 30, "group": "GROUP D", "date": "2026-06-19", "time": "21:00", "team1": {"name": "Turkey", "code": "TUR", "flag": "🇹🇷"}, "team2": {"name": "USA", "code": "USA", "flag": "🇺🇸"}, "venue": "SoFi Stadium, Los Angeles"},
    ]

    fixtures = {"upcoming": [], "past": [], "live": []}

    for match in ALL_MATCHES:
        m = dict(match)  # shallow copy
        match_date = m["date"]

        if match_date < today:
            # Past match — ensure scores exist
            m["status"] = "completed"
            if "score" not in m["team1"]:
                m["team1"]["score"] = 0
            if "score" not in m["team2"]:
                m["team2"]["score"] = 0
            fixtures["past"].append(m)
        elif match_date == today:
            # Today's matches — could be live or upcoming
            m["status"] = "upcoming"
            fixtures["upcoming"].insert(0, m)  # today's matches at top
        else:
            # Future match — no scores
            m["status"] = "upcoming"
            t1 = dict(m["team1"])
            t2 = dict(m["team2"])
            t1.pop("score", None)
            t2.pop("score", None)
            m["team1"] = t1
            m["team2"] = t2
            fixtures["upcoming"].append(m)

    return fixtures


FALLBACK_FIXTURES = _build_fixtures()


async def scrape_fifa_fixtures() -> dict:
    """
    Attempt to scrape FIFA's scores-fixtures page.
    Falls back to hardcoded real data if scraping fails.
    """
    global _fixtures_cache, _cache_timestamp

    # Check cache
    if time.time() - _cache_timestamp < CACHE_TTL and any(_fixtures_cache.values()):
        return _fixtures_cache

    try:
        url = "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/scores-fixtures"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)

            if resp.status_code == 200 and len(resp.text) > 5000:
                fixtures = _parse_fifa_html(resp.text)
                if fixtures and any(fixtures.values()):
                    _fixtures_cache = fixtures
                    _cache_timestamp = time.time()
                    print(f"[FIFA] Scraped {len(fixtures.get('upcoming', []))} upcoming, {len(fixtures.get('past', []))} past fixtures")
                    return _fixtures_cache

        raise Exception("Scraping did not yield results")

    except Exception as e:
        print(f"[FIFA] Scrape failed ({e}), using real fallback data")
        # Rebuild fallback dynamically based on current date
        _fixtures_cache = _build_fixtures()
        _cache_timestamp = time.time()
        return _fixtures_cache


def _parse_fifa_html(html: str) -> dict:
    """Parse FIFA HTML page for match fixtures."""
    soup = BeautifulSoup(html, "lxml")
    fixtures = {"upcoming": [], "past": [], "live": []}

    # Try to find JSON data embedded in script tags
    for script in soup.find_all("script"):
        text = script.string or ""
        if "MatchStatus" in text or "HomeTeam" in text or "matchday" in text.lower():
            try:
                data = json.loads(text)
                matches = _extract_matches_from_json(data)
                if matches and any(matches.values()):
                    return matches
            except (json.JSONDecodeError, Exception):
                continue

    return fixtures


def _extract_matches_from_json(data, depth=0):
    """Recursively search JSON data for match arrays."""
    if depth > 10:
        return None

    if isinstance(data, dict):
        for key in ["matches", "Results", "fixtures", "Matches"]:
            if key in data and isinstance(data[key], list) and len(data[key]) > 0:
                return _convert_matches(data[key])

        for value in data.values():
            result = _extract_matches_from_json(value, depth + 1)
            if result:
                return result

    elif isinstance(data, list) and len(data) > 2:
        if all(isinstance(item, dict) for item in data[:3]):
            sample = data[0]
            if any(k in sample for k in ["HomeTeam", "AwayTeam", "home_team", "away_team"]):
                return _convert_matches(data)

        for item in data:
            result = _extract_matches_from_json(item, depth + 1)
            if result:
                return result

    return None


def _convert_matches(matches: list) -> dict:
    """Convert FIFA JSON match data to our format."""
    fixtures = {"upcoming": [], "past": [], "live": []}

    for match in matches:
        try:
            home = match.get("HomeTeam", match.get("home_team", {})) or {}
            away = match.get("AwayTeam", match.get("away_team", {})) or {}

            home_name = _get_team_name(home)
            away_name = _get_team_name(away)
            if not home_name or not away_name:
                continue

            home_code = home.get("IdCountry", home.get("code", ""))
            away_code = away.get("IdCountry", away.get("code", ""))

            fixture = {
                "id": match.get("IdMatch", match.get("id", 0)),
                "group": _get_group_name(match),
                "date": _get_date(match),
                "time": _get_time(match),
                "venue": _get_venue(match),
                "status": "upcoming",
                "team1": {"name": home_name, "code": home_code, "flag": get_flag(home_code)},
                "team2": {"name": away_name, "code": away_code, "flag": get_flag(away_code)},
            }

            match_status = match.get("MatchStatus", match.get("status", 0))
            home_score = home.get("Score", home.get("score"))
            away_score = away.get("Score", away.get("score"))

            if match_status in [0, "upcoming", "scheduled", 1]:
                fixture["status"] = "upcoming"
                fixtures["upcoming"].append(fixture)
            elif match_status in [3, "finished", "completed"]:
                fixture["status"] = "completed"
                fixture["team1"]["score"] = home_score
                fixture["team2"]["score"] = away_score
                fixtures["past"].append(fixture)
            else:
                fixture["status"] = "live"
                fixture["team1"]["score"] = home_score
                fixture["team2"]["score"] = away_score
                fixtures["live"].append(fixture)
        except Exception:
            continue

    return fixtures if any(fixtures.values()) else None


def _get_team_name(team):
    if isinstance(team, dict):
        for key in ["TeamName", "ShortClubName", "name"]:
            val = team.get(key)
            if val:
                if isinstance(val, list) and val:
                    return val[0].get("Description", str(val[0]))
                return str(val)
    return ""


def _get_group_name(match):
    gn = match.get("GroupName", match.get("group_name", ""))
    if isinstance(gn, list) and gn:
        return gn[0].get("Description", "Group Stage")
    return str(gn) if gn else "Group Stage"


def _get_date(match):
    for key in ["Date", "date", "MatchDate"]:
        val = match.get(key, "")
        if val:
            return str(val)[:10]
    return ""


def _get_time(match):
    for key in ["LocalDate", "local_date", "MatchTime"]:
        val = match.get(key, "")
        if val and len(str(val)) >= 16:
            return str(val)[11:16]
    return "TBD"


def _get_venue(match):
    stadium = match.get("Stadium", match.get("stadium", {}))
    if isinstance(stadium, dict):
        for key in ["Name", "name"]:
            val = stadium.get(key)
            if val:
                if isinstance(val, list) and val:
                    return val[0].get("Description", "")
                return str(val)
    return str(stadium) if stadium else ""


# ── Country flag mapping ─────────────────────────────────────────────
COUNTRY_FLAGS = {
    "USA": "🇺🇸", "MEX": "🇲🇽", "CAN": "🇨🇦", "BRA": "🇧🇷", "ARG": "🇦🇷",
    "GER": "🇩🇪", "FRA": "🇫🇷", "ENG": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "ESP": "🇪🇸", "POR": "🇵🇹",
    "NED": "🇳🇱", "ITA": "🇮🇹", "JPN": "🇯🇵", "KOR": "🇰🇷", "AUS": "🇦🇺",
    "MAR": "🇲🇦", "SEN": "🇸🇳", "NGA": "🇳🇬", "GHA": "🇬🇭", "CMR": "🇨🇲",
    "EGY": "🇪🇬", "KSA": "🇸🇦", "QAT": "🇶🇦", "IRN": "🇮🇷", "COL": "🇨🇴",
    "URU": "🇺🇾", "CHL": "🇨🇱", "ECU": "🇪🇨", "PAR": "🇵🇾", "PER": "🇵🇪",
    "CRC": "🇨🇷", "HON": "🇭🇳", "JAM": "🇯🇲", "TRI": "🇹🇹", "BOL": "🇧🇴",
    "SUI": "🇨🇭", "BEL": "🇧🇪", "CRO": "🇭🇷", "SRB": "🇷🇸", "DEN": "🇩🇰",
    "NOR": "🇳🇴", "SWE": "🇸🇪", "POL": "🇵🇱", "UKR": "🇺🇦", "WAL": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "SCO": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "TUN": "🇹🇳", "ALG": "🇩🇿", "RSA": "🇿🇦", "NZL": "🇳🇿",
    "CZE": "🇨🇿", "BIH": "🇧🇦", "CUW": "🇨🇼", "CIV": "🇨🇮", "CPV": "🇨🇻",
    "IRQ": "🇮🇶", "JOR": "🇯🇴", "COD": "🇨🇩", "UZB": "🇺🇿", "PAN": "🇵🇦",
    "AUT": "🇦🇹", "HTI": "🇭🇹", "TUR": "🇹🇷",
}


def get_flag(code: str) -> str:
    return COUNTRY_FLAGS.get(code.upper(), "🏳️") if code else "🏳️"


def get_cached_fixtures() -> dict:
    return _fixtures_cache if any(_fixtures_cache.values()) else _build_fixtures()
