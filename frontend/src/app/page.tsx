"use client";

import { useEffect, useState, useCallback } from "react";
import Header from "@/components/Header";
import ChannelGrid from "@/components/ChannelGrid";
import FixturesSidebar from "@/components/FixturesSidebar";
import Footer from "@/components/Footer";
import dynamic from "next/dynamic";

const VideoPlayer = dynamic(() => import("@/components/VideoPlayer"), {
  ssr: false,
});
import {
  Channel,
  FixturesData,
  fetchChannels,
  fetchFixtures,
} from "@/lib/api";

export default function HomePage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [fixtures, setFixtures] = useState<FixturesData>({
    upcoming: [],
    past: [],
    live: [],
  });
  const [activeTab, setActiveTab] = useState<"stream" | "upcoming" | "results">("stream");
  const [activeChannel, setActiveChannel] = useState<Channel | null>(null);

  const loadData = useCallback(async () => {
    const [ch, fx] = await Promise.all([fetchChannels(), fetchFixtures()]);
    setChannels(ch);
    setFixtures(fx);
  }, []);

  useEffect(() => {
    loadData();
    // Refresh every 5 minutes
    const interval = setInterval(loadData, 300000);
    return () => clearInterval(interval);
  }, [loadData]);

  return (
    <div className="app-root">
      <Header />

      {/* Tab Switcher for watch/upcoming/results */}
      <div className="tabs-container">
        <button
          className={`tab-btn ${activeTab === "stream" ? "active" : ""}`}
          onClick={() => setActiveTab("stream")}
        >
          <span className="tab-icon">📺</span> Live Stream
        </button>
        <button
          className={`tab-btn ${activeTab === "upcoming" ? "active" : ""}`}
          onClick={() => setActiveTab("upcoming")}
        >
          <span className="tab-icon">📅</span> Upcoming
        </button>
        <button
          className={`tab-btn ${activeTab === "results" ? "active" : ""}`}
          onClick={() => setActiveTab("results")}
        >
          <span className="tab-icon">🏆</span> Results
        </button>
      </div>

      {/* MAIN INTERFACE — Tabbed Layout */}
      <main className="main-layout tabbed-layout">
        {activeTab === "stream" && (
          <>
            {/* Center Player */}
            <section className="player-area">
              <VideoPlayer channel={activeChannel} />
            </section>

            {/* Channels List */}
            <section className="channels-area">
              <ChannelGrid
                channels={channels}
                activeChannel={activeChannel}
                onSelectChannel={setActiveChannel}
              />
            </section>
          </>
        )}

        {activeTab === "upcoming" && (
          <FixturesSidebar fixtures={fixtures} view="upcoming" />
        )}

        {activeTab === "results" && (
          <FixturesSidebar fixtures={fixtures} view="past" />
        )}
      </main>

      <Footer />
    </div>
  );
}
