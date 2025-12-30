"""
Betting Monitor MCP Server

Monitors line movements using The Odds API historical data.
Detects steam moves, significant line changes, and provides real-time alerts.
Supports MULTIPLE SPORTS.
"""

from mcp.server.fastmcp import FastMCP
import httpx
import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path

# Initialize FastMCP server
mcp = FastMCP("BettingMonitor")

# Configuration
API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Alert Configuration
# Time to clear alerts (in minutes). Default: 60 mins.
ALERT_TTL_MINUTES = int(os.getenv("ALERT_TTL_MINUTES", 60))

# Alert storage
ALERTS_FILE = DATA_DIR / "alerts.json"
OPENING_LINES_FILE = DATA_DIR / "opening_lines.json"
OPENING_PROPS_FILE = DATA_DIR / "opening_props.json"

# Thresholds for alerts (can be tuned per sport if needed)
SPREAD_MOVE_THRESHOLD = 1.0  # Points
TOTAL_MOVE_THRESHOLD = 1.5   # Points
ML_MOVE_THRESHOLD = 25       # American odds points
STEAM_MOVE_THRESHOLD = 1.5   # Points in < 30 min = steam
PROP_MOVE_THRESHOLD = 2.0    # Points/Yards for props

# Sport Emojis
SPORT_EMOJIS = {
    "americanfootball_nfl": "🏈",
    "americanfootball_ncaaf": "🏈",
    "basketball_nba": "🏀",
    "basketball_ncaab": "🏀",
    "baseball_mlb": "⚾",
    "icehockey_nhl": "🏒",
    "soccer": "⚽",
    "tennis": "🎾",
    "mma": "🥊",
    "boxing": "🥊",
    "golf": "⛳"
}


def load_json_file(filepath: Path) -> Dict:
    """Load JSON file or return empty dict."""
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_json_file(filepath: Path, data: Dict):
    """Save data to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def clean_old_alerts(data: Dict) -> Dict:
    """Move alerts older than ALERT_TTL_MINUTES to expired list."""
    alerts = data.get('alerts', [])
    expired = data.get('expired', [])

    if ALERT_TTL_MINUTES <= 0:
        return data

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=ALERT_TTL_MINUTES)
    valid_alerts = []

    # Limit expired list size
    if len(expired) > 500:
        expired = expired[:500]

    for alert in alerts:
        ts_str = alert.get('timestamp')
        if not ts_str:
            continue

        try:
            if ts_str.endswith('Z'):
                ts_str = ts_str.replace('Z', '+00:00')
            alert_time = datetime.fromisoformat(ts_str)

            if alert_time > cutoff:
                valid_alerts.append(alert)
            else:
                # Move to expired
                expired.insert(0, alert)
        except:
            continue

    data['alerts'] = valid_alerts
    data['expired'] = expired
    return data


def get_alerts() -> List[Dict]:
    """Get stored alerts, filtering out old ones."""
    data = load_json_file(ALERTS_FILE)

    # Clean old alerts on read
    data = clean_old_alerts(data)

    # Save back to disk to persist expiration
    save_json_file(ALERTS_FILE, data)

    return data.get('alerts', [])


def save_alert(alert: Dict):
    """Save a new alert."""
    data = load_json_file(ALERTS_FILE)

    # Clean first
    data = clean_old_alerts(data)

    alerts = data.get('alerts', [])
    expired = data.get('expired', [])

    # Check if this is a known alert (active OR expired)
    game_id = alert.get('game_id')
    alert_type = alert.get('type')

    # Add sport emoji to the alert object for convenience
    if 'sport' in alert:
        alert['sport_emoji'] = SPORT_EMOJIS.get(alert['sport'], "🎮")

    # 1. Check Active Alerts
    for existing in alerts:
        if (existing.get('game_id') == game_id and
            existing.get('type') == alert_type):

            # Preserve timestamp
            alert['timestamp'] = existing.get('timestamp')

            # Update in place
            existing.update(alert)
            save_json_file(ALERTS_FILE, data)
            print(f"DEBUG: Updated active alert for {alert.get('game')}")
            return

    # 2. Check Expired Alerts
    for existing in expired:
        if (existing.get('game_id') == game_id and
            existing.get('type') == alert_type):

            # It's expired. Check if it's "Significantly" different?
            # For now, we assume if it's the same type/game, it's the same drift.
            # We simply IGNORE it so it doesn't pop up again.
            print(f"DEBUG: Ignored expired alert for {alert.get('game')}")
            return

    # 3. It's New
    print(f"DEBUG: New alert for {alert.get('game')}")
    alerts.insert(0, alert)
    data['alerts'] = alerts[:200]

    save_json_file(ALERTS_FILE, data)


@mcp.tool()
async def snapshot_current_lines(sport: str = "americanfootball_nfl") -> str:
    """
    [SNAPSHOT] Save CURRENT lines as the baseline for future comparison for a specific sport.
    Use this if historical data is unavailable or to start tracking from NOW.
    """
    if not API_KEY:
        return "ERROR: ODDS_API_KEY not set."

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            url = f"{BASE_URL}/sports/{sport}/odds"
            params = {
                "apiKey": API_KEY,
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american"
            }

            resp = await client.get(url, params=params)
            resp.raise_for_status()
            games = resp.json()

            if not games:
                return f"No current odds available to snapshot for {sport}."

            timestamp = datetime.now(timezone.utc).isoformat()

            # Store opening lines (using current as baseline)
            opening_lines = {}
            output = f"[BASELINE SNAPSHOT TAKEN for {sport} at {timestamp}]\n"
            output += f"Games: {len(games)}\n"
            output += "=" * 50 + "\n\n"

            for game in games:
                game_id = game.get('id')
                home = game.get('home_team')
                away = game.get('away_team')
                commence = game.get('commence_time')

                opening_lines[game_id] = {
                    'home': home,
                    'away': away,
                    'commence_time': commence,
                    'timestamp': timestamp
                }

                bookmakers = game.get('bookmakers', [])
                if bookmakers:
                    bookie = bookmakers[0]
                    for market in bookie['markets']:
                        if market['key'] == 'spreads':
                            for outcome in market['outcomes']:
                                if outcome['name'] == home:
                                    opening_lines[game_id]['spread_home'] = outcome.get('point', 0)
                                else:
                                    opening_lines[game_id]['spread_away'] = outcome.get('point', 0)
                        elif market['key'] == 'totals':
                            if market['outcomes']:
                                opening_lines[game_id]['total'] = market['outcomes'][0].get('point')
                        elif market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                if outcome['name'] == home:
                                    opening_lines[game_id]['ml_home'] = outcome.get('price')
                                else:
                                    opening_lines[game_id]['ml_away'] = outcome.get('price')

                # Format output (brief)
                spread_home = opening_lines[game_id].get('spread_home', 'N/A')
                output += f"{away} @ {home}: {home} {spread_home}\n"

            # Load existing file to preserve other sports
            all_openings = load_json_file(OPENING_LINES_FILE)

            # Update ONLY this sport
            all_openings[sport] = {
                'timestamp': timestamp,
                'games': opening_lines,
                'type': 'live_snapshot'
            }

            save_json_file(OPENING_LINES_FILE, all_openings)

            return output

        except Exception as e:
            return f"Error taking snapshot: {str(e)}"


@mcp.tool()
async def get_opening_lines(sport: str = "americanfootball_nfl", hours_ago: int = 48) -> str:
    """
    [HISTORICAL] Get opening lines from X hours ago using historical odds API.
    If historical API fails (401), falls back to taking a CURRENT snapshot.
    """
    if not API_KEY:
        return "ERROR: ODDS_API_KEY not set."

    # Calculate timestamp for opening lines
    open_time = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    date_param = open_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            url = f"{BASE_URL}/historical/sports/{sport}/odds"
            params = {
                "apiKey": API_KEY,
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american",
                "date": date_param
            }

            resp = await client.get(url, params=params)

            # Handle 401 specifically for historical access
            if resp.status_code == 401:
                return await snapshot_current_lines(sport)

            resp.raise_for_status()
            result = resp.json()

            timestamp = result.get('timestamp', date_param)
            games = result.get('data', [])

            if not games:
                return f"No historical data available for {sport} at {date_param}."

            # Store opening lines
            opening_lines = {}
            output = f"[OPENING LINES for {sport} from {timestamp}]\n"
            output += f"Games: {len(games)}\n"
            output += "=" * 50 + "\n\n"

            for game in games:
                game_id = game.get('id')
                home = game.get('home_team')
                away = game.get('away_team')
                commence = game.get('commence_time')

                opening_lines[game_id] = {
                    'home': home,
                    'away': away,
                    'commence_time': commence,
                    'timestamp': timestamp
                }

                bookmakers = game.get('bookmakers', [])
                if bookmakers:
                    bookie = bookmakers[0]
                    for market in bookie['markets']:
                        if market['key'] == 'spreads':
                            for outcome in market['outcomes']:
                                if outcome['name'] == home:
                                    opening_lines[game_id]['spread_home'] = outcome.get('point', 0)
                                else:
                                    opening_lines[game_id]['spread_away'] = outcome.get('point', 0)
                        elif market['key'] == 'totals':
                            if market['outcomes']:
                                opening_lines[game_id]['total'] = market['outcomes'][0].get('point')
                        elif market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                if outcome['name'] == home:
                                    opening_lines[game_id]['ml_home'] = outcome.get('price')
                                else:
                                    opening_lines[game_id]['ml_away'] = outcome.get('price')

                # Format output
                spread_home = opening_lines[game_id].get('spread_home', 'N/A')
                total = opening_lines[game_id].get('total', 'N/A')
                output += f"{away} @ {home}: {spread_home} | {total}\n"

            # Load existing file to preserve other sports
            all_openings = load_json_file(OPENING_LINES_FILE)

            # Update ONLY this sport
            all_openings[sport] = {
                'timestamp': timestamp,
                'games': opening_lines,
                'type': 'historical'
            }

            save_json_file(OPENING_LINES_FILE, all_openings)

            output += f"\n[Opening lines saved for {len(opening_lines)} games]"
            return output

        except Exception as e:
            # Fallback to live snapshot on error
            return await snapshot_current_lines(sport)


@mcp.tool()
async def compare_to_opening(sport: str = "americanfootball_nfl") -> str:
    """
    [LINE MOVEMENT] Compare current lines to opening lines for a specific sport.
    Returns all games with significant movement.
    Must run get_opening_lines(sport) first to establish baseline.
    """
    if not API_KEY:
        return "ERROR: ODDS_API_KEY not set."

    # Load opening lines
    all_openings = load_json_file(OPENING_LINES_FILE)
    sport_data = all_openings.get(sport)

    if not sport_data:
        return f"ERROR: No opening lines saved for {sport}. Run get_opening_lines(sport='{sport}') first."

    opening_lines = sport_data.get('games', {})
    open_timestamp = sport_data.get('timestamp', 'Unknown')

    # Get current lines
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            url = f"{BASE_URL}/sports/{sport}/odds"
            params = {
                "apiKey": API_KEY,
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american"
            }

            resp = await client.get(url, params=params)
            resp.raise_for_status()
            games = resp.json()

            if not games:
                return f"No current odds available for {sport}."

            movements = []
            now = datetime.now(timezone.utc).isoformat()

            for game in games:
                game_id = game.get('id')
                home = game.get('home_team')
                away = game.get('away_team')

                if game_id not in opening_lines:
                    continue

                opening = opening_lines[game_id]
                bookmakers = game.get('bookmakers', [])
                if not bookmakers:
                    continue

                current = {}
                bookie = bookmakers[0]
                for market in bookie['markets']:
                    if market['key'] == 'spreads':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home:
                                current['spread_home'] = outcome.get('point', 0)
                            else:
                                current['spread_away'] = outcome.get('point', 0)
                    elif market['key'] == 'totals':
                        if market['outcomes']:
                            current['total'] = market['outcomes'][0].get('point')
                    elif market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home:
                                current['ml_home'] = outcome.get('price')
                            else:
                                current['ml_away'] = outcome.get('price')

                game_movements = []

                # Check spread movement
                if 'spread_home' in current and 'spread_home' in opening:
                    spread_move = current['spread_home'] - opening['spread_home']
                    if abs(spread_move) >= SPREAD_MOVE_THRESHOLD:
                        significance = "🔴 MAJOR" if abs(spread_move) >= 2 else "🟡 Notable"
                        game_movements.append({
                            'type': 'SPREAD',
                            'description': f"{significance}: {home} spread moved {spread_move:+.1f} pts",
                            'opening': opening['spread_home'],
                            'current': current['spread_home'],
                            'change': spread_move
                        })

                        # Save alert
                        save_alert({
                            'type': 'SPREAD_MOVE',
                            'game_id': game_id,
                            'game': f"{away} @ {home}",
                            'movement': f"Spread moved {spread_move:+.1f} pts",
                            'opening': opening['spread_home'],
                            'current': current['spread_home'],
                            'significance': 'HIGH' if abs(spread_move) >= 2 else 'MEDIUM',
                            'timestamp': now,
                            'sport': sport
                        })

                # Check total movement
                if 'total' in current and 'total' in opening:
                    total_move = current['total'] - opening['total']
                    if abs(total_move) >= TOTAL_MOVE_THRESHOLD:
                        direction = "UP" if total_move > 0 else "DOWN"
                        significance = "🔴 MAJOR" if abs(total_move) >= 3 else "🟡 Notable"
                        game_movements.append({
                            'type': 'TOTAL',
                            'description': f"{significance}: Total moved {total_move:+.1f} pts {direction}",
                            'opening': opening['total'],
                            'current': current['total'],
                            'change': total_move
                        })

                        save_alert({
                            'type': 'TOTAL_MOVE',
                            'game_id': game_id,
                            'game': f"{away} @ {home}",
                            'movement': f"Total moved {total_move:+.1f} pts {direction}",
                            'opening': opening['total'],
                            'current': current['total'],
                            'significance': 'HIGH' if abs(total_move) >= 3 else 'MEDIUM',
                            'timestamp': now,
                            'sport': sport
                        })

                # Check moneyline movement
                if 'ml_home' in current and 'ml_home' in opening:
                    ml_move = current['ml_home'] - opening['ml_home']
                    if abs(ml_move) >= ML_MOVE_THRESHOLD:
                        direction = "longer" if ml_move > 0 else "shorter"
                        game_movements.append({
                            'type': 'MONEYLINE',
                            'description': f"🟡 {home} ML moved {ml_move:+d} ({direction})",
                            'opening': opening['ml_home'],
                            'current': current['ml_home'],
                            'change': ml_move
                        })

                if game_movements:
                    movements.append({
                        'game': f"{away} @ {home}",
                        'game_id': game_id,
                        'movements': game_movements
                    })

            # Format output
            if not movements:
                return f"[LINE MOVEMENT CHECK - {sport} {SPORT_EMOJIS.get(sport, '')}]\nNo significant movements detected."

            output = f"[🚨 LINE MOVEMENT REPORT - {sport} {SPORT_EMOJIS.get(sport, '🎮')}]\n"
            output += f"Significant Movements: {len(movements)} games\n"
            output += "=" * 50 + "\n\n"

            for m in movements:
                output += f"📊 {m['game']}\n"
                for mov in m['movements']:
                    output += f"   {mov['description']}\n"
                    output += f"   Open: {mov['opening']} → Current: {mov['current']}\n"
                output += "\n"

            return output

        except Exception as e:
            return f"Error comparing lines: {str(e)}"


@mcp.tool()
async def detect_steam_moves(sport: str = "americanfootball_nfl") -> str:
    """
    [STEAM DETECTION] Check for rapid line movement in the last 30 minutes for a specific sport.
    Steam = 1.5+ point move in under 30 minutes.
    """
    if not API_KEY:
        return "ERROR: ODDS_API_KEY not set."

    # Get lines from 30 minutes ago
    past_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    date_param = past_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Get historical (30 min ago)
            hist_url = f"{BASE_URL}/historical/sports/{sport}/odds"
            hist_params = {
                "apiKey": API_KEY,
                "regions": "us",
                "markets": "spreads,totals",
                "oddsFormat": "american",
                "date": date_param
            }

            hist_resp = await client.get(hist_url, params=hist_params)
            hist_resp.raise_for_status()
            hist_result = hist_resp.json()
            hist_games = {g['id']: g for g in hist_result.get('data', [])}

            # Get current
            curr_url = f"{BASE_URL}/sports/{sport}/odds"
            curr_params = {
                "apiKey": API_KEY,
                "regions": "us",
                "markets": "spreads,totals",
                "oddsFormat": "american"
            }

            curr_resp = await client.get(curr_url, params=curr_params)
            curr_resp.raise_for_status()
            curr_games = curr_resp.json()

            steam_moves = []
            now = datetime.now(timezone.utc).isoformat()

            for game in curr_games:
                game_id = game.get('id')
                home = game.get('home_team')
                away = game.get('away_team')

                if game_id not in hist_games:
                    continue

                hist_game = hist_games[game_id]

                # Extract spreads
                curr_spread = None
                hist_spread = None

                for bookie in game.get('bookmakers', [])[:1]:
                    for market in bookie['markets']:
                        if market['key'] == 'spreads':
                            for outcome in market['outcomes']:
                                if outcome['name'] == home:
                                    curr_spread = outcome.get('point', 0)

                for bookie in hist_game.get('bookmakers', [])[:1]:
                    for market in bookie['markets']:
                        if market['key'] == 'spreads':
                            for outcome in market['outcomes']:
                                if outcome['name'] == home:
                                    hist_spread = outcome.get('point', 0)

                if curr_spread is not None and hist_spread is not None:
                    move = curr_spread - hist_spread
                    if abs(move) >= STEAM_MOVE_THRESHOLD:
                        steam_moves.append({
                            'game': f"{away} @ {home}",
                            'game_id': game_id,
                            'spread_30min_ago': hist_spread,
                            'spread_now': curr_spread,
                            'move': move,
                            'direction': 'toward ' + home if move < 0 else 'away from ' + home
                        })

                        # Save steam alert
                        save_alert({
                            'type': 'STEAM_MOVE',
                            'game_id': game_id,
                            'game': f"{away} @ {home}",
                            'movement': f"🚨 STEAM: {move:+.1f} pts in 30 min!",
                            'before': hist_spread,
                            'after': curr_spread,
                            'significance': 'CRITICAL',
                            'timestamp': now,
                            'sport': sport
                        })

            if not steam_moves:
                return f"[STEAM DETECTION - {sport} {SPORT_EMOJIS.get(sport, '')}]\nNo steam moves detected."

            output = f"[🚨🚨 STEAM MOVE ALERT - {sport} {SPORT_EMOJIS.get(sport, '🎮')} 🚨🚨]\n"
            output += f"Detected {len(steam_moves)} steam move(s) in last 30 min!\n"
            output += "=" * 50 + "\n\n"

            for sm in steam_moves:
                output += f"⚡ {sm['game']}\n"
                output += f"   Movement: {sm['move']:+.1f} pts ({sm['direction']})\n\n"

            return output

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return f"[STEAM DETECTION - {sport}] Skipped: Historical data access required (401)."
            return f"Error detecting steam: {str(e)}"

        except Exception as e:
            return f"Error detecting steam: {str(e)}"


@mcp.tool()
async def snapshot_props(sport: str = "americanfootball_nfl", limit_games: int = 10) -> str:
    """
    [PROPS SNAPSHOT] Save current player props as baseline.
    Limits based on sport priority (NFL gets more coverage).
    """
    if not API_KEY:
        return "ERROR: ODDS_API_KEY not set."

    # Smart limits based on sport importance/volume
    if "nfl" in sport:
        limit_games = 16 # Cover full slate
    elif "ncaaf" in sport:
        limit_games = 10 # Top matchups
    elif "nba" in sport:
        limit_games = 5  # Key games
    else:
        limit_games = 3  # Others

    # Determine key markets based on sport
    markets = "player_points" # Default
    if "nfl" in sport or "ncaaf" in sport:
        markets = "player_pass_yds,player_rush_yds"
    elif "nba" in sport or "ncaab" in sport:
        markets = "player_points,player_rebounds,player_assists"
    elif "mlb" in sport:
        markets = "pitcher_strikeouts"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 1. Get upcoming games first
            url = f"{BASE_URL}/sports/{sport}/events"
            resp = await client.get(url, params={"apiKey": API_KEY, "commenceTimeFrom": datetime.now(timezone.utc).isoformat()})

            if resp.status_code != 200:
                return f"Error fetching events: {resp.status_code}"

            events = resp.json()
            # Sort by time and take next few
            events.sort(key=lambda x: x.get('commence_time'))
            target_events = events[:limit_games]

            if not target_events:
                return f"No upcoming games found for {sport}."

            # 2. Fetch props for each event
            props_data = {}
            count = 0

            for event in target_events:
                game_id = event['id']
                matchup = f"{event['away_team']} @ {event['home_team']}"

                odds_resp = await client.get(
                    f"{BASE_URL}/sports/{sport}/events/{game_id}/odds",
                    params={"apiKey": API_KEY, "regions": "us", "markets": markets, "oddsFormat": "american"}
                )

                if odds_resp.status_code == 200:
                    data = odds_resp.json()
                    bookmakers = data.get('bookmakers', [])
                    if bookmakers:
                        # Use first bookmaker (consensus/market leader)
                        bookie = bookmakers[0]

                        game_props = {}
                        for market in bookie['markets']:
                            market_key = market['key']
                            for outcome in market['outcomes']:
                                # Key: Player Name + Market (e.g. "Patrick Mahomes_player_pass_yds")
                                # Use description or name
                                player = outcome.get('description', outcome.get('name'))
                                point = outcome.get('point')
                                if point:
                                    key = f"{player}_{market_key}"
                                    game_props[key] = {
                                        'player': player,
                                        'market': market_key,
                                        'line': point,
                                        'odds': outcome.get('price')
                                    }

                        props_data[game_id] = {
                            'matchup': matchup,
                            'props': game_props
                        }
                        count += len(game_props)

            # Save to file
            all_props = load_json_file(OPENING_PROPS_FILE)
            all_props[sport] = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'games': props_data
            }
            save_json_file(OPENING_PROPS_FILE, all_props)

            return f"[PROPS SNAPSHOT - {sport}]\nTracked {len(props_data)} games, {count} prop lines."

        except Exception as e:
            return f"Error snapshotting props: {str(e)}"


@mcp.tool()
async def compare_props(sport: str = "americanfootball_nfl") -> str:
    """
    [PROP MOVEMENT] Compare current props to baseline.
    """
    if not API_KEY:
        return "ERROR: ODDS_API_KEY not set."

    all_props = load_json_file(OPENING_PROPS_FILE)
    sport_data = all_props.get(sport)

    if not sport_data:
        return f"No baseline props found for {sport}. Run snapshot_props first."

    opening_games = sport_data.get('games', {})
    timestamp = sport_data.get('timestamp')

    # Determine key markets (same logic)
    markets = "player_points"
    if "nfl" in sport or "ncaaf" in sport:
        markets = "player_pass_yds,player_rush_yds"
    elif "nba" in sport or "ncaab" in sport:
        markets = "player_points,player_rebounds,player_assists"
    elif "mlb" in sport:
        markets = "pitcher_strikeouts"

    movements = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for game_id, game_data in opening_games.items():
            try:
                # Fetch current
                odds_resp = await client.get(
                    f"{BASE_URL}/sports/{sport}/events/{game_id}/odds",
                    params={"apiKey": API_KEY, "regions": "us", "markets": markets, "oddsFormat": "american"}
                )

                if odds_resp.status_code != 200: continue

                data = odds_resp.json()
                bookmakers = data.get('bookmakers', [])
                if not bookmakers: continue

                bookie = bookmakers[0]
                opening_props = game_data.get('props', {})

                for market in bookie['markets']:
                    market_key = market['key']
                    for outcome in market['outcomes']:
                        player = outcome.get('description', outcome.get('name'))
                        point = outcome.get('point')
                        if not point: continue

                        key = f"{player}_{market_key}"
                        if key in opening_props:
                            open_line = opening_props[key]['line']
                            diff = point - open_line

                            if abs(diff) >= PROP_MOVE_THRESHOLD:
                                move_str = f"{player} {market_key}: {open_line} -> {point} ({diff:+.1f})"
                                movements.append({
                                    'game': game_data['matchup'],
                                    'desc': move_str,
                                    'significance': 'HIGH' if abs(diff) >= 3 else 'MEDIUM'
                                })

                                # Save alert
                                save_alert({
                                    'type': 'PROP_MOVE',
                                    'game_id': game_id,
                                    'game': game_data['matchup'],
                                    'movement': move_str,
                                    'significance': 'HIGH' if abs(diff) >= 3 else 'MEDIUM',
                                    'timestamp': datetime.now(timezone.utc).isoformat(),
                                    'sport': sport
                                })
            except:
                continue

    if not movements:
        return f"[PROP CHECK - {sport} {SPORT_EMOJIS.get(sport, '')}]\nNo significant prop movements vs {timestamp}."

    output = f"[🚨 PROP ALERTS - {sport} {SPORT_EMOJIS.get(sport, '🎮')}]\n"
    for m in movements:
        output += f"⚡ {m['game']}: {m['desc']}\n"

    return output


@mcp.tool()
async def get_recent_alerts(limit: int = 20) -> str:
    """
    [ALERTS] Get recent line movement and steam alerts.
    """
    alerts = get_alerts()

    if not alerts:
        return "No alerts in history."

    alerts = alerts[:limit]

    output = f"[🔔 RECENT ALERTS - Last {len(alerts)}]\n"
    output += "=" * 50 + "\n\n"

    for alert in alerts:
        timestamp = alert.get('timestamp', 'Unknown')
        sport = alert.get('sport', 'Unknown')

        # Get sport emoji
        sport_emoji = SPORT_EMOJIS.get(sport, "🎮") # Default to controller if unknown

        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime("%m/%d %I:%M%p")
        except:
            time_str = timestamp[:16]

        significance = alert.get('significance', 'MEDIUM')
        if significance == 'CRITICAL': emoji = "🚨"
        elif significance == 'HIGH': emoji = "🔴"
        else: emoji = "🟡"

        output += f"{emoji} [{time_str}] {alert.get('type', 'ALERT')} ({sport_emoji} {sport})\n"
        output += f"   {alert.get('game', 'Unknown')}\n"
        output += f"   {alert.get('movement', 'No details')}\n\n"

    return output


@mcp.tool()
def clear_alerts() -> str:
    """Clear all stored alerts."""
    try:
        if ALERTS_FILE.exists():
            ALERTS_FILE.unlink()
        return "Alert history cleared successfully."
    except Exception as e:
        return f"Error clearing alerts: {str(e)}"


if __name__ == "__main__":
    mcp.run()
