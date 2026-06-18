"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Hls from "hls.js";
import * as dashjs from "dashjs";
import { Channel, Server, getProxyStreamUrl, isBdixOrLocal } from "@/lib/api";
import Noise from "./Noise";
import {
  FiRefreshCw,
  FiMaximize,
  FiMinimize,
  FiAlertCircle,
  FiChevronDown,
} from "react-icons/fi";

interface VideoPlayerProps {
  channel: Channel | null;
  onClose?: () => void;
}

// Quality level entry from HLS.js
interface QualityLevel {
  index: number;   // -1 = Auto
  label: string;
  height: number;
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

/** Return a human-readable label for a quality level height in pixels. */
function heightToLabel(height: number): string {
  if (height >= 2000) return "2K / 1440p";
  if (height >= 1080) return "1080p (FHD)";
  if (height >= 720) return "720p (HD)";
  if (height >= 480) return "480p";
  if (height >= 360) return "360p";
  return `${height}p`;
}

export default function VideoPlayer({ channel, onClose }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const dashRef = useRef<dashjs.MediaPlayerClass | null>(null);
  const [activeServer, setActiveServer] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Quality selector state
  const [qualityLevels, setQualityLevels] = useState<QualityLevel[]>([]);
  const [selectedQuality, setSelectedQuality] = useState<number>(-1); // -1 = Auto
  const [currentQualityLabel, setCurrentQualityLabel] = useState<string>("");
  const [showQualityMenu, setShowQualityMenu] = useState(false);

  // Refs to avoid stale closures in event handlers
  const channelRef = useRef<Channel | null>(null);
  const activeServerRef = useRef<number>(0);
  const retryCountRef = useRef<number>(0);
  const nativeCleanupRef = useRef<(() => void) | null>(null);
  const loadStreamRef = useRef<(server: Server) => void>(() => { });

  useEffect(() => { channelRef.current = channel; }, [channel]);
  useEffect(() => { activeServerRef.current = activeServer; }, [activeServer]);
  useEffect(() => { retryCountRef.current = retryCount; }, [retryCount]);

  // Close quality menu on outside click
  useEffect(() => {
    if (!showQualityMenu) return;
    const close = () => setShowQualityMenu(false);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [showQualityMenu]);

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

  // Apply quality level selection to HLS.js
  const applyQualityLevel = useCallback((levelIndex: number) => {
    const hls = hlsRef.current;
    if (!hls) return;
    if (levelIndex === -1) {
      // Auto mode
      hls.currentLevel = -1;
      hls.loadLevel = -1;
    } else {
      // Lock to specific level
      hls.currentLevel = levelIndex;
      hls.loadLevel = levelIndex;
    }
    setSelectedQuality(levelIndex);
  }, []);

  const loadStream = useCallback(
    (server: Server) => {
      if (!videoRef.current) return;

      // Reset quality state on stream change
      setQualityLevels([]);
      setSelectedQuality(-1);
      setCurrentQualityLabel("");

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

        player.updateSettings({
          streaming: {
            buffer: {
              stableBufferTime: 8,
              bufferTimeAtTopQuality: 12,
              initialBufferLevel: 1,
              bufferToKeep: 10,
              bufferPruningInterval: 10,
            },
            delay: {
              liveDelay: 4,
            },
            abr: {
              autoSwitchBitrate: { video: true, audio: true },
            },
            retryAttempts: {
              MPD: 3,
              MediaSegment: 3,
              InitializationSegment: 3,
            },
            retryIntervals: {
              MPD: 1000,
              MediaSegment: 1000,
              InitializationSegment: 1000,
            },
          },
        } as any);

        // ClearKey DRM configuration if keys exist
        if (server.license_key) {
          const keysObj: Record<string, string> = {};
          try {
            const trimmedKey = server.license_key.trim();
            if (trimmedKey.startsWith("{")) {
              const parsed = JSON.parse(trimmedKey);
              if (parsed.keys && Array.isArray(parsed.keys)) {
                parsed.keys.forEach((keyEntry: any) => {
                  if (keyEntry.kid && keyEntry.k) {
                    keysObj[keyEntry.kid] = keyEntry.k;
                  }
                });
              } else {
                Object.entries(parsed).forEach(([kidHex, kHex]) => {
                  if (typeof kidHex === "string" && typeof kHex === "string") {
                    keysObj[hexToBase64Url(kidHex.trim())] = hexToBase64Url(kHex.trim());
                  }
                });
              }
            } else if (trimmedKey.includes(":")) {
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
          lowLatencyMode: false,              // Disabled: proxy adds latency, causes stalls

          // ── Buffer tuning for proxied live streams ──────────────────────
          backBufferLength: 10,
          maxBufferLength: 12,                // 12s buffer — more room for proxy latency spikes
          maxMaxBufferLength: 30,             // Hard cap
          maxBufferHole: 0.5,                 // Tolerate small gaps without stall
          maxStarvationDelay: 4,              // If stalled > 4s, jump forward instead of spinning

          // ── Live stream sync settings ───────────────────────────────────
          liveSyncDurationCount: 3,
          liveMaxLatencyDurationCount: 8,
          liveBackBufferLength: 10,

          // ── Pre-fetch the next fragment early ──────────────────────────
          startFragPrefetch: true,

          // ── Timeouts: fail fast, retry quickly ─────────────────────────
          fragLoadingTimeOut: 10000,          // 10s per fragment
          manifestLoadingTimeOut: 8000,       // 8s manifest timeout
          levelLoadingTimeOut: 8000,
          fragLoadingMaxRetry: 4,
          manifestLoadingMaxRetry: 4,
          fragLoadingRetryDelay: 500,

          // ── Quality / ABR settings ──────────────────────────────────────
          // startLevel: 0 = ALWAYS start at the highest quality level.
          // This avoids the common pattern where HLS.js starts at SD and
          // then re-buffers while upgrading to HD — which is the #1 cause
          // of the heavy buffering the user experiences.
          startLevel: 0,
          // Generous initial bandwidth estimate (5 Mbps) for fast-start at HD
          abrEwmaDefaultEstimate: 5000000,
          abrEwmaFastLive: 3.0,
          abrEwmaSlowLive: 9.0,
          abrBandWidthFactor: 0.9,
          abrBandWidthUpFactor: 0.7,

          xhrSetup: (xhr) => {
            xhr.timeout = 10000;
          },
        });

        hls.loadSource(streamUrl);
        hls.attachMedia(videoRef.current);

        // ── On manifest parse: extract quality levels ─────────────────────
        hls.on(Hls.Events.MANIFEST_PARSED, (_evt, data) => {
          setIsLoading(false);
          videoRef.current?.play()
            .then(() => setIsPlaying(true))
            .catch(() => { });

          // Build quality level list from manifest levels
          const levels: QualityLevel[] = [
            { index: -1, label: "Auto", height: -1 },
            ...data.levels.map((lvl, idx) => ({
              index: idx,
              label: heightToLabel(lvl.height),
              height: lvl.height,
            })),
          ];
          // De-duplicate labels (some streams report same height twice)
          const seen = new Set<string>();
          const uniqueLevels = levels.filter((l) => {
            const key = l.label;
            if (seen.has(key) && l.index !== -1) return false;
            seen.add(key);
            return true;
          });
          // Always show the quality picker so user can see current quality.
          // Single-bitrate streams show [Auto, <level>] — still useful.
          setQualityLevels(uniqueLevels.length >= 1 ? uniqueLevels : []);

          if (data.levels.length > 0) {
            const firstLevel = data.levels[data.levels.length - 1]; // Highest quality
            setCurrentQualityLabel(heightToLabel(firstLevel.height));
          }
        });

        // ── Track the currently playing quality level ─────────────────────
        hls.on(Hls.Events.LEVEL_SWITCHED, (_evt, data) => {
          const level = hls.levels[data.level];
          if (level) {
            setCurrentQualityLabel(heightToLabel(level.height));
          }
        });

        // ── Error handling ────────────────────────────────────────────────
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
        // Safari native HLS
        const video = videoRef.current;
        video.src = streamUrl;

        const handleLoadedMetadata = () => {
          setIsLoading(false);
          video.play()
            .then(() => setIsPlaying(true))
            .catch(() => { });
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
    const video = videoRef.current;
    if (!video) return;

    if (video.requestFullscreen) {
      if (!document.fullscreenElement) {
        video.requestFullscreen().catch((err) => {
          console.error("[VideoPlayer] Error entering fullscreen:", err);
        });
      } else {
        document.exitFullscreen().catch((err) => {
          console.error("[VideoPlayer] Error exiting fullscreen:", err);
        });
      }
    } else if ((video as any).webkitEnterFullscreen) {
      try { (video as any).webkitEnterFullscreen(); } catch { }
    } else if ((video as any).msRequestFullscreen) {
      (video as any).msRequestFullscreen();
    }
  };

  useEffect(() => {
    const handleFsChange = () => {
      const isFs = !!(document.fullscreenElement || (document as any).webkitFullscreenElement);
      setIsFullscreen(isFs);
    };
    document.addEventListener("fullscreenchange", handleFsChange);
    document.addEventListener("webkitfullscreenchange", handleFsChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFsChange);
      document.removeEventListener("webkitfullscreenchange", handleFsChange);
    };
  }, []);

  // Detect if the active server is a BDIX stream
  const isBdix = channel && channel.servers[activeServer]
    ? isBdixOrLocal(channel.servers[activeServer].url)
    : false;

  // No channel selected — show placeholder
  if (!channel) {
    return (
      <div className="video-player-container" ref={containerRef}>
        <div className="player-header-bar">
          <span>— Select a Channel to Watch —</span>
        </div>
        <div className="video-wrapper placeholder-wrapper">
          <Noise patternAlpha={18} />
          <div className="placeholder-content">
            <div className="placeholder-logo-wrapper">
              <img
                src="/fifa_logo.png"
                alt="FIFA World Cup 2026 Logo"
                className="placeholder-fifa-logo"
              />
            </div>
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
          {/* Quality picker — only shown when multiple levels exist */}
          {qualityLevels.length > 1 && (
            <div className="quality-picker-wrapper" onClick={(e) => e.stopPropagation()}>
              <button
                className="player-btn quality-picker-btn"
                title="Select Quality"
                onClick={() => setShowQualityMenu((v) => !v)}
              >
                {selectedQuality === -1
                  ? `Auto${currentQualityLabel ? ` (${currentQualityLabel})` : ""}`
                  : qualityLevels.find((l) => l.index === selectedQuality)?.label ?? "Auto"}
                <FiChevronDown style={{ marginLeft: 4, verticalAlign: "middle" }} />
              </button>
              {showQualityMenu && (
                <div className="quality-menu">
                  {qualityLevels.map((lvl) => (
                    <button
                      key={lvl.index}
                      className={`quality-menu-item${selectedQuality === lvl.index ? " active" : ""}`}
                      onClick={() => {
                        applyQualityLevel(lvl.index);
                        setShowQualityMenu(false);
                      }}
                    >
                      {lvl.label}
                      {lvl.index === -1 && currentQualityLabel && (
                        <span className="quality-current-hint"> ({currentQualityLabel})</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

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
            <FiRefreshCw className="refresh-icon" />
          </button>
          <button className="player-btn" onClick={toggleFullscreen} title="Fullscreen">
            {isFullscreen ? <FiMinimize /> : <FiMaximize />}
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
            <FiAlertCircle className="error-icon" />
            <p>{error}</p>
            {isBdix && (
              <p className="bdix-notice">
                ⚡ This channel uses a BDIX stream — it requires a BDIX-connected ISP to play.
              </p>
            )}
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
          <span className="quality-badge">
            {currentQualityLabel || channel.quality}
          </span>
          {isBdix && (
            <span className="bdix-badge" title="This stream uses BDIX (Bangladesh Internet Exchange) — best for BDIX ISP users">
              BDIX
            </span>
          )}
          <span className="server-info">
            Server {activeServer + 1}/{channel.servers.length}
          </span>
        </span>
        <a
          href="https://dipayon.vercel.app/"
          target="_blank"
          rel="noopener noreferrer"
          className="stream-source"
          style={{ cursor: "pointer", transition: "color 0.2s" }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent-pink)")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
        >
          Develop by Dipayon
        </a>
      </div>
    </div>
  );
}
