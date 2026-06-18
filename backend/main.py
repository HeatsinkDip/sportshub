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


# Strong references to running background tasks to prevent Python GC from cleaning them up:
background_tasks = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load disk cache, initialize client, start background tasks."""
    print("[Startup] Initializing global HTTP client and cache...")
    global global_proxy_client
    limits = httpx.Limits(max_keepalive_connections=150, max_connections=300)
    global_proxy_client = httpx.AsyncClient(
        limits=limits,
        timeout=httpx.Timeout(timeout=45.0, connect=5.0, read=30.0, write=10.0),
        follow_redirects=True,
    )

    # Load from disk cache instantly (takes ~10ms)
    try:
        from m3u_parser import load_channels_from_disk
        load_channels_from_disk()
    except Exception as e:
        print(f"[Startup] Cache load error: {e}")

    # Trigger async scraping in background to refresh the list without blocking server startup
    t1 = asyncio.create_task(fetch_and_parse_m3u())
    t2 = asyncio.create_task(fetch_openfootball_data())
    t3 = asyncio.create_task(scrape_fifa_fixtures())
    background_tasks.add(t1)
    background_tasks.add(t2)
    background_tasks.add(t3)
    t1.add_done_callback(background_tasks.discard)
    t2.add_done_callback(background_tasks.discard)
    t3.add_done_callback(background_tasks.discard)

    # Start periodic refresh every 15 minutes
    refresh_task = asyncio.create_task(periodic_refresh())
    background_tasks.add(refresh_task)
    refresh_task.add_done_callback(background_tasks.discard)
    print("[Startup] Background tasks initialized successfully.")

    yield

    # Cleanup
    for task in list(background_tasks):
        task.cancel()
    
    try:
        await refresh_task
    except asyncio.CancelledError:
        pass

    # Close HTTP client pool
    if global_proxy_client:
        await global_proxy_client.aclose()

    try:
        from fixtures_scraper import close_shared_client
        await close_shared_client()
    except Exception as e:
        print(f"[Shutdown] Error closing shared client: {e}")



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
        from m3u_parser import load_channels_from_disk
        channels = load_channels_from_disk()

    import json
    payload = xor_hex_encrypt(json.dumps(channels))

    return JSONResponse(
        content={
            "payload": payload,
            "total": len(channels),
            "last_updated": "live",
        },
        headers={
            "Cache-Control": "public, max-age=300, stale-while-revalidate=60",
        },
    )


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
    result = await fetch_sportmonks_fixtures_by_date(date, tz_offset)
    return JSONResponse(
        content=result,
        headers={
            "Cache-Control": "public, max-age=60, stale-while-revalidate=30",
        },
    )


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

def xor_hex_encrypt(data: str, key: int = 0x5A) -> str:
    return "".join(f"{ord(c) ^ key:02x}" for c in data)

def xor_hex_decrypt(hex_str: str, key: int = 0x5A) -> str:
    try:
        chars = []
        for i in range(0, len(hex_str), 2):
            val = int(hex_str[i:i+2], 16)
            chars.append(chr(val ^ key))
        return "".join(chars)
    except Exception:
        return ""

def decode_config(hex_config: str) -> dict:
    if hex_config == "empty":
        return {}
    try:
        import json
        decrypted = xor_hex_decrypt(hex_config)
        return json.loads(decrypted)
    except Exception:
        return {}

def encode_config(config: dict) -> str:
    if not config:
        return "empty"
    import json
    return xor_hex_encrypt(json.dumps(config))

def decode_url(hex_url: str) -> str:
    return xor_hex_decrypt(hex_url)

def encode_url(url: str) -> str:
    return xor_hex_encrypt(url)

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
        "Accept-Encoding": "identity",  # Disable compression — video is already compressed
        "Connection": "keep-alive",
    }

    if referrer:
        headers["Referer"] = referrer
        headers["Origin"] = urlparse(referrer).scheme + "://" + urlparse(referrer).netloc

    global global_proxy_client
    if not global_proxy_client:
        global_proxy_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    resp = None
    try:
        req = global_proxy_client.build_request("GET", url, headers=headers)
        resp = await global_proxy_client.send(req, stream=True)

        if resp.status_code >= 400:
            status_code = resp.status_code
            content_type = resp.headers.get("content-type")
            body = await resp.aread()
            await resp.aclose()
            resp = None
            return Response(content=body, status_code=status_code, media_type=content_type)

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
            resp_url = str(resp.url)
            body_bytes = await resp.aread()
            await resp.aclose()
            resp = None
            body_text = body_bytes.decode("utf-8", errors="ignore")
            backend_base_url = get_backend_base_url(request)
            body = _rewrite_manifest_urls(body_text, resp_url, referrer, user_agent, backend_base_url)
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
            resp_url = str(resp.url)
            body_bytes = await resp.aread()
            await resp.aclose()
            resp = None
            body_text = body_bytes.decode("utf-8", errors="ignore")
            backend_base_url = get_backend_base_url(request)
            body = _rewrite_mpd_manifest(body_text, resp_url, referrer, user_agent, backend_base_url)
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
            clean_path = urlparse(url).path.lower()
            is_static_segment = clean_path.endswith((".ts", ".mp4", ".m4s", ".key", ".aac", ".vtt"))
            response_headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*",
                "Cache-Control": "public, max-age=86400" if is_static_segment else "no-cache",
                "X-Accel-Buffering": "no",   # Disable nginx proxy buffering for live streams
            }

            stream_resp = resp
            resp = None

            # Pass-through Content-Length from upstream when available.
            # This avoids chunked transfer encoding overhead and lets clients
            # show download progress / seek correctly for static segments.
            upstream_content_length = stream_resp.headers.get("content-length")
            if upstream_content_length and is_static_segment:
                response_headers["Content-Length"] = upstream_content_length

            async def stream_content():
                try:
                    # 256KB chunks — 8x larger than before, reduces Python async loop overhead
                    async for chunk in stream_resp.aiter_bytes(chunk_size=262144):
                        yield chunk
                finally:
                    await stream_resp.aclose()

            upstream_media_type = stream_resp.headers.get("content-type", "").lower()
            if clean_path.endswith(".ts") or "trolltech" in upstream_media_type or "linguist" in upstream_media_type:
                media_type = "video/mp2t"
            elif clean_path.endswith(".mp4"):
                media_type = "video/mp4"
            elif clean_path.endswith(".m4s"):
                media_type = "video/iso.segment"
            elif clean_path.endswith(".aac"):
                media_type = "audio/aac"
            elif clean_path.endswith(".vtt"):
                media_type = "text/vtt"
            elif clean_path.endswith(".key"):
                media_type = "application/octet-stream"
            else:
                media_type = stream_resp.headers.get("content-type", "video/mp2t")

            return StreamingResponse(
                stream_content(),
                status_code=stream_resp.status_code,
                media_type=media_type,
                headers=response_headers,
            )

    except httpx.TimeoutException:
        return JSONResponse({"error": "Stream timeout"}, status_code=504)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=502)
    finally:
        if resp is not None:
            try:
                await resp.aclose()
            except Exception:
                pass


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
        "Accept-Encoding": "identity",  # Disable compression — video is already compressed
        "Connection": "keep-alive",
    }
    if referrer:
        headers["Referer"] = referrer
        headers["Origin"] = urlparse(referrer).scheme + "://" + urlparse(referrer).netloc

    global global_proxy_client
    if not global_proxy_client:
        global_proxy_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    resp = None
    try:
        req = global_proxy_client.build_request("GET", url, headers=headers)
        resp = await global_proxy_client.send(req, stream=True)

        if resp.status_code >= 400:
            status_code = resp.status_code
            content_type = resp.headers.get("content-type")
            body = await resp.aread()
            await resp.aclose()
            resp = None
            return Response(content=body, status_code=status_code, media_type=content_type)

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
            resp_url = str(resp.url)
            body_bytes = await resp.aread()
            await resp.aclose()
            resp = None
            body_text = body_bytes.decode("utf-8", errors="ignore")
            backend_base_url = get_backend_base_url(request)
            body = _rewrite_manifest_urls(body_text, resp_url, referrer, user_agent, backend_base_url)
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
            resp_url = str(resp.url)
            body_bytes = await resp.aread()
            await resp.aclose()
            resp = None
            body_text = body_bytes.decode("utf-8", errors="ignore")
            backend_base_url = get_backend_base_url(request)
            body = _rewrite_mpd_manifest(body_text, resp_url, referrer, user_agent, backend_base_url)
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
            clean_path = urlparse(url).path.lower()
            is_static_segment = clean_path.endswith((".ts", ".mp4", ".m4s", ".key", ".aac", ".vtt"))
            response_headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*",
                "Cache-Control": "public, max-age=86400" if is_static_segment else "no-cache",
                "X-Accel-Buffering": "no",   # Disable nginx proxy buffering for live streams
            }

            stream_resp = resp
            resp = None

            # Pass-through Content-Length from upstream when available.
            upstream_content_length = stream_resp.headers.get("content-length")
            if upstream_content_length and is_static_segment:
                response_headers["Content-Length"] = upstream_content_length

            async def stream_content():
                try:
                    # 256KB chunks — 8x larger than before, reduces Python async loop overhead
                    async for chunk in stream_resp.aiter_bytes(chunk_size=262144):
                        yield chunk
                finally:
                    await stream_resp.aclose()

            upstream_media_type = stream_resp.headers.get("content-type", "").lower()
            if clean_path.endswith(".ts") or "trolltech" in upstream_media_type or "linguist" in upstream_media_type:
                media_type = "video/mp2t"
            elif clean_path.endswith(".mp4"):
                media_type = "video/mp4"
            elif clean_path.endswith(".m4s"):
                media_type = "video/iso.segment"
            elif clean_path.endswith(".aac"):
                media_type = "audio/aac"
            elif clean_path.endswith(".vtt"):
                media_type = "text/vtt"
            elif clean_path.endswith(".key"):
                media_type = "application/octet-stream"
            else:
                media_type = stream_resp.headers.get("content-type", "video/mp2t")

            return StreamingResponse(
                stream_content(),
                status_code=stream_resp.status_code,
                media_type=media_type,
                headers=response_headers,
            )

    except httpx.TimeoutException:
        return JSONResponse({"error": "Stream timeout"}, status_code=504)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=502)
    finally:
        if resp is not None:
            try:
                await resp.aclose()
            except Exception:
                pass


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
                    config = {}
                    if referrer:
                        config["referrer"] = referrer
                    if user_agent:
                        config["user_agent"] = user_agent
                    hex_config = encode_config(config)
                    hex_url = encode_url(abs_url)
                    proxy_url = f"{backend_base_url}/api/proxy-stream/c/{hex_config}/{hex_url}/"
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
                config = {}
                if referrer:
                    config["referrer"] = referrer
                if user_agent:
                    config["user_agent"] = user_agent
                hex_config = encode_config(config)
                hex_url = encode_url(abs_url)
                proxy_url = f"{backend_base_url}/api/proxy-stream/c/{hex_config}/{hex_url}/"
                rewritten.append(proxy_url)

    return '\n'.join(rewritten)


# ── Run ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
