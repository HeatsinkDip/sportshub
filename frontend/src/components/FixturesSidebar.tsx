"use client";

import { useState, useMemo } from "react";

interface Team {
  name: string;
  code: string;
  flag: string;
  score?: number;
}

interface Fixture {
  id: number;
  group: string;
  date: string;
  time?: string;
  status: string;
  venue?: string;
  team1: Team;
  team2: Team;
}

interface FixturesSidebarProps {
  fixtures: { upcoming: Fixture[]; past: Fixture[]; live: Fixture[] };
}

export default function FixturesSidebar({ fixtures }: FixturesSidebarProps) {
  return (
    <>
      {/* LEFT: Upcoming */}
      <section className="fixtures-panel fixtures-sidebar-left">
        <div className="fixtures-container">
          {/* Live matches first if any */}
          {fixtures.live.length > 0 && (
            <div className="fixture-section">
              <h2 className="fixture-heading live-heading">
                <span className="live-dot-heading"></span> Live Now
              </h2>
              <div className="fixture-list">
                {fixtures.live.map((m) => (
                  <LiveCard key={m.id} match={m} />
                ))}
              </div>
            </div>
          )}

          <h2 className="fixture-heading upcoming-heading">
            <span className="heading-icon">📅</span> Upcoming Fixtures
          </h2>
          <div className="fixture-list">
            {fixtures.upcoming.length > 0 ? (
              fixtures.upcoming.map((m) => (
                <UpcomingCard key={m.id} match={m} />
              ))
            ) : (
              <div className="no-fixtures">No upcoming fixtures</div>
            )}
          </div>
        </div>
      </section>

      {/* RIGHT: Past Results */}
      <section className="fixtures-panel fixtures-sidebar-right">
        <PastResults matches={fixtures.past} />
      </section>
    </>
  );
}

/* ── Upcoming Card ─────────────────────────────────────────────────── */
function UpcomingCard({ match }: { match: Fixture }) {
  const dateStr = formatDate(match.date);
  return (
    <div className="fixture-card">
      <div className="fixture-meta">
        <span className="fixture-group">
          {match.group} • {dateStr}
        </span>
      </div>
      <div className="fixture-matchup">
        <span className="fixture-team">
          <span className="team-flag">{match.team1.flag}</span>
          <span className="team-name">{match.team1.name}</span>
        </span>
        <span className="fixture-time">{match.time || "TBD"}</span>
        <span className="fixture-team right">
          <span className="team-name">{match.team2.name}</span>
          <span className="team-flag">{match.team2.flag}</span>
        </span>
      </div>
      {match.venue && <div className="fixture-venue">📍 {match.venue}</div>}
    </div>
  );
}

/* ── Live Card ─────────────────────────────────────────────────────── */
function LiveCard({ match }: { match: Fixture }) {
  return (
    <div className="fixture-card live-card">
      <div className="fixture-meta">
        <span className="fixture-group">{match.group}</span>
        <span className="fixture-status live-status">
          <span className="live-pulse-sm"></span> LIVE
        </span>
      </div>
      <div className="fixture-score-row">
        <div
          className={`fixture-team-score ${
            (match.team1.score ?? 0) > (match.team2.score ?? 0) ? "winner" : ""
          }`}
        >
          <span className="team-flag">{match.team1.flag}</span>
          <span className="team-name">{match.team1.name}</span>
          <span className="score-box live-score">{match.team1.score ?? 0}</span>
        </div>
        <div
          className={`fixture-team-score ${
            (match.team2.score ?? 0) > (match.team1.score ?? 0) ? "winner" : ""
          }`}
        >
          <span className="team-flag">{match.team2.flag}</span>
          <span className="team-name">{match.team2.name}</span>
          <span className="score-box live-score">{match.team2.score ?? 0}</span>
        </div>
      </div>
    </div>
  );
}

/* ── Past Results with date filter ─────────────────────────────────── */
function PastResults({ matches }: { matches: Fixture[] }) {
  const [dateFilter, setDateFilter] = useState("all");

  const uniqueDates = useMemo(() => {
    const dates = [...new Set(matches.map((m) => m.date))].sort();
    return dates;
  }, [matches]);

  const filtered = useMemo(() => {
    if (dateFilter === "all") return matches;
    return matches.filter((m) => m.date === dateFilter);
  }, [matches, dateFilter]);

  return (
    <div className="fixtures-container">
      <h2 className="fixture-heading past-heading">
        <span className="heading-icon">🕐</span> Past Results
      </h2>

      {/* Date Filter */}
      <div className="fixture-filter">
        <label className="filter-label">Filter by Date</label>
        <div className="select-wrapper">
          <select
            className="date-select"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
          >
            <option value="all">All Matchdays</option>
            {uniqueDates.map((d) => (
              <option key={d} value={d}>
                {formatDate(d)}
              </option>
            ))}
          </select>
          <span className="select-arrow">▾</span>
        </div>
      </div>

      <div className="fixture-list">
        {filtered.length > 0 ? (
          filtered.map((m) => <PastCard key={m.id} match={m} />)
        ) : (
          <div className="no-fixtures">No fixtures found for this date.</div>
        )}
      </div>
    </div>
  );
}

/* ── Past Card ─────────────────────────────────────────────────────── */
function PastCard({ match }: { match: Fixture }) {
  return (
    <div className="fixture-card">
      <div className="fixture-meta">
        <span className="fixture-group">{match.group} • COMPLETED</span>
        <span className="fixture-status completed">FT</span>
      </div>
      <div className="fixture-score-row">
        <div
          className={`fixture-team-score ${
            (match.team1.score ?? 0) > (match.team2.score ?? 0) ? "winner" : ""
          }`}
        >
          <span className="team-flag">{match.team1.flag}</span>
          <span className="team-name">{match.team1.name}</span>
          <span className="score-box">{match.team1.score ?? 0}</span>
        </div>
        <div
          className={`fixture-team-score ${
            (match.team2.score ?? 0) > (match.team1.score ?? 0) ? "winner" : ""
          }`}
        >
          <span className="team-flag">{match.team2.flag}</span>
          <span className="team-name">{match.team2.name}</span>
          <span className="score-box">{match.team2.score ?? 0}</span>
        </div>
      </div>
    </div>
  );
}

/* ── Utilities ─────────────────────────────────────────────────────── */
function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr + "T12:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return dateStr;
  }
}
