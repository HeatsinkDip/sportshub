"use client";

import { useEffect, useState, useCallback } from "react";
import Header from "@/components/Header";
import VideoPlayer from "@/components/VideoPlayer";
import ChannelGrid from "@/components/ChannelGrid";
import FixturesSidebar from "@/components/FixturesSidebar";
import Footer from "@/components/Footer";
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

      {/* MAIN INTERFACE — 3-column grid matching worldcuphub.tsx */}
      <main className="main-layout">
        {/* LEFT: Upcoming Fixtures */}
        <FixturesSidebar fixtures={fixtures} />

        {/* CENTER: Video Player */}
        <section className="player-area">
          <VideoPlayer channel={activeChannel} />
        </section>

        {/* Channel Carousel (full width spanning all columns) */}
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
