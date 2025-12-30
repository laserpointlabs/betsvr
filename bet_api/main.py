import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from mcp_manager import mcp_manager

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("bet_api")


LM_API_BASE_URL = os.getenv("LM_API_BASE_URL", "https://lmapi.laserpointlabs.com").rstrip(
    "/"
)


def _get_auth_header(request: Request) -> str:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (missing Authorization header)",
        )
    return auth


def _extract_bearer_token(auth_header: str) -> str:
    """
    Return the token portion from an Authorization header.
    Accepts either "Bearer <token>" or "<token>" (legacy).
    """
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return auth_header.strip()


async def require_valid_token(request: Request) -> str:
    """
    Validate the caller's Bearer token by asking lmsvr to perform an authenticated call.
    We intentionally do NOT store or manage keys in betsvr.
    """
    auth = _get_auth_header(request)
    token = _extract_bearer_token(auth)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # If this looks like a device token, validate via /api/verify-device (no auth header).
            if token.startswith("dt_"):
                resp = await client.post(
                    f"{LM_API_BASE_URL}/api/verify-device",
                    json={"device_token": token},
                )
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"LM provider validation failed: {resp.status_code}",
                    )
                data = resp.json()
                if data.get("valid"):
                    return auth
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                )

            # Otherwise treat it as a normal API key and validate via an authenticated call.
            resp = await client.get(
                f"{LM_API_BASE_URL}/api/models", headers={"Authorization": auth}
            )
            if resp.status_code == 200:
                return auth
            if resp.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"LM provider validation failed: {resp.status_code}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LM provider unreachable: {str(e)}",
        )


app = FastAPI(
    title="betsvr bet_api",
    description="Betting product API that validates auth via lmsvr and runs betting monitoring.",
    version="0.1.0",
)


# CORS: keep permissive for localhost; production traffic uses same-origin via nginx proxy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bet.laserpointlabs.com",
        "http://localhost:8002",
        "http://127.0.0.1:8002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SPORTS_TO_MONITOR = [
    "americanfootball_nfl",
    "americanfootball_ncaaf",
    "basketball_nba",
    "basketball_ncaab",
    "baseball_mlb",
]


async def monitor_lines_loop() -> None:
    """
    Background task to monitor line movements periodically.
    Mirrors the behavior previously hosted in lmsvr/api_gateway.
    """
    logger.info("Starting background monitoring task...")

    # Ensure tools are loaded (build tool map)
    try:
        logger.info("Refreshing tool list for monitoring task...")
        await mcp_manager.get_tools_ollama_format()
    except Exception as e:
        logger.error("Failed to refresh tools: %s", e)

    import time

    last_prop_check = 0

    try:
        while True:
            prop_interval = int(os.getenv("PROP_CHECK_INTERVAL", 15))

            try:
                logger.info("Running scheduled check (Prop Interval: %sm)...", prop_interval)

                for sport in SPORTS_TO_MONITOR:
                    logger.info("Checking %s...", sport)

                    # 1) Ensure opening lines exist (baseline) for this sport
                    opening_file = Path("/mcp_servers/betting_monitor/data/opening_lines.json")
                    has_opening = False
                    if opening_file.exists():
                        try:
                            data = json.load(open(opening_file))
                            if sport in data:
                                has_opening = True
                        except Exception:
                            pass

                    if not has_opening:
                        logger.info(
                            "No opening lines found for %s. Taking initial snapshot...",
                            sport,
                        )
                        await mcp_manager.execute_tool(
                            "get_opening_lines", {"sport": sport, "hours_ago": 48}
                        )

                    # 2) Compare to opening
                    await mcp_manager.execute_tool("compare_to_opening", {"sport": sport})

                    # 3) Steam detection
                    await mcp_manager.execute_tool("detect_steam_moves", {"sport": sport})

                    # 4) Props check (interval-gated)
                    if time.time() - last_prop_check > (prop_interval * 60):
                        opening_props_file = Path(
                            "/mcp_servers/betting_monitor/data/opening_props.json"
                        )
                        has_props = False
                        if opening_props_file.exists():
                            try:
                                data = json.load(open(opening_props_file))
                                if sport in data:
                                    has_props = True
                            except Exception:
                                pass

                        if not has_props:
                            logger.info("Taking props snapshot for %s...", sport)
                            await mcp_manager.execute_tool("snapshot_props", {"sport": sport})
                        else:
                            result = await mcp_manager.execute_tool("compare_props", {"sport": sport})
                            logger.info("Prop check (%s): %s", sport, result)

                # Update timestamp if we ran props
                if time.time() - last_prop_check > (prop_interval * 60):
                    last_prop_check = time.time()

                # Force cleanup of old alerts (server cleans on read)
                await mcp_manager.execute_tool("get_recent_alerts", {"limit": 1})
                logger.info("Alert cleanup routine executed.")

                logger.info("Scheduled check complete.")
            except Exception as e:
                logger.error("Error in monitoring loop: %s", e)

            # Base sleep: 15 minutes
            await asyncio.sleep(900)
    except asyncio.CancelledError:
        logger.info("Monitoring task cancelled")


@app.on_event("startup")
async def startup_event():
    await mcp_manager.start_servers()
    logger.info("MCP servers started")

    # Start background monitoring loop
    asyncio.create_task(monitor_lines_loop())


@app.on_event("shutdown")
async def shutdown_event():
    await mcp_manager.cleanup()
    logger.info("MCP servers stopped")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "bet_api"}


@app.get("/api/alerts")
async def get_betting_alerts(
    limit: int = 20, _auth: str = Depends(require_valid_token)
):
    """
    Return recent alerts from betting_monitor's alert storage.
    """
    try:
        alerts_file = Path("/mcp_servers/betting_monitor/data/alerts.json")
        if not alerts_file.exists():
            return {"alerts": [], "message": "No alerts yet. Monitoring has not produced alerts."}

        with open(alerts_file, "r") as f:
            data = json.load(f)

        alerts = data.get("alerts", [])[:limit]
        last_updated = data.get("last_updated", None)
        return {"alerts": alerts, "count": len(alerts), "last_updated": last_updated}
    except Exception as e:
        logger.error("Error fetching alerts: %s", e)
        return {"alerts": [], "error": str(e)}


@app.post("/api/alerts/check")
async def trigger_alert_check(_auth: str = Depends(require_valid_token)):
    """
    Trigger a manual check for line movements, steam moves, and props across all sports.
    """
    try:
        results = {}
        # Ensure tools map is populated (tool list is cheap)
        await mcp_manager.get_tools_ollama_format()

        for sport in SPORTS_TO_MONITOR:
            movement_result = await mcp_manager.execute_tool("compare_to_opening", {"sport": sport})
            results[f"{sport}_movements"] = movement_result

            steam_result = await mcp_manager.execute_tool("detect_steam_moves", {"sport": sport})
            results[f"{sport}_steam"] = steam_result

            try:
                prop_result = await mcp_manager.execute_tool("compare_props", {"sport": sport})
                results[f"{sport}_props"] = prop_result
            except Exception:
                pass

        # Force cleanup (server cleans on read)
        await mcp_manager.execute_tool("get_recent_alerts", {"limit": 1})

        return {
            "status": "checked",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results,
        }
    except Exception as e:
        logger.error("Error checking alerts: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/alerts/snapshot")
async def take_opening_snapshot(
    hours_ago: int = 48, _auth: str = Depends(require_valid_token)
):
    """
    Take a snapshot of opening lines for comparison.
    """
    try:
        await mcp_manager.get_tools_ollama_format()
        result = await mcp_manager.execute_tool(
            "get_opening_lines", {"sport": "americanfootball_nfl", "hours_ago": hours_ago}
        )
        return {
            "status": "snapshot_taken",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": result,
        }
    except Exception as e:
        logger.error("Error taking snapshot: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
