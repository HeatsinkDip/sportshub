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
from fixtures_scraper import scrape_fifa_fixtures, get_cached_fixtures, fetch_openfootball_data


# ── Background refresh task ──────────────────────────────────────────
async def periodic_refresh():
    """Refresh M3U playlist, openfootball data, and fixtures every 15 minutes."""
    while True:
        try:
            await fetch_and_parse_m3u()
            await fetch_openfootball_data()
            await scrape_fifa_fixtures()
        except Exception as e:
            print(f"[Refresh] Error: {e}")
        await asyncio.sleep(900)  # 15 minutes


# Create global HTTP client for stream proxying
global_proxy_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load disk cache, initialize client, start background tasks."""
    print("[Startup] Initializing global HTTP client and cache...")
    global global_proxy_client
    limits = httpx.Limits(max_keepalive_connections=150, max_connections=300)
    global_proxy_client = httpx.AsyncClient(limits=limits, timeout=45.0, follow_redirects=True)

    # Load from disk cache instantly (takes ~10ms)
    try:
        from m3u_parser import load_channels_from_disk
        load_channels_from_disk()
    except Exception as e:
        print(f"[Startup] Cache load error: {e}")

    # Trigger async scraping in background to refresh the list without blocking server startup
    asyncio.create_task(fetch_and_parse_m3u())
    asyncio.create_task(fetch_openfootball_data())
    asyncio.create_task(scrape_fifa_fixtures())

    # Start periodic refresh every 15 minutes
    refresh_task = asyncio.create_task(periodic_refresh())
    print("[Startup] Background tasks initialized successfully.")

    yield

    # Cleanup
    refresh_task.cancel()
    try:
        await refresh_task
    except asyncio.CancelledError:
        pass

    # Close HTTP client pool
    if global_proxy_client:
        await global_proxy_client.aclose()


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
    allow_origins=["*"],
    allow_credentials=False,
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
async def get_fixtures(
    date: str = Query(None, description="Format YYYY-MM-DD"),
    tz_offset: int = Query(0, description="Browser getTimezoneOffset() in minutes")
):
    """Return upcoming and past fixtures, optionally filtered by date."""
    if not date:
        from datetime import date as dt
        date = dt.today().isoformat()
    from fixtures_scraper import fetch_sportmonks_fixtures_by_date
    return await fetch_sportmonks_fixtures_by_date(date, tz_offset)


@app.get("/api/refresh")
async def refresh_data():
    """Force refresh M3U playlist and fixtures."""
    channels = await fetch_and_parse_m3u()
    fixtures = await scrape_fifa_fixtures()
    return {
        "channels_count": len(channels),
        "fixtures": {k: len(v) for k, v in fixtures.items()},
    }


def get_backend_base_url(request: Request) -> str:
    """Dynamically determine the backend's external base URL from request headers or URL."""
    proto = request.headers.get("x-forwarded-proto")
    if not proto:
        proto = request.url.scheme
        
    host = request.headers.get("x-forwarded-host")
    if not host:
        host = request.headers.get("host")
    if not host:
        host = request.url.netloc
        
    return f"{proto}://{host}"

def decode_config(hex_config: str) -> dict:
    if hex_config == "empty":
        return {}
    try:
        import json
        return json.loads(bytes.fromhex(hex_config).decode('utf-8'))
    except Exception:
        return {}

def encode_config(config: dict) -> str:
    if not config:
        return "empty"
    import json
    return json.dumps(config).encode('utf-8').hex()

def decode_url(hex_url: str) -> str:
    try:
        return bytes.fromhex(hex_url).decode('utf-8')
    except Exception:
        return ""

def encode_url(url: str) -> str:
    return url.encode('utf-8').hex()

def _rewrite_mpd_manifest(content: str, manifest_url: str, referrer: str, user_agent: str, backend_base_url: str) -> str:
    """
    Rewrite base URLs or inject a BaseURL tag pointing to the path-based proxy
    so that relative DASH segments resolve through the proxy correctly.
    """
    base_dir = manifest_url.rsplit('/', 1)[0] + '/'
    
    config = {}
    if referrer:
        config["referrer"] = referrer
    if user_agent:
        config["user_agent"] = user_agent
    hex_config = encode_config(config)
    
    hex_base = encode_url(base_dir)
    # We use a path-based BaseURL relative to the local proxy
    proxy_base_url = f"{backend_base_url}/api/proxy-stream/c/{hex_config}/{hex_base}/"
    
    # Check if there are existing <BaseURL> tags
    has_base_url = "<BaseURL" in content
    
    if has_base_url:
        def replace_base_url(match):
            inner_url = match.group(2).strip()
            # Resolve relative/absolute URL
            abs_url = urljoin(manifest_url, inner_url)
            if not abs_url.endswith('/'):
                abs_url += '/'
            hex_abs = encode_url(abs_url)
            return f'<{match.group(1)}>{backend_base_url}/api/proxy-stream/c/{hex_config}/{hex_abs}/</BaseURL>'
            
        content = re.sub(r'<(BaseURL[^>]*)>(.*?)</BaseURL>', replace_base_url, content, flags=re.DOTALL)
    else:
        # Insert BaseURL tag directly inside the <MPD> element
        mpd_match = re.search(r'<MPD[^>]*>', content)
        if mpd_match:
            insert_idx = mpd_match.end()
            content = content[:insert_idx] + f'\n<BaseURL>{proxy_base_url}</BaseURL>' + content[insert_idx:]
            
    return content


@app.get("/api/proxy-stream")
async def proxy_stream(
    request: Request,
    url: str = Query(..., description="M3U8/MPD stream URL to proxy"),
    referrer: str = Query("", description="HTTP Referer header"),
    user_agent: str = Query("", description="HTTP User-Agent header"),
):
    """
    Proxy HLS/DASH manifests and segments using a global connection pool
    to minimize latency, resolving CORS and omitting Content-Length to avoid mismatch errors.
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

    global global_proxy_client
    if not global_proxy_client:
        global_proxy_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    try:
        req = global_proxy_client.build_request("GET", url, headers=headers)
        resp = await global_proxy_client.send(req, stream=True)

        if resp.status_code >= 400:
            body = await resp.aread()
            await resp.aclose()
            return Response(content=body, status_code=resp.status_code, media_type=resp.headers.get("content-type"))

        content_type = resp.headers.get("content-type", "").lower()
        is_m3u8 = (
            url.endswith(".m3u8")
            or "mpegurl" in content_type
            or "m3u" in content_type
            or "application/x-mpegurl" in content_type
        )
        is_mpd = (
            url.endswith(".mpd")
            or "dash+xml" in content_type
            or "mpd" in content_type
        )

        if is_m3u8:
            body_bytes = await resp.aread()
            await resp.aclose()
            body_text = body_bytes.decode("utf-8", errors="ignore")
            backend_base_url = get_backend_base_url(request)
            body = _rewrite_manifest_urls(body_text, str(resp.url), referrer, user_agent, backend_base_url)
            return Response(
                content=body,
                media_type="application/vnd.apple.mpegurl",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Cache-Control": "no-cache",
                },
            )
        elif is_mpd:
            body_bytes = await resp.aread()
            await resp.aclose()
            body_text = body_bytes.decode("utf-8", errors="ignore")
            backend_base_url = get_backend_base_url(request)
            body = _rewrite_mpd_manifest(body_text, str(resp.url), referrer, user_agent, backend_base_url)
            return Response(
                content=body,
                media_type="application/dash+xml",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Cache-Control": "no-cache",
                },
            )
        else:
            # Segment/binary: Stream content chunk by chunk, omitting Content-Length to prevent mismatches
            response_headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*",
                "Cache-Control": "public, max-age=86400" if url.endswith((".ts", ".mp4", ".m4s")) else "no-cache",
            }

            async def stream_content():
                try:
                    async for chunk in resp.aiter_bytes(chunk_size=32768):
                        yield chunk
                finally:
                    await resp.aclose()

            return StreamingResponse(
                stream_content(),
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "video/mp2t"),
                headers=response_headers,
            )

    except httpx.TimeoutException:
        return JSONResponse({"error": "Stream timeout"}, status_code=504)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)


@app.get("/api/proxy-stream/c/{hex_config}/{hex_url}/{relative_path:path}")
async def proxy_stream_path(
    hex_config: str,
    hex_url: str,
    relative_path: str,
    request: Request
):
    """
    Path-based stream proxy endpoint to handle relative DASH segment requests cleanly.
    """
    config = decode_config(hex_config)
    base_url = decode_url(hex_url)
    if not base_url:
        return JSONResponse({"error": "Invalid base URL"}, status_code=400)

    # Resolve absolute URL for the segment/nested resource
    url = urljoin(base_url, relative_path)

    # Append any incoming query parameters (tokens, keys, etc.)
    query_params = request.url.query
    if query_params:
        client_params = dict(request.query_params)
        client_params.pop("referrer", None)
        client_params.pop("user_agent", None)
        if client_params:
            from urllib.parse import urlencode
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{urlencode(client_params)}"

    referrer = config.get("referrer", "")
    user_agent = config.get("user_agent", "")

    headers = {
        "User-Agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referrer:
        headers["Referer"] = referrer
        headers["Origin"] = urlparse(referrer).scheme + "://" + urlparse(referrer).netloc

    global global_proxy_client
    if not global_proxy_client:
        global_proxy_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    try:
        req = global_proxy_client.build_request("GET", url, headers=headers)
        resp = await global_proxy_client.send(req, stream=True)

        if resp.status_code >= 400:
            body = await resp.aread()
            await resp.aclose()
            return Response(content=body, status_code=resp.status_code, media_type=resp.headers.get("content-type"))

        content_type = resp.headers.get("content-type", "").lower()
        is_m3u8 = (
            url.endswith(".m3u8")
            or "mpegurl" in content_type
            or "m3u" in content_type
        )
        is_mpd = (
            url.endswith(".mpd")
            or "dash+xml" in content_type
            or "mpd" in content_type
        )

        if is_m3u8:
            body_bytes = await resp.aread()
            await resp.aclose()
            body_text = body_bytes.decode("utf-8", errors="ignore")
            backend_base_url = get_backend_base_url(request)
            body = _rewrite_manifest_urls(body_text, str(resp.url), referrer, user_agent, backend_base_url)
            return Response(
                content=body,
                media_type="application/vnd.apple.mpegurl",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Cache-Control": "no-cache",
                },
            )
        elif is_mpd:
            body_bytes = await resp.aread()
            await resp.aclose()
            body_text = body_bytes.decode("utf-8", errors="ignore")
            backend_base_url = get_backend_base_url(request)
            body = _rewrite_mpd_manifest(body_text, str(resp.url), referrer, user_agent, backend_base_url)
            return Response(
                content=body,
                media_type="application/dash+xml",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Cache-Control": "no-cache",
                },
            )
        else:
            response_headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*",
                "Cache-Control": "public, max-age=86400" if url.endswith((".ts", ".mp4", ".m4s")) else "no-cache",
            }

            async def stream_content():
                try:
                    async for chunk in resp.aiter_bytes(chunk_size=32768):
                        yield chunk
                finally:
                    await resp.aclose()

            return StreamingResponse(
                stream_content(),
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "video/mp2t"),
                headers=response_headers,
            )

    except httpx.TimeoutException:
        return JSONResponse({"error": "Stream timeout"}, status_code=504)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)


def _rewrite_manifest_urls(manifest: str, base_url: str, referrer: str, user_agent: str, backend_base_url: str) -> str:
    """
    Rewrite URLs in an HLS manifest to go through our proxy.
    Handles both relative and absolute URLs, producing absolute URLs.
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
                    if uri.startswith(f"{backend_base_url}/api/proxy-stream"):
                        return match.group(0)
                    if uri.startswith("/api/proxy-stream"):
                        return f'URI="{backend_base_url}{uri}"'
                    abs_url = urljoin(base_url, uri)
                    proxy_url = f"{backend_base_url}/api/proxy-stream?url={quote(abs_url)}"
                    if referrer:
                        proxy_url += f"&referrer={quote(referrer)}"
                    if user_agent:
                        proxy_url += f"&user_agent={quote(user_agent)}"
                    return f'URI="{proxy_url}"'

                stripped = re.sub(r'URI="([^"]*)"', replace_uri, stripped)

            rewritten.append(stripped)
        else:
            # This is a URL line — rewrite it
            if stripped.startswith(f"{backend_base_url}/api/proxy-stream"):
                rewritten.append(stripped)
            elif stripped.startswith("/api/proxy-stream"):
                rewritten.append(f"{backend_base_url}{stripped}")
            else:
                abs_url = urljoin(base_url, stripped)
                proxy_url = f"{backend_base_url}/api/proxy-stream?url={quote(abs_url)}"
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
