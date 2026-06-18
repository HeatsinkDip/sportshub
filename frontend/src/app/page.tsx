"use client";

import { useEffect, useState } from "react";
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
  fetchChannels,
  fetchFixtures,
  FALLBACK_CHANNELS,
} from "@/lib/api";

function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function HomePage() {
  const [channels, setChannels] = useState<Channel[]>(FALLBACK_CHANNELS);
  const [upcomingFixtures, setUpcomingFixtures] = useState<any[]>([]);
  const [pastFixtures, setPastFixtures] = useState<any[]>([]);
  const [liveFixtures, setLiveFixtures] = useState<any[]>([]);
  const [fixturesLoading, setFixturesLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"stream" | "live_score" | "results" | "upcoming">("stream");
  const [activeChannel, setActiveChannel] = useState<Channel | null>(null);

  const [upcomingDate, setUpcomingDate] = useState<string>(todayIso());
  const [completedDate, setCompletedDate] = useState<string>(todayIso());

  // Load channels once on mount
  useEffect(() => {
    async function loadChannels() {
      const ch = await fetchChannels();
      setChannels(ch);
    }
    loadChannels();

    const interval = setInterval(() => {
      if (document.visibilityState === "visible") loadChannels();
    }, 300000);

    const onVis = () => { if (document.visibilityState === "visible") loadChannels(); };
    document.addEventListener("visibilitychange", onVis);
    return () => { clearInterval(interval); document.removeEventListener("visibilitychange", onVis); };
  }, []);

  // Load upcoming/live fixtures — poll every 30s
  useEffect(() => {
    let mounted = true;

    async function loadUpcoming() {
      try {
        setFixturesLoading(true);
        const fx = await fetchFixtures(upcomingDate);
        if (!mounted) return;
        setUpcomingFixtures(fx.upcoming || []);
        setLiveFixtures(fx.live || []);
      } catch (err) {
        console.error("Error loading upcoming fixtures:", err);
      } finally {
        if (mounted) setFixturesLoading(false);
      }
    }
    loadUpcoming();

    const interval = setInterval(() => {
      if (document.visibilityState === "visible") loadUpcoming();
    }, 30000);

    const onVis = () => { if (document.visibilityState === "visible") loadUpcoming(); };
    document.addEventListener("visibilitychange", onVis);

    return () => {
      mounted = false;
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [upcomingDate]);

  // Load completed fixtures
  useEffect(() => {
    let mounted = true;

    async function loadCompleted() {
      try {
        const fx = await fetchFixtures(completedDate);
        if (!mounted) return;
        setPastFixtures(fx.past || []);
      } catch (err) {
        console.error("Error loading completed fixtures:", err);
      }
    }
    loadCompleted();

    const interval = setInterval(() => {
      if (document.visibilityState === "visible") loadCompleted();
    }, 120000);

    const onVis = () => { if (document.visibilityState === "visible") loadCompleted(); };
    document.addEventListener("visibilitychange", onVis);

    return () => {
      mounted = false;
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [completedDate]);

  return (
    <div className="app-root">
      <Header />

      {/* Tab Switcher */}
      <div className="tabs-container">
        <button
          className={`tab-btn ${activeTab === "stream" ? "active" : ""}`}
          onClick={() => setActiveTab("stream")}
        >
          <span className="tab-icon"><FiTv /></span>
          <span className="tab-label">Live Stream</span>
        </button>
        <button
          className={`tab-btn ${activeTab === "live_score" ? "active" : ""}`}
          onClick={() => setActiveTab("live_score")}
        >
          <span className="tab-icon"><FiActivity /></span>
          <span className="tab-label">Live Score</span>
        </button>
        <button
          className={`tab-btn ${activeTab === "results" ? "active" : ""}`}
          onClick={() => setActiveTab("results")}
        >
          <span className="tab-icon"><FiAward /></span>
          <span className="tab-label">Results</span>
        </button>
        <button
          className={`tab-btn ${activeTab === "upcoming" ? "active" : ""}`}
          onClick={() => setActiveTab("upcoming")}
        >
          <span className="tab-icon"><FiCalendar /></span>
          <span className="tab-label">Schedule</span>
        </button>
      </div>

      {/* MAIN INTERFACE */}
      <main className={`main-layout active-tab-${activeTab}`}>
        <FixturesSidebar
          upcomingFixtures={upcomingFixtures}
          pastFixtures={pastFixtures}
          liveFixtures={liveFixtures}
          upcomingDate={upcomingDate}
          onSelectUpcomingDate={setUpcomingDate}
          completedDate={completedDate}
          onSelectCompletedDate={setCompletedDate}
          isLoading={fixturesLoading}
        />

        {/* Center Player */}
        <section className="player-area">
          <VideoPlayer channel={activeChannel} />
        </section>

        {/* Channel Grid */}
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
