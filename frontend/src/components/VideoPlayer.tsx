"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Hls from "hls.js";
import { Channel, Server, getProxyStreamUrl } from "@/lib/api";

interface VideoPlayerProps {
  channel: Channel | null;
  onClose?: () => void;
}

export default function VideoPlayer({ channel, onClose }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const [activeServer, setActiveServer] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [quality, setQuality] = useState("auto");
  const [retryCount, setRetryCount] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const loadStream = useCallback(
    (server: Server) => {
      if (!videoRef.current) return;

      // Cleanup previous
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }

      setIsLoading(true);
      setError(null);
      setIsPlaying(false);

      const streamUrl = getProxyStreamUrl(server);

      if (Hls.isSupported()) {
        const hls = new Hls({
          debug: false,
          enableWorker: true,
          lowLatencyMode: false,
          backBufferLength: 90,
          maxBufferLength: 30,
          maxMaxBufferLength: 60,
          startFragPrefetch: true,
          xhrSetup: (xhr) => {
            xhr.timeout = 30000;
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
                if (retryCount < 3) {
                  setRetryCount((c) => c + 1);
                  hls.startLoad();
                } else {
                  setError("Network error — stream may be offline");
                  setIsLoading(false);
                }
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                hls.recoverMediaError();
                break;
              default:
                setError("Stream unavailable — try another server");
                setIsLoading(false);
                break;
            }
          }
        });

        hlsRef.current = hls;
      } else if (videoRef.current.canPlayType("application/vnd.apple.mpegurl")) {
        // Safari native HLS
        videoRef.current.src = streamUrl;
        videoRef.current.addEventListener("loadedmetadata", () => {
          setIsLoading(false);
          videoRef.current
            ?.play()
            .then(() => setIsPlaying(true))
            .catch(() => {});
        });
      } else {
        setError("HLS playback not supported in this browser");
        setIsLoading(false);
      }
    },
    [retryCount]
  );

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
