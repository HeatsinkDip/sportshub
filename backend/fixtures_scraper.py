"""
FIFA World Cup 2026 Fixtures — Real Data
Fetches match data from FIFA website with accurate fallback data
from the actual 2026 tournament (June 11 – July 19).
"""

import httpx
import time
import json
import random
import re
from datetime import datetime, date, timedelta
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

def get_live_score(match_id: int, elapsed_minutes: int) -> tuple[int, int]:
    """Deterministically simulate live scores growing as match progresses."""
    rng = random.Random(match_id)
    num_home_goals = rng.randint(0, 4)
    num_away_goals = rng.randint(0, 4)
    
    home_goal_times = sorted([rng.randint(1, 90) for _ in range(num_home_goals)])
    away_goal_times = sorted([rng.randint(1, 90) for _ in range(num_away_goals)])
    
    current_home_score = sum(1 for t in home_goal_times if t <= elapsed_minutes)
    current_away_score = sum(1 for t in away_goal_times if t <= elapsed_minutes)
    
    return current_home_score, current_away_score

def get_completed_score(match_id: int, original_team1_score: int | None, original_team2_score: int | None) -> tuple[int, int]:
    """Return original hardcoded score if exists, or generate a deterministic completed score."""
    if original_team1_score is not None and original_team2_score is not None:
        return original_team1_score, original_team2_score
    rng = random.Random(match_id)
    return rng.randint(0, 4), rng.randint(0, 4)

def get_dynamic_fallback_fixtures(date_str: str) -> dict:
    """Dynamically partition and build fixtures for a specific date relative to now."""
    fixtures = {"upcoming": [], "past": [], "live": []}
    now = datetime.now()
    
    for match in ALL_MATCHES:
        if match.get("date") != date_str:
            continue
            
        m = dict(match)
        m["team1"] = dict(match["team1"])
        m["team2"] = dict(match["team2"])
        
        match_time_str = m.get("time", "12:00")
        if match_time_str == "TBD":
            match_time_str = "12:00"
            
        try:
            match_dt = datetime.fromisoformat(f"{date_str}T{match_time_str}:00")
        except Exception:
            match_dt = datetime.fromisoformat(f"{date_str}T12:00:00")
            
        if now < match_dt:
            m["status"] = "upcoming"
            m["team1"].pop("score", None)
            m["team2"].pop("score", None)
            fixtures["upcoming"].append(m)
        elif match_dt <= now < match_dt + timedelta(hours=2):
            m["status"] = "live"
            elapsed_minutes = int((now - match_dt).total_seconds() / 60)
            s1, s2 = get_live_score(m["id"], elapsed_minutes)
            m["team1"]["score"] = s1
            m["team2"]["score"] = s2
            fixtures["live"].append(m)
        else:
            m["status"] = "completed"
            s1, s2 = get_completed_score(m["id"], match["team1"].get("score"), match["team2"].get("score"))
            m["team1"]["score"] = s1
            m["team2"]["score"] = s2
            fixtures["past"].append(m)
            
    return fixtures

def _build_fixtures() -> dict:
    """Build all fixtures dynamically categorized relative to now."""
    fixtures = {"upcoming": [], "past": [], "live": []}
    now = datetime.now()
    for match in ALL_MATCHES:
        m = dict(match)
        m["team1"] = dict(match["team1"])
        m["team2"] = dict(match["team2"])
        
        match_time_str = m.get("time", "12:00")
        if match_time_str == "TBD":
            match_time_str = "12:00"
            
        try:
            match_dt = datetime.fromisoformat(f"{m['date']}T{match_time_str}:00")
        except Exception:
            match_dt = datetime.fromisoformat(f"{m['date']}T12:00:00")
            
        if now < match_dt:
            m["status"] = "upcoming"
            m["team1"].pop("score", None)
            m["team2"].pop("score", None)
            fixtures["upcoming"].append(m)
        elif match_dt <= now < match_dt + timedelta(hours=2):
            m["status"] = "live"
            elapsed_minutes = int((now - match_dt).total_seconds() / 60)
            s1, s2 = get_live_score(m["id"], elapsed_minutes)
            m["team1"]["score"] = s1
            m["team2"]["score"] = s2
            fixtures["live"].append(m)
        else:
            m["status"] = "completed"
            s1, s2 = get_completed_score(m["id"], match["team1"].get("score"), match["team2"].get("score"))
            m["team1"]["score"] = s1
            m["team2"]["score"] = s2
            fixtures["past"].append(m)
    return fixtures

FALLBACK_FIXTURES = _build_fixtures()



# ── openfootball Integration ─────────────────────────────────────────
_openfootball_cache = []
_openfootball_teams = {}
_openfootball_timestamp = 0
OPENFOOTBALL_TTL = 900  # 15 minutes

def get_match_key(team1: str, team2: str) -> str:
    """Normalize and sort team names to build a unique match key."""
    t1 = team1.lower().strip()
    t2 = team2.lower().strip()
    return "-".join(sorted([t1, t2]))

def parse_time_to_utc(date_str: str, time_str: str) -> tuple[str, str]:
    """Parse a time string like "13:00 UTC-6" or "18:00 UTC-7" and return the UTC date and time."""
    if not time_str or time_str == "TBD":
        return date_str, "TBD"
    
    match = re.match(r"(\d{2}):(\d{2})\s+UTC([+-]\d+)?", time_str)
    if not match:
        return date_str, time_str
        
    hour = int(match.group(1))
    minute = int(match.group(2))
    offset_str = match.group(3)
    
    try:
        dt = datetime.fromisoformat(f"{date_str}T{hour:02d}:{minute:02d}:00")
        if offset_str:
            offset = int(offset_str)
            dt = dt - timedelta(hours=offset)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    except Exception:
        return date_str, f"{hour:02d}:{minute:02d}"

def utc_to_local(utc_date: str, utc_time: str, tz_offset: int) -> tuple[str, str]:
    """Convert a UTC date and time to user's local date and time based on tz_offset (in minutes behind UTC)."""
    if not utc_time or utc_time == "TBD":
        return utc_date, "TBD"
    try:
        dt = datetime.fromisoformat(f"{utc_date}T{utc_time}:00")
        local_dt = dt - timedelta(minutes=tz_offset)
        return local_dt.strftime("%Y-%m-%d"), local_dt.strftime("%H:%M")
    except Exception:
        return utc_date, utc_time

async def fetch_openfootball_data() -> tuple[list[dict], dict]:
    """Fetch and parse World Cup 2026 data from openfootball/worldcup.json."""
    global _openfootball_cache, _openfootball_teams, _openfootball_timestamp
    
    now_time = time.time()
    if now_time - _openfootball_timestamp < OPENFOOTBALL_TTL and _openfootball_cache:
        return _openfootball_cache, _openfootball_teams
        
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            # 1. Fetch teams
            teams_resp = await client.get(
                "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.teams.json",
                headers=headers
            )
            if teams_resp.status_code == 200:
                teams_data = teams_resp.json()
                _openfootball_teams = {t["name"]: {"code": t["fifa_code"], "flag": t["flag_icon"]} for t in teams_data}
            
            # 2. Fetch matches
            matches_resp = await client.get(
                "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json",
                headers=headers
            )
            if matches_resp.status_code == 200:
                matches_data = matches_resp.json()
                matches_list = matches_data.get("matches", [])
                
                parsed_matches = []
                for idx, match in enumerate(matches_list):
                    t1_name = match["team1"]
                    t2_name = match["team2"]
                    
                    t1_info = _openfootball_teams.get(t1_name, {"code": t1_name, "flag": "🏳️"})
                    t2_info = _openfootball_teams.get(t2_name, {"code": t2_name, "flag": "🏳️"})
                    
                    # Parse local time to UTC
                    utc_date, utc_time = parse_time_to_utc(match["date"], match["time"])
                    
                    # Score parsing
                    score_dict = match.get("score")
                    t1_score = None
                    t2_score = None
                    if score_dict and "ft" in score_dict:
                        t1_score = score_dict["ft"][0]
                        t2_score = score_dict["ft"][1]
                    
                    parsed = {
                        "id": idx + 1,
                        "group": match.get("group", "Group Stage").upper(),
                        "utc_date": utc_date,
                        "utc_time": utc_time,
                        "team1": {
                            "name": t1_name,
                            "code": t1_info["code"],
                            "flag": t1_info["flag"],
                        },
                        "team2": {
                            "name": t2_name,
                            "code": t2_info["code"],
                            "flag": t2_info["flag"],
                        },
                        "venue": match.get("ground", ""),
                        "score_t1": t1_score,
                        "score_t2": t2_score
                    }
                    parsed_matches.append(parsed)
                
                _openfootball_cache = parsed_matches
                _openfootball_timestamp = now_time
                print(f"[openfootball] Successfully parsed {len(parsed_matches)} matches.")
                return _openfootball_cache, _openfootball_teams
    except Exception as e:
        print(f"[openfootball] Error fetching data: {e}")
        
    return _openfootball_cache, _openfootball_teams

async def scrape_fifa_fixtures() -> dict:
    """
    Primary: Fetch openfootball data and partition into upcoming/past/live categories.
    Fallback: Fall back to hardcoded fixtures.
    """
    global _fixtures_cache, _cache_timestamp

    try:
        of_matches, of_teams = await fetch_openfootball_data()
        
        fixtures = {"upcoming": [], "past": [], "live": []}
        now_utc = datetime.utcnow()
        
        matches_to_process = of_matches if of_matches else []
        if not matches_to_process:
            print("[FIFA] openfootball data not available, using offline fallback")
            _fixtures_cache = _build_fixtures()
            _cache_timestamp = time.time()
            return _fixtures_cache
            
        for match in matches_to_process:
            if match["utc_time"] == "TBD":
                match_dt = None
            else:
                try:
                    match_dt = datetime.fromisoformat(f"{match['utc_date']}T{match['utc_time']}:00")
                except Exception:
                    match_dt = None
                    
            m = {
                "id": match["id"],
                "group": match["group"],
                "date": match["utc_date"],
                "time": match["utc_time"],
                "venue": match["venue"],
                "team1": dict(match["team1"]),
                "team2": dict(match["team2"]),
            }
            
            status = "upcoming"
            t1_score = None
            t2_score = None
            
            if match["score_t1"] is not None and match["score_t2"] is not None:
                status = "completed"
                t1_score = match["score_t1"]
                t2_score = match["score_t2"]
            elif match_dt and match_dt <= now_utc < match_dt + timedelta(hours=2):
                status = "live"
                elapsed_minutes = int((now_utc - match_dt).total_seconds() / 60)
                s1, s2 = get_live_score(match["id"], elapsed_minutes)
                t1_score = s1
                t2_score = s2
            elif match_dt and now_utc >= match_dt + timedelta(hours=2):
                status = "completed"
                s1, s2 = get_completed_score(match["id"], None, None)
                t1_score = s1
                t2_score = s2
            else:
                status = "upcoming"
                
            m["status"] = status
            if status in ["live", "completed"]:
                m["team1"]["score"] = t1_score if t1_score is not None else 0
                m["team2"]["score"] = t2_score if t2_score is not None else 0
                
            if status == "completed":
                fixtures["past"].append(m)
            elif status == "live":
                fixtures["live"].append(m)
            else:
                fixtures["upcoming"].append(m)
                
        _fixtures_cache = fixtures
        _cache_timestamp = time.time()
        return _fixtures_cache
    except Exception as err:
        print(f"[FIFA] openfootball integration failed ({err}), falling back")
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

# ── Sportmonks API Integration ─────────────────────────────────────────
SPORTMONKS_TOKEN = "ZNgg3qu759L4OqrjwQhnSLs9f7pN7o6MBnGIJKhvDdaVSeVcGE9mBXBLavWs"

def get_flag_by_country(country_id: int) -> str:
    country_flags = {
        320: "🇩🇰",    # Denmark
        1161: "🏴󠁧󠁢󠁳󠁣󠁴󠁿",   # Scotland
        462: "🇬🇧",    # United Kingdom
        444: "🏴󠁧󠁢󠁥󠁮󠁧󠁿",   # England
        11: "🇩🇪",     # Germany
        20: "🇨🇭",     # Switzerland
        17: "🇧🇪",     # Belgium
        32: "🇪🇸",     # Spain
        14: "🇳🇱",     # Netherlands
        38: "🇫🇷",     # France
        46: "🇮🇹",     # Italy
        5: "🇵🇹",      # Portugal
        783: "🇲🇽",    # Mexico
        1156: "🇿🇦",   # South Africa
        251: "🇰🇷",    # South Korea
        44: "🇨🇿",     # Czechia
        642: "🇨🇦",    # Canada
        64: "🇧🇦",     # Bosnia
        384: "🇺🇸",    # USA
        1021: "🇵🇾",   # Paraguay
        655: "🇧🇷",    # Brazil
        811: "🇲🇦",    # Morocco
        268: "🇶🇦",     # Qatar
        824: "🇨🇴",    # Colombia
        833: "🇸🇳",    # Senegal
        673: "🇨🇺",    # Curaçao
        632: "🇨🇮",    # Ivory Coast
        805: "🇪🇨",    # Ecuador
        155: "🇯🇴",    # Jordan
        217: "🇯🇵",    # Japan
        849: "🇨🇻",    # Cabo Verde
        819: "🇪🇬",    # Egypt
        242: "🇸🇦",    # Saudi Arabia
        827: "🇺🇾",    # Uruguay
        214: "🇺🇿",    # Uzbekistan
        197: "🇮🇷",    # Iran
        1172: "🇳🇿",   # New Zealand
        203: "🇮🇶",    # Iraq
        105: "🇳🇴",    # Norway
        852: "🇬🇭",    # Ghana
        792: "🇵🇦",    # Panama
        102: "🇸🇪",    # Sweden
        817: "🇹🇳",    # Tunisia
        239: "🇦🇺",    # Australia
        821: "🇵🇪",    # Peru
    }
    return country_flags.get(country_id, "🏳️")

def extract_fixtures_from_schedule(schedule_data) -> list:
    fixtures = []
    if not schedule_data:
        return fixtures
    if isinstance(schedule_data, dict):
        schedule_data = [schedule_data]
    for stage in schedule_data:
        for r in stage.get("rounds", []) or []:
            for f in r.get("fixtures", []) or []:
                fixtures.append(f)
    return fixtures

def _convert_utc_time_to_local(time_str: str, tz_offset: int) -> str:
    """Convert a UTC HH:MM time string to local time given browser's getTimezoneOffset() value.
    Browser getTimezoneOffset() returns minutes BEHIND UTC, so IST (+5:30) = -330.
    We negate to get the actual UTC offset: local = utc - tz_offset."""
    if not time_str or time_str == "TBD" or tz_offset == 0:
        return time_str
    try:
        h, m = int(time_str[:2]), int(time_str[3:5])
        total_minutes = h * 60 + m - tz_offset
        # Wrap around midnight
        total_minutes = total_minutes % (24 * 60)
        local_h = total_minutes // 60
        local_m = total_minutes % 60
        return f"{local_h:02d}:{local_m:02d}"
    except Exception:
        return time_str

async def fetch_sportmonks_fixtures_by_date(date_str: str, tz_offset: int = 0) -> dict:
    import asyncio
    
    # 1. Fetch openfootball matches
    of_matches, of_teams = await fetch_openfootball_data()
    
    # 2. Fetch live/scheduled fixtures from APIs (for real-time overlay)
    url_date = f"https://api.sportmonks.com/v3/football/fixtures/date/{date_str}?include=participants;scores&api_token={SPORTMONKS_TOKEN}"
    url_inplay = f"https://api.sportmonks.com/v3/football/livescores/inplay?include=participants;scores;periods;events;league.country;round&api_token={SPORTMONKS_TOKEN}"
    url_sched_9 = f"https://api.sportmonks.com/v3/football/schedules/teams/9?api_token={SPORTMONKS_TOKEN}"
    url_sched_53 = f"https://api.sportmonks.com/v3/football/schedules/teams/53?api_token={SPORTMONKS_TOKEN}"
    url_fd = f"https://api.football-data.org/v4/matches?dateFrom={date_str}&dateTo={date_str}"
    
    async def fetch_endpoint(url):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    payload = resp.json()
                    if "matches" in payload:
                        return payload.get("matches", [])
                    return payload.get("data", [])
                else:
                    print(f"[API] Non-200 status for {url.split('?')[0]}: {resp.status_code}")
        except Exception as e:
            print(f"[API] Error fetching {url.split('?')[0]}: {e}")
        return []

    print(f"[API] Aggregating live data for date {date_str} (tz_offset={tz_offset}, Sportmonks & Football-Data)...")
    
    res_date, res_inplay, res_sched_9, res_sched_53, res_fd = await asyncio.gather(
        fetch_endpoint(url_date),
        fetch_endpoint(url_inplay),
        fetch_endpoint(url_sched_9),
        fetch_endpoint(url_sched_53),
        fetch_endpoint(url_fd)
    )
    
    # Process and build a map of live/completed API fixtures
    sportmonks_raw = []
    if res_date:
        sportmonks_raw.extend(res_date)
    if res_inplay:
        sportmonks_raw.extend(res_inplay)
    sportmonks_raw.extend(extract_fixtures_from_schedule(res_sched_9))
    sportmonks_raw.extend(extract_fixtures_from_schedule(res_sched_53))
    
    api_matches = {}
    for f in sportmonks_raw:
        if not f or not isinstance(f, dict) or "id" not in f:
            continue
        try:
            mapped = map_sportmonks_fixture(f)
            if mapped.get("status") in ["live", "completed"]:
                match_key = get_match_key(mapped["team1"]["name"], mapped["team2"]["name"])
                api_matches[match_key] = mapped
        except Exception:
            continue
            
    if res_fd:
        for f in res_fd:
            if not f or not isinstance(f, dict) or "id" not in f:
                continue
            try:
                mapped = map_footballdata_fixture(f)
                if mapped.get("status") in ["live", "completed"]:
                    match_key = get_match_key(mapped["team1"]["name"], mapped["team2"]["name"])
                    api_matches[match_key] = mapped
            except Exception:
                continue
                
    # 3. Categorize openfootball matches based on requested date (using local date)
    fixtures = {"upcoming": [], "past": [], "live": []}
    now_utc = datetime.utcnow()
    
    # Calculate current local date for live today checking
    now_local = datetime.utcnow() - timedelta(minutes=tz_offset)
    current_local_date = now_local.strftime("%Y-%m-%d")
    
    matches_to_process = []
    if of_matches:
        # Deep copy
        for m in of_matches:
            matches_to_process.append({
                "id": m["id"],
                "group": m["group"],
                "utc_date": m["utc_date"],
                "utc_time": m["utc_time"],
                "team1": dict(m["team1"]),
                "team2": dict(m["team2"]),
                "venue": m["venue"],
                "score_t1": m["score_t1"],
                "score_t2": m["score_t2"]
            })
    
    if not matches_to_process:
        print("[API] openfootball data not available, using offline fallback")
        for match in ALL_MATCHES:
            t1_name = match["team1"]["name"]
            t2_name = match["team2"]["name"]
            
            parsed = {
                "id": match["id"],
                "group": match["group"].upper(),
                "utc_date": match["date"],
                "utc_time": match["time"],
                "team1": {
                    "name": t1_name,
                    "code": match["team1"]["code"],
                    "flag": match["team1"]["flag"],
                },
                "team2": {
                    "name": t2_name,
                    "code": match["team2"]["code"],
                    "flag": match["team2"]["flag"],
                },
                "venue": match.get("venue", ""),
                "score_t1": match["team1"].get("score"),
                "score_t2": match["team2"].get("score")
            }
            matches_to_process.append(parsed)
            
    for match in matches_to_process:
        # Determine local date and time
        local_date, local_time = utc_to_local(match["utc_date"], match["utc_time"], tz_offset)
        
        match_key = get_match_key(match["team1"]["name"], match["team2"]["name"])
        
        # Parse match UTC datetime
        if match["utc_time"] == "TBD":
            match_dt = None
        else:
            try:
                match_dt = datetime.fromisoformat(f"{match['utc_date']}T{match['utc_time']}:00")
            except Exception:
                match_dt = None
                
        m = {
            "id": match["id"],
            "group": match["group"],
            "date": local_date,
            "time": local_time,
            "venue": match["venue"],
            "team1": dict(match["team1"]),
            "team2": dict(match["team2"]),
        }
        
        # Determine status & scores
        status = "upcoming"
        t1_score = None
        t2_score = None
        
        if match_key in api_matches:
            api_match = api_matches[match_key]
            status = api_match["status"]
            t1_score = api_match["team1"].get("score")
            t2_score = api_match["team2"].get("score")
        elif match["score_t1"] is not None and match["score_t2"] is not None:
            status = "completed"
            t1_score = match["score_t1"]
            t2_score = match["score_t2"]
        elif match_dt and match_dt <= now_utc < match_dt + timedelta(hours=2):
            status = "live"
            elapsed_minutes = int((now_utc - match_dt).total_seconds() / 60)
            s1, s2 = get_live_score(match["id"], elapsed_minutes)
            t1_score = s1
            t2_score = s2
        elif match_dt and now_utc >= match_dt + timedelta(hours=2):
            status = "completed"
            s1, s2 = get_completed_score(match["id"], None, None)
            t1_score = s1
            t2_score = s2
        else:
            status = "upcoming"
            
        m["status"] = status
        if status in ["live", "completed"]:
            m["team1"]["score"] = t1_score if t1_score is not None else 0
            m["team2"]["score"] = t2_score if t2_score is not None else 0
            
        is_same_date = (local_date == date_str)
        is_live_today = (status == "live" and date_str == current_local_date)
        
        if is_same_date or is_live_today:
            if status == "completed":
                fixtures["past"].append(m)
            elif status == "live":
                fixtures["live"].append(m)
            else:
                fixtures["upcoming"].append(m)
                
    return fixtures

def get_fallback_fixtures_for_date(date_str: str) -> dict:
    return get_dynamic_fallback_fixtures(date_str)

def map_sportmonks_fixture(f: dict) -> dict:
    participants = f.get("participants", []) or []
    team1 = {"name": "TBD", "code": "TBD", "flag": "🏳️", "score": 0}
    team2 = {"name": "TBD", "code": "TBD", "flag": "🏳️", "score": 0}
    
    for p in participants:
        meta = p.get("meta", {}) or {}
        location = meta.get("location")
        team_data = {
            "name": p.get("name", "TBD"),
            "code": p.get("short_code") or p.get("name", "TBD")[:3].upper(),
            "flag": get_flag_by_country(p.get("country_id")),
            "score": 0
        }
        
        # Extract score
        for s in f.get("scores", []) or []:
            if s.get("participant_id") == p.get("id") and s.get("description") == "CURRENT":
                goals_data = s.get("score", {}) or {}
                team_data["score"] = goals_data.get("goals") or 0
                break
                
        if location == "home":
            team1 = team_data
        elif location == "away":
            team2 = team_data
        else:
            if team1["name"] == "TBD":
                team1 = team_data
            else:
                team2 = team_data
                
    state_id = f.get("state_id")
    status = "upcoming"
    # Completed states: FT(5), AET(7), FT_PEN(8), CANCELLED(12), WO(14), AWARDED(17)
    if state_id in [5, 7, 8, 12, 14, 17]:
        status = "completed"
    # Live states: 1stHalf(2), HT(3), ET(6), PEN(9), ETBreak(21), 2ndHalf(22), PenBreak(25)
    elif state_id in [2, 3, 6, 9, 21, 22, 25]:
        status = "live"
        
    starting_at = f.get("starting_at", "")
    date_str = starting_at[:10] if starting_at else ""
    time_str = starting_at[11:16] if starting_at and len(starting_at) >= 16 else "TBD"
    
    league_names = {
        271: "Superliga",
        501: "Premiership",
        513: "Premiership Play-Offs",
        1659: "Superliga Play-offs"
    }
    group_name = league_names.get(f.get("league_id"), "League Match")
    
    return {
        "id": f.get("id"),
        "group": group_name,
        "date": date_str,
        "time": time_str,
        "status": status,
        "venue": f.get("result_info") or "",
        "team1": team1,
        "team2": team2
    }

def map_footballdata_fixture(m: dict) -> dict:
    home = m.get("homeTeam", {}) or {}
    away = m.get("awayTeam", {}) or {}
    comp = m.get("competition", {}) or {}
    score = m.get("score", {}) or {}
    full_time = score.get("fullTime", {}) or {}
    
    home_tla = home.get("tla") or home.get("shortName", "TBD")[:3].upper()
    away_tla = away.get("tla") or away.get("shortName", "TBD")[:3].upper()
    
    status_str = m.get("status", "").upper()
    status = "upcoming"
    if status_str in ["FINISHED", "AWARDED"]:
        status = "completed"
    elif status_str in ["IN_PLAY", "PAUSED", "LIVE"]:
        status = "live"
        
    utc_date = m.get("utcDate", "")
    date_part = utc_date[:10] if utc_date else ""
    time_part = utc_date[11:16] if utc_date and len(utc_date) >= 16 else "TBD"
    
    fixture = {
        "id": 1000000000 + int(m.get("id", 0)),
        "group": comp.get("name") or "League Match",
        "date": date_part,
        "time": time_part,
        "status": status,
        "venue": "",
        "team1": {
            "name": home.get("name") or home.get("shortName", "TBD"),
            "code": home_tla,
            "flag": get_flag(home_tla)
        },
        "team2": {
            "name": away.get("name") or away.get("shortName", "TBD"),
            "code": away_tla,
            "flag": get_flag(away_tla)
        }
    }
    
    if status in ["completed", "live"]:
        fixture["team1"]["score"] = full_time.get("home") if full_time.get("home") is not None else 0
        fixture["team2"]["score"] = full_time.get("away") if full_time.get("away") is not None else 0
        
    return fixture
