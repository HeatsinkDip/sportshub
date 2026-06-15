"use client";

import { useEffect, useState, useCallback } from "react";
import Header from "@/components/Header";
import ChannelGrid from "@/components/ChannelGrid";
import FixturesSidebar from "@/components/FixturesSidebar";
import Footer from "@/components/Footer";
import dynamic from "next/dynamic";
import { FiTv, FiCalendar, FiAward, FiActivity } from "react-icons/fi";

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
  const [upcomingFixtures, setUpcomingFixtures] = useState<any[]>([]);
  const [pastFixtures, setPastFixtures] = useState<any[]>([]);
  const [liveFixtures, setLiveFixtures] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<"stream" | "live_score" | "results" | "upcoming">("stream");
  const [activeChannel, setActiveChannel] = useState<Channel | null>(null);

  const getTodayDateString = () => {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const [upcomingDate, setUpcomingDate] = useState<string>(getTodayDateString());
  const [completedDate, setCompletedDate] = useState<string>(getTodayDateString());

  // Load channels once on mount
  useEffect(() => {
    async function loadChannels() {
      const ch = await fetchChannels();
      setChannels(ch);
    }
    loadChannels();
    const interval = setInterval(loadChannels, 300000);
    return () => clearInterval(interval);
  }, []);

  // Load upcoming/live fixtures dynamically for the selected upcoming date
  useEffect(() => {
    async function loadUpcoming() {
      try {
        const fx = await fetchFixtures(upcomingDate);
        setUpcomingFixtures(fx.upcoming || []);
        setLiveFixtures(fx.live || []);
      } catch (err) {
        console.error("Error loading upcoming fixtures:", err);
      }
    }
    loadUpcoming();
    const interval = setInterval(loadUpcoming, 120000);
    return () => clearInterval(interval);
  }, [upcomingDate]);

  // Load completed fixtures dynamically for the selected completed date
  useEffect(() => {
    async function loadCompleted() {
      try {
        const fx = await fetchFixtures(completedDate);
        setPastFixtures(fx.past || []);
      } catch (err) {
        console.error("Error loading completed fixtures:", err);
      }
    }
    loadCompleted();
    const interval = setInterval(loadCompleted, 120000);
    return () => clearInterval(interval);
  }, [completedDate]);

  return (
    <div className="app-root">
      <Header />

      {/* Tab Switcher for watch/upcoming/results */}
      <div className="tabs-container">
        <button
          className={`tab-btn ${activeTab === "stream" ? "active" : ""}`}
          onClick={() => setActiveTab("stream")}
        >
          <span className="tab-icon"><FiTv /></span> Live Stream
        </button>
        <button
          className={`tab-btn ${activeTab === "live_score" ? "active" : ""}`}
          onClick={() => setActiveTab("live_score")}
        >
          <span className="tab-icon"><FiActivity /></span> Live Score
        </button>
        <button
          className={`tab-btn ${activeTab === "results" ? "active" : ""}`}
          onClick={() => setActiveTab("results")}
        >
          <span className="tab-icon"><FiAward /></span> Results
        </button>
        <button
          className={`tab-btn ${activeTab === "upcoming" ? "active" : ""}`}
          onClick={() => setActiveTab("upcoming")}
        >
          <span className="tab-icon"><FiCalendar /></span> Upcoming Match
        </button>
      </div>

      {/* MAIN INTERFACE — Desktop 3-Column / Mobile Tabbed Layout */}
      <main className={`main-layout active-tab-${activeTab}`}>
        {/* Left Upcoming & Right Past Sidebars */}
        <FixturesSidebar
          upcomingFixtures={upcomingFixtures}
          pastFixtures={pastFixtures}
          liveFixtures={liveFixtures}
          upcomingDate={upcomingDate}
          onSelectUpcomingDate={setUpcomingDate}
          completedDate={completedDate}
          onSelectCompletedDate={setCompletedDate}
        />

        {/* Center Player */}
        <section className="player-area">
          <VideoPlayer channel={activeChannel} />
        </section>

        {/* Channel Carousel */}
        <section className="channels-area">
          <ChannelGrid
            channels={channels}
            activeChannel={activeChannel}
            onSelectChannel={setActiveChannel}
          />
        </section>
      </main>

      <Footer />
    </div>
  );
}
