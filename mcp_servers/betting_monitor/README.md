# Betting Monitor MCP

This service provides real-time monitoring of betting lines and player props using **The Odds API**.

## Features

### 1. Line Movement Alerts
- Tracks **Spreads**, **Totals**, and **Moneylines** for all major sports.
- Alerts on significant moves (e.g., Spread > 1.0 pt, Total > 1.5 pts).
- **Steam Detection**: Identifies rapid moves (> 1.5 pts in 30 mins) indicating sharp action.

### 2. Player Prop Monitoring
- Tracks key player props for the **Top 3 upcoming games** per sport to save quota.
- Markets monitored:
  - **NFL/NCAAF**: Passing Yards, Rushing Yards
  - **NBA/NCAAB**: Points, Rebounds, Assists
  - **MLB**: Pitcher Strikeouts
- Alerts when a prop line moves by **2.0+ points/yards**.

### 3. Alert Management
- **Alert TTL**: Alerts automatically expire after `ALERT_TTL_MINUTES` (default 60).
- **Deduplication**: Updates existing alerts if the movement persists, preserving the original timestamp.
- **Sound/Vibrate**: Frontend plays notification sound on new alerts.

## Configuration

Set in `.env` or `docker-compose.yml`:

- `ODDS_API_KEY`: Your API key (Paid plan required for Props/Historical).
- `ALERT_TTL_MINUTES`: Minutes before an alert is removed (default 60).

## Usage

The monitoring loop runs automatically in `api_gateway`. You can also manually trigger tools via LLM:

- "Check for line movements" -> `compare_to_opening()`
- "Any steam moves?" -> `detect_steam_moves()`
- "Analyze this alert" -> Uses `get_odds`, `get_injuries`, `get_game_weather`.
