# PRIZEPICKS DATA - SETUP REQUIRED

## Status: ⚠️ Blocked (403 Forbidden)

The PrizePicks internal API (`api.prizepicks.com/projections`) is blocking automated requests due to Cloudflare protection.

## Solutions (Choose One):

### Option 1: Third-Party Data Provider (Recommended for Production)
Use a paid service that scrapes PrizePicks data on your behalf:
- **OpticOdds** (https://opticodds.com) - $99-299/month
- **Betstamp Pro** (https://betstamp.app) - Pricing varies
- **OddsJam** (https://oddsjam.com) - Has PrizePicks props

### Option 2: Manual Data Entry
Create static markdown files with common props that update daily:
```markdown
# prizepicks_props_2025-12-08.md
## Patrick Mahomes
- Passing Yards: 275.5
- Passing TDs: 2.5

## Travis Kelce
- Receiving Yards: 65.5
- Receptions: 5.5
```

Then use the `betting_context` server (already working) to read these files.

### Option 3: Advanced Scraping (Not Recommended - TOS Violation)
Use Selenium with Chrome to bypass Cloudflare, but this:
- Violates PrizePicks Terms of Use
- Requires constant maintenance
- Risk of IP ban

## Current Workaround
For now, the system will return an error when trying to fetch PrizePicks data. Users can still ask about **parlay strategy** and **prop betting concepts** using the betting guides.
