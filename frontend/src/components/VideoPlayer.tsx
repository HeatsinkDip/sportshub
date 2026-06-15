"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Hls from "hls.js";
import * as dashjs from "dashjs";
import { Channel, Server, getProxyStreamUrl } from "@/lib/api";

interface VideoPlayerProps {
  channel: Channel | null;
  onClose?: () => void;
}

function base64urlToHex(b64url: string): string {
  let b64 = b64url.replace(/-/g, "+").replace(/_/g, "/");
  while (b64.length % 4) {
    b64 += "=";
  }
  const bin = atob(b64);
  return Array.from(bin, (c) => c.charCodeAt(0).toString(16).padStart(2, "0")).join("");
}

function hexToBase64Url(hex: string): string {
  let bin = "";
  for (let i = 0; i < hex.length; i += 2) {
    bin += String.fromCharCode(parseInt(hex.substr(i, 2), 16));
  }
  let b64 = btoa(bin);
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

export default function VideoPlayer({ channel, onClose }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const dashRef = useRef<dashjs.MediaPlayerClass | null>(null);
  const [activeServer, setActiveServer] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [quality, setQuality] = useState("auto");
  const [retryCount, setRetryCount] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Refs to avoid stale closures in event handlers
  const channelRef = useRef<Channel | null>(null);
  const activeServerRef = useRef<number>(0);
  const retryCountRef = useRef<number>(0);
  const nativeCleanupRef = useRef<(() => void) | null>(null);
  const loadStreamRef = useRef<(server: Server) => void>(() => {});

  useEffect(() => {
    channelRef.current = channel;
  }, [channel]);

  useEffect(() => {
    activeServerRef.current = activeServer;
  }, [activeServer]);

  useEffect(() => {
    retryCountRef.current = retryCount;
  }, [retryCount]);

  // Fallback handler: tries the next server or sets error if all exhausted
  const handleFailover = useCallback(() => {
    const currentChannel = channelRef.current;
    const currentServerIndex = activeServerRef.current;
    
    if (currentChannel && currentServerIndex < currentChannel.servers.length - 1) {
      const nextIndex = currentServerIndex + 1;
      console.log(`Server ${currentServerIndex + 1} failed. Trying Server ${nextIndex + 1}...`);
      setActiveServer(nextIndex);
      setRetryCount(0);
      loadStreamRef.current(currentChannel.servers[nextIndex]);
    } else {
      setError("Stream unavailable on all servers — try again later");
      setIsLoading(false);
    }
  }, []);

  const loadStream = useCallback(
    (server: Server) => {
      if (!videoRef.current) return;

      // Cleanup previous Hls
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }

      // Cleanup previous Dash
      if (dashRef.current) {
        dashRef.current.destroy();
        dashRef.current = null;
      }

      // Cleanup native listeners
      if (nativeCleanupRef.current) {
        nativeCleanupRef.current();
        nativeCleanupRef.current = null;
      }

      setIsLoading(true);
      setError(null);
      setIsPlaying(false);

      const streamUrl = getProxyStreamUrl(server);
      console.log(`[VideoPlayer] Loading stream URL: ${streamUrl}`);

      const isDash = server.url.endsWith(".mpd") || server.url.includes("mpd") || streamUrl.includes(".mpd") || streamUrl.includes("mpd");

      if (isDash) {
        const player = dashjs.MediaPlayer().create();

        // ClearKey DRM configuration if keys exist
        if (server.license_key) {
          const keysObj: Record<string, string> = {};
          try {
            const trimmedKey = server.license_key.trim();
            if (trimmedKey.startsWith("{")) {
              const parsed = JSON.parse(trimmedKey);
              if (parsed.keys && Array.isArray(parsed.keys)) {
                // JWK format: keys are already base64url
                parsed.keys.forEach((keyEntry: any) => {
                  if (keyEntry.kid && keyEntry.k) {
                    keysObj[keyEntry.kid] = keyEntry.k;
                  }
                });
              } else {
                // Direct hex map format: e.g. {"kid_hex": "key_hex"}
                Object.entries(parsed).forEach(([kidHex, kHex]) => {
                  if (typeof kidHex === "string" && typeof kHex === "string") {
                    keysObj[hexToBase64Url(kidHex.trim())] = hexToBase64Url(kHex.trim());
                  }
                });
              }
            } else if (trimmedKey.includes(":")) {
              // KID_HEX:KEY_HEX format
              const parts = trimmedKey.split(":");
              if (parts.length === 2) {
                const kidHex = parts[0].trim();
                const kHex = parts[1].trim();
                keysObj[hexToBase64Url(kidHex)] = hexToBase64Url(kHex);
              }
            }
          } catch (e) {
            console.error("Error configuring ClearKey DRM keys:", e);
          }

          if (Object.keys(keysObj).length > 0) {
            player.setProtectionData({
              "org.w3.clearkey": {
                "clearkeys": keysObj
              }
            } as any);
          }
        }

        player.initialize(videoRef.current, streamUrl, true);

        player.on(dashjs.MediaPlayer.events.CAN_PLAY, () => {
          setIsLoading(false);
          setIsPlaying(true);
        });

        player.on(dashjs.MediaPlayer.events.ERROR, (e: any) => {
          console.error("Dash.js error event:", e);
          handleFailover();
        });

        dashRef.current = player;
      } else if (Hls.isSupported()) {
        const hls = new Hls({
          debug: false,
          enableWorker: true,
          lowLatencyMode: true,            // Tuned for faster startup/low-latency
          backBufferLength: 30,            // Smaller buffer to preserve memory
          maxBufferLength: 10,             // Start playing faster (10s buffer instead of 30s)
          maxMaxBufferLength: 15,          // Cap max buffer to 15s instead of 60s
          startFragPrefetch: true,
          liveSyncDurationCount: 3,        // Keep sync close to live edge
          liveMaxLatencyDurationCount: 5,  // Fail/fallback if latency is too large
          xhrSetup: (xhr) => {
            xhr.timeout = 10000;           // 10s timeout instead of 30s to trigger failover faster
          },
        });

        hls.loadSource(streamUrl);
        hls.attachMedia(videoRef.current);

        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          setIsLoading(false);
          videoRef.current
            ?.play()
            .then(() => setIsPlaying(true))
            .catch(() => {});
        });

        hls.on(Hls.Events.ERROR, (_event, data) => {
          if (data.fatal) {
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                if (retryCountRef.current < 2) {
                  setRetryCount((c) => c + 1);
                  hls.startLoad();
                } else {
                  handleFailover();
                }
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                hls.recoverMediaError();
                break;
              default:
                handleFailover();
                break;
            }
          }
        });

        hlsRef.current = hls;
      } else if (videoRef.current.canPlayType("application/vnd.apple.mpegurl")) {
        // Safari native HLS (e.g. iOS Safari)
        const video = videoRef.current;
        video.src = streamUrl;
        
        const handleLoadedMetadata = () => {
          setIsLoading(false);
          video.play()
            .then(() => setIsPlaying(true))
            .catch(() => {});
        };

        const handleNativeError = () => {
          console.error("[VideoPlayer] Native video error event triggered");
          handleFailover();
        };

        video.addEventListener("loadedmetadata", handleLoadedMetadata);
        video.addEventListener("error", handleNativeError);

        nativeCleanupRef.current = () => {
          video.removeEventListener("loadedmetadata", handleLoadedMetadata);
          video.removeEventListener("error", handleNativeError);
        };
      } else {
        setError("HLS playback not supported in this browser");
        setIsLoading(false);
      }
    },
    [handleFailover]
  );

  // Assign loadStream to ref so handleFailover can access it without circular dependency
  useEffect(() => {
    loadStreamRef.current = loadStream;
  }, [loadStream]);

  useEffect(() => {
    if (channel && channel.servers.length > 0) {
      setActiveServer(0);
      setRetryCount(0);
      loadStream(channel.servers[0]);
    }

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
      if (dashRef.current) {
        dashRef.current.destroy();
        dashRef.current = null;
      }
      if (nativeCleanupRef.current) {
        nativeCleanupRef.current();
        nativeCleanupRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channel]);

  const handleServerChange = (idx: number) => {
    if (!channel) return;
    setActiveServer(idx);
    setRetryCount(0);
    loadStream(channel.servers[idx]);
  };

  const handleRetry = () => {
    if (!channel) return;
    setRetryCount(0);
    loadStream(channel.servers[activeServer]);
  };

  const handleRefresh = () => {
    if (!channel || channel.servers.length === 0) return;
    console.log("[VideoPlayer] Refreshing current stream...");
    loadStream(channel.servers[activeServer]);
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const handleFsChange = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", handleFsChange);
    return () => document.removeEventListener("fullscreenchange", handleFsChange);
  }, []);

  // No channel selected — show placeholder
  if (!channel) {
    return (
      <div className="video-player-container" ref={containerRef}>
        <div className="player-header-bar">
          <span>— Select a Channel to Watch —</span>
        </div>
        <div className="video-wrapper placeholder-wrapper">
          <div className="placeholder-content">
            <div className="placeholder-icon">📺</div>
            <h3>FIFA World Cup 2026™</h3>
            <p>Choose a channel below to start watching</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="video-player-container" ref={containerRef}>
      {/* Top bar */}
      <div className="player-header-bar">
        <span className="live-badge-player">
          <span className="pulse-dot"></span> LIVE
        </span>
        <span className="channel-name-player">{channel.name}</span>
        <div className="player-controls-top">
          {channel.servers.length > 1 && (
            <select
              className="server-select"
              value={activeServer}
              onChange={(e) => handleServerChange(Number(e.target.value))}
            >
              {channel.servers.map((s, i) => (
                <option key={i} value={i}>
                  Server {i + 1} ({s.quality})
                </option>
              ))}
            </select>
          )}
          <button className="player-btn refresh-btn" onClick={handleRefresh} title="Refresh Stream">
            ↻
          </button>
          <button className="player-btn" onClick={toggleFullscreen} title="Fullscreen">
            {isFullscreen ? "⊡" : "⛶"}
          </button>
        </div>
      </div>

      {/* Video area */}
      <div className="video-wrapper">
        <video
          ref={videoRef}
          className="video-element"
          controls
          playsInline
          autoPlay
        />

        {/* Loading overlay */}
        {isLoading && (
          <div className="player-overlay">
            <div className="loading-spinner"></div>
            <p>Connecting to {channel.name}...</p>
          </div>
        )}

        {/* Error overlay */}
        {error && (
          <div className="player-overlay error-overlay">
            <div className="error-icon">⚡</div>
            <p>{error}</p>
            <div className="error-actions">
              <button className="retry-btn" onClick={handleRetry}>
                Retry
              </button>
              {channel.servers.length > 1 && activeServer < channel.servers.length - 1 && (
                <button
                  className="retry-btn alt"
                  onClick={() => handleServerChange(activeServer + 1)}
                >
                  Try Server {activeServer + 2}
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Bottom info bar */}
      <div className="player-bottom-bar">
        <span className="stream-info">
          <span className="quality-badge">{channel.quality}</span>
          <span className="server-info">
            Server {activeServer + 1}/{channel.servers.length}
          </span>
        </span>
        <span className="stream-source">iptv-org · public stream</span>
      </div>
    </div>
  );
}
