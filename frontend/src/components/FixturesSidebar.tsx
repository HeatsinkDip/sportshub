"use client";

import { useMemo } from "react";
import { FiCalendar, FiChevronLeft, FiChevronRight, FiAward, FiMapPin } from "react-icons/fi";

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
  upcomingFixtures: Fixture[];
  pastFixtures: Fixture[];
  liveFixtures: Fixture[];
  view?: "upcoming" | "past" | "all";
  upcomingDate: string;
  onSelectUpcomingDate: (date: string) => void;
  completedDate: string;
  onSelectCompletedDate: (date: string) => void;
}

export default function FixturesSidebar({
  upcomingFixtures,
  pastFixtures,
  liveFixtures,
  view = "all",
  upcomingDate,
  onSelectUpcomingDate,
  completedDate,
  onSelectCompletedDate,
}: FixturesSidebarProps) {
  // Sort upcoming by time ascending (earliest first)
  const sortedUpcoming = useMemo(() => {
    return [...upcomingFixtures].sort((a, b) => (a.time || "").localeCompare(b.time || ""));
  }, [upcomingFixtures]);

  // Sort past by time descending (most recent first)
  const sortedPast = useMemo(() => {
    return [...pastFixtures].sort((a, b) => (b.time || "").localeCompare(a.time || ""));
  }, [pastFixtures]);

  return (
    <>
      {/* LEFT: Live & Completed Results */}
      <section className="fixtures-panel fixtures-sidebar-left">
        <div className="fixtures-container">
          <CalendarBar selectedDate={completedDate} onSelectDate={onSelectCompletedDate} />

          {/* Live matches Section */}
          <div className={`fixture-section live-section-desktop ${liveFixtures.length === 0 ? "live-section-empty" : ""}`}>
            <h2 className="fixture-heading live-heading">
              <span className="live-dot-heading"></span> Live Now
            </h2>
            <div className="fixture-list">
              {liveFixtures.length > 0 ? (
                liveFixtures.map((m) => (
                  <LiveCard key={m.id} match={m} />
                ))
              ) : (
                <div className="no-fixtures">No matches live right now</div>
              )}
            </div>
          </div>

          {/* Completed matches Section */}
          <div className="fixture-section completed-section-desktop">
            <h2 className="fixture-heading past-heading">
              <span className="heading-icon"><FiAward /></span> Completed Results
            </h2>
            <div className="fixture-list">
              {sortedPast.length > 0 ? (
                sortedPast.map((m) => (
                  <PastCard key={m.id} match={m} />
                ))
              ) : (
                <div className="no-fixtures">No completed matches for this date</div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* RIGHT: Upcoming */}
      <section className="fixtures-panel fixtures-sidebar-right">
        <div className="fixtures-container">
          <CalendarBar selectedDate={upcomingDate} onSelectDate={onSelectUpcomingDate} />

          <div className="fixture-section">
            <h2 className="fixture-heading upcoming-heading">
              <span className="heading-icon">
                <FiCalendar style={{ display: "inline-block", verticalAlign: "middle", marginTop: -2 }} />
              </span>{" "}
              Upcoming Matches
            </h2>
            <div className="fixture-list">
              {sortedUpcoming.length > 0 ? (
                sortedUpcoming.map((m) => (
                  <UpcomingCard key={m.id} match={m} />
                ))
              ) : (
                <div className="no-fixtures">No upcoming matches for this date</div>
              )}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

/* ── Calendar Bar Component ────────────────────────────────────────── */
interface CalendarBarProps {
  selectedDate: string;
  onSelectDate: (date: string) => void;
}

function CalendarBar({ selectedDate, onSelectDate }: CalendarBarProps) {
  const currentDate = new Date(selectedDate + "T12:00:00");

  const dates = useMemo(() => {
    const arr = [];
    for (let i = -2; i <= 2; i++) {
      const d = new Date(currentDate);
      d.setDate(currentDate.getDate() + i);
      arr.push(d);
    }
    return arr;
  }, [selectedDate]);

  const handlePrevDay = () => {
    const prev = new Date(currentDate);
    prev.setDate(currentDate.getDate() - 1);
    onSelectDate(formatIsoDate(prev));
  };

  const handleNextDay = () => {
    const next = new Date(currentDate);
    next.setDate(currentDate.getDate() + 1);
    onSelectDate(formatIsoDate(next));
  };

  const formatIsoDate = (d: Date) => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  return (
    <div className="calendar-bar">
      <button className="cal-nav-btn" onClick={handlePrevDay} aria-label="Previous day">
        <FiChevronLeft />
      </button>

      <div className="cal-dates-row">
        {dates.map((d) => {
          const iso = formatIsoDate(d);
          const isActive = iso === selectedDate;
          const isToday = iso === formatIsoDate(new Date());
          const labelDay = d.toLocaleDateString("en-US", { weekday: "short" });
          const labelNum = d.getDate();
          return (
            <button
              key={iso}
              className={`cal-date-btn ${isActive ? "active" : ""} ${isToday ? "today" : ""}`}
              onClick={() => onSelectDate(iso)}
            >
              <span className="cal-day-name">{labelDay}</span>
              <span className="cal-day-num">{labelNum}</span>
            </button>
          );
        })}
      </div>

      <button className="cal-nav-btn" onClick={handleNextDay} aria-label="Next day">
        <FiChevronRight />
      </button>

      <div className="cal-picker-wrapper">
        <FiCalendar className="cal-picker-icon" />
        <input
          type="date"
          className="cal-date-picker-input"
          value={selectedDate}
          onChange={(e) => {
            if (e.target.value) onSelectDate(e.target.value);
          }}
        />
      </div>
    </div>
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
      {match.venue && (
        <div className="fixture-venue">
          <FiMapPin style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4, marginTop: -2 }} />
          {match.venue}
        </div>
      )}
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
