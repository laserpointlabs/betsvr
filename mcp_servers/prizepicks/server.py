from mcp.server.fastmcp import FastMCP
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Initialize FastMCP server
mcp = FastMCP("PrizePicksData")

# Data location
DATA_DIR = Path(__file__).parent / "data"
PROJECTIONS_FILE = DATA_DIR / "projections.json"

def load_projections() -> Dict[str, Any]:
    """Load projections from the local JSON file uploaded by the client."""
    if PROJECTIONS_FILE.exists():
        try:
            with open(PROJECTIONS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading projections file: {e}")
    return {}

@mcp.tool()
async def get_prizepicks_props(sport: str = "NFL", player_name: str = None, stat_type: str = None) -> str:
    """
    Get PrizePicks player props from crowdsourced data.

    Args:
        sport: Sport name (e.g., "NBA", "NFL", "CFB", "CBB", "NHL").
        player_name: Filter by player name.
        stat_type: Filter by stat (e.g. "Points", "Rebounds").
    """
    data = load_projections()
    if not data:
        return "No PrizePicks data available. Please ensure the frontend app is open to sync data."

    # Parse data
    raw_projections = data.get('data', [])
    included = data.get('included', [])

    # Build lookups
    leagues = {x['id']: x['attributes']['name'] for x in included if x['type'] == 'league'}
    players = {x['id']: x['attributes']['name'] for x in included if x['type'] == 'new_player'}

    # Normalize sport input
    sport_upper = sport.upper()
    sport_map = {"NCAAF": "CFB", "NCAAB": "CBB", "NCAAM": "CBB"}
    target_sport = sport_map.get(sport_upper, sport_upper)

    filtered_props = []

    for p in raw_projections:
        attrs = p.get('attributes', {})
        rels = p.get('relationships', {})

        # Get League
        league_id = rels.get('league', {}).get('data', {}).get('id')
        league_name = leagues.get(league_id, "Unknown")

        if league_name != target_sport:
            continue

        # Get Player
        player_id = rels.get('new_player', {}).get('data', {}).get('id')
        p_name = players.get(player_id, "Unknown Player")

        # Filters
        if player_name and player_name.lower() not in p_name.lower():
            continue

        stat = attrs.get('stat_type', 'Unknown')
        if stat_type and stat_type.lower() not in stat.lower():
            continue

        filtered_props.append({
            'player': p_name,
            'stat': stat,
            'line': attrs.get('line_score'),
            'type': attrs.get('board_time'), # Use as indicator
            'desc': attrs.get('description')
        })

    if not filtered_props:
        return f"No props found for {target_sport} matching your criteria."

    # Format Output
    output = f"[PRIZEPICKS PROPS - {target_sport}]\n"
    output += f"Found {len(filtered_props)} props.\n"
    output += "=" * 50 + "\n\n"

    # Group by player
    by_player = {}
    for p in filtered_props:
        if p['player'] not in by_player:
            by_player[p['player']] = []
        by_player[p['player']].append(p)

    count = 0
    for player, props in by_player.items():
        output += f"**{player}**\n"
        for prop in props:
            output += f"  - {prop['stat']}: {prop['line']}\n"
        output += "\n"
        count += 1
        if count >= 20: # Limit output size
            output += "... (more players hidden) ...\n"
            break

    return output.strip()

@mcp.tool()
def prizepicks_strategy() -> Dict[str, str]:
    """Get tips for building PrizePicks lineups."""
    return {
        "Correlation": "Stack QB + WR (Over/Over). Or QB Over / WR Under (if spreading usage).",
        "Defense": "Target props against weak defenses (use get_team_stats to check).",
        "Blowout Risk": "Avoid Overs for stars in games with massive spreads (bench risk)."
    }

if __name__ == "__main__":
    mcp.run()
