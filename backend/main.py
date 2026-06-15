"""
D'one TV — FastAPI Backend
Serves IPTV channel data, FIFA fixtures, and proxies HLS streams.
"""

import asyncio
import re
from contextlib import asynccontextmanager
from urllib.parse import urlparse, urljoin, unquote, quote

import httpx
from fastapi import FastAPI, Query, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from m3u_parser import fetch_and_parse_m3u, get_cached_channels
from fixtures_scraper import scrape_fifa_fixtures, get_cached_fixtures


# ── Background refresh task ──────────────────────────────────────────
async def periodic_refresh():
    """Refresh M3U playlist and fixtures every 10 minutes."""
    while True:
        try:
            await fetch_and_parse_m3u()
            await scrape_fifa_fixtures()
        except Exception as e:
            print(f"[Refresh] Error: {e}")
        await asyncio.sleep(600)  # 10 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: fetch initial data, start background refresh."""
    print("[Startup] Fetching initial M3U playlist...")
    await fetch_and_parse_m3u()
    print("[Startup] Fetching initial fixtures...")
    await scrape_fifa_fixtures()

    # Start background refresh
    task = asyncio.create_task(periodic_refresh())
    print("[Startup] Background refresh task started")

    yield

    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ── FastAPI App ──────────────────────────────────────────────────────
app = FastAPI(
    title="D'one TV API",
    description="Backend for World Cup IPTV streaming hub",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API Endpoints ────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "service": "D'one TV API", "version": "1.0.0"}


@app.get("/api/channels")
async def get_channels():
    """Return all World Cup channels with their stream servers."""
    channels = get_cached_channels()
    if not channels:
        # Try fetching again
        channels = await fetch_and_parse_m3u()

    return {
        "channels": channels,
        "total": len(channels),
        "last_updated": "live",
    }


@app.get("/api/fixtures")
async def get_fixtures():
    """Return upcoming and past World Cup fixtures."""
    fixtures = get_cached_fixtures()
    if not any(fixtures.values()):
        fixtures = await scrape_fifa_fixtures()

    return fixtures


@app.get("/api/refresh")
async def refresh_data():
    """Force refresh M3U playlist and fixtures."""
    channels = await fetch_and_parse_m3u()
    fixtures = await scrape_fifa_fixtures()
    return {
        "channels_count": len(channels),
        "fixtures": {k: len(v) for k, v in fixtures.items()},
    }


@app.get("/api/proxy-stream")
async def proxy_stream(
    url: str = Query(..., description="M3U8 stream URL to proxy"),
    referrer: str = Query("", description="HTTP Referer header"),
    user_agent: str = Query("", description="HTTP User-Agent header"),
):
    """
    Proxy an HLS M3U8 manifest or TS segment to bypass CORS.
    Rewrites internal URLs in manifests to also go through the proxy.
    """
    if not url:
        return JSONResponse({"error": "Missing url parameter"}, status_code=400)

    url = unquote(url)

    headers = {
        "User-Agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    if referrer:
        headers["Referer"] = referrer
        headers["Origin"] = urlparse(referrer).scheme + "://" + urlparse(referrer).netloc

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)

            content_type = resp.headers.get("content-type", "application/octet-stream")
            
            # Read first chunk or entire text to check if it is a manifest
            is_m3u8 = False
            body_text = ""
            if url.endswith(".m3u8") or "mpegurl" in content_type.lower() or "m3u" in content_type.lower():
                is_m3u8 = True
                body_text = resp.text
            else:
                try:
                    # Try to decode to check for #EXTM3U
                    body_text = resp.text
                    if body_text.strip().startswith("#EXTM3U"):
                        is_m3u8 = True
                except Exception:
                    pass

            # If it's an M3U8 manifest, rewrite internal URLs
            if is_m3u8:
                # Use str(resp.url) to resolve relative URLs against the final redirected URL
                body = _rewrite_manifest_urls(body_text, str(resp.url), referrer, user_agent)

                return Response(
                    content=body,
                    media_type="application/vnd.apple.mpegurl",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "*",
                        "Cache-Control": "no-cache",
                    },
                )
            else:
                # Binary content (TS segments, keys, etc.)
                return Response(
                    content=resp.content,
                    media_type=content_type,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "*",
                    },
                )

    except httpx.TimeoutException:
        return JSONResponse({"error": "Stream timeout"}, status_code=504)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)


def _rewrite_manifest_urls(manifest: str, base_url: str, referrer: str, user_agent: str) -> str:
    """
    Rewrite URLs in an HLS manifest to go through our proxy.
    Handles both relative and absolute URLs.
    """
    lines = manifest.split('\n')
    rewritten = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines and comments (but keep them)
        if not stripped or stripped.startswith('#'):
            # Check for URI= in EXT-X-KEY or similar tags
            if 'URI="' in stripped:
                def replace_uri(match):
                    uri = match.group(1)
                    if uri.startswith("/api/proxy-stream"):
                        return match.group(0)
                    abs_url = urljoin(base_url, uri)
                    proxy_url = f"/api/proxy-stream?url={quote(abs_url)}"
                    if referrer:
                        proxy_url += f"&referrer={quote(referrer)}"
                    if user_agent:
                        proxy_url += f"&user_agent={quote(user_agent)}"
                    return f'URI="{proxy_url}"'

                stripped = re.sub(r'URI="([^"]*)"', replace_uri, stripped)

            rewritten.append(stripped)
        else:
            # This is a URL line — rewrite it
            if stripped.startswith("/api/proxy-stream"):
                rewritten.append(stripped)
            else:
                abs_url = urljoin(base_url, stripped)
                proxy_url = f"/api/proxy-stream?url={quote(abs_url)}"
                if referrer:
                    proxy_url += f"&referrer={quote(referrer)}"
                if user_agent:
                    proxy_url += f"&user_agent={quote(user_agent)}"
                rewritten.append(proxy_url)

    return '\n'.join(rewritten)


# ── Run ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
