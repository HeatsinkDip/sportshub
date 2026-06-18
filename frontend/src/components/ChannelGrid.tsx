"use client";

import { useRef } from "react";
import { Channel } from "@/lib/api";
import StarBorder from "./StarBorder";
import { FiStar, FiRadio, FiChevronLeft, FiChevronRight } from "react-icons/fi";

interface ChannelGridProps {
  channels: Channel[];
  activeChannel: Channel | null;
  onSelectChannel: (channel: Channel) => void;
}

export default function ChannelGrid({
  channels,
  activeChannel,
  onSelectChannel,
}: ChannelGridProps) {
  const featured = channels.filter((c) => c.category === "featured");
  const live = channels.filter((c) => c.category === "live");

  return (
    <section className="channel-section">
      {/* Featured / Recommended */}
      {featured.length > 0 && (
        <>
          <div className="section-header">
            <h2 className="section-title featured-title">
              <span className="title-icon"><FiStar /></span> FIFA Live (Recommended)
            </h2>
            <span className="channel-count">{featured.length} channels</span>
          </div>
          <ChannelCarousel
            channels={featured}
            activeChannel={activeChannel}
            onSelectChannel={onSelectChannel}
          />
        </>
      )}

      {/* Live Channels */}
      {live.length > 0 && (
        <>
          <div className="section-header" style={{ marginTop: 16 }}>
            <h2 className="section-title live-title">
              <span className="title-icon"><FiRadio /></span> Live Channels
            </h2>
            <span className="channel-count">{live.length} channels</span>
          </div>
          <ChannelCarousel
            channels={live}
            activeChannel={activeChannel}
            onSelectChannel={onSelectChannel}
          />
        </>
      )}

      {channels.length === 0 && (
        <div className="no-channels">
          <div className="loading-spinner" />
          <p>Loading channels. Please wait...</p>
        </div>
      )}
    </section>
  );
}

function ChannelCarousel({
  channels,
  activeChannel,
  onSelectChannel,
}: {
  channels: Channel[];
  activeChannel: Channel | null;
  onSelectChannel: (channel: Channel) => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scroll = (dir: "left" | "right") => {
    if (!scrollRef.current) return;
    const amount = dir === "left" ? -300 : 300;
    scrollRef.current.scrollBy({ left: amount, behavior: "smooth" });
  };

  return (
    <div className="carousel-wrapper">
      <button
        className="carousel-btn carousel-btn-left"
        onClick={() => scroll("left")}
        aria-label="Scroll left"
      >
        <FiChevronLeft />
      </button>

      <div className="channel-grid" ref={scrollRef}>
        {channels.map((ch) => (
          <ChannelCard
            key={ch.id}
            channel={ch}
            isActive={activeChannel?.id === ch.id}
            onClick={() => onSelectChannel(ch)}
          />
        ))}
      </div>

      <button
        className="carousel-btn carousel-btn-right"
        onClick={() => scroll("right")}
        aria-label="Scroll right"
      >
        <FiChevronRight />
      </button>
    </div>
  );
}

function ChannelCard({
  channel,
  isActive,
  onClick,
}: {
  channel: Channel;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <StarBorder
      as="button"
      className={`channel-card ${isActive ? "active" : ""}`}
      onClick={onClick}
      color={isActive ? "#d946ef" : "rgba(255, 255, 255, 0.25)"}
      speed={isActive ? "3.5s" : "8s"}
      thickness={isActive ? 2 : 1}
    >
      <div className="card-top">
        {channel.logo ? (
          <div className="logo-pill">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={channel.logo}
              alt={channel.name}
              className="channel-logo"
              onError={(e) => {
                const img = e.target as HTMLImageElement;
                img.style.display = "none";
                const pill = img.parentElement as HTMLElement | null;
                if (pill) {
                  pill.style.background = "transparent";
                  const fb = pill.parentElement?.querySelector(".logo-fallback") as HTMLElement | null;
                  if (fb) fb.style.display = "flex";
                }
              }}
            />
          </div>
        ) : null}
        <div
          className="logo-fallback"
          style={{ display: channel.logo ? "none" : "flex" }}
        >
          {channel.name.charAt(0)}
        </div>
      </div>


      <div className="card-bottom">
        <span className="channel-card-name">{channel.name}</span>
        <div className="card-meta">
          <span className={`quality-tag ${channel.quality.toLowerCase()}`}>
            {channel.quality}
          </span>
          {channel.servers.length > 1 && (
            <span className="server-count-badge">
              {channel.servers.length} srv
            </span>
          )}
        </div>
      </div>

      {/* Live indicator */}
      <div className="card-live-dot">
        <span className="live-pulse"></span>
      </div>
    </StarBorder>
  );
}
