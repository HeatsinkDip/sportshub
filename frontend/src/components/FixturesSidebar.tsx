"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import {
  FiCalendar,
  FiChevronLeft,
  FiChevronRight,
  FiAward,
  FiMapPin,
  FiClock,
} from "react-icons/fi";

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
  isLoading?: boolean;
}

/* ── ISO date helpers ─────────────────────────────────────────────── */
function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function FixturesSidebar({
  upcomingFixtures,
  pastFixtures,
  liveFixtures,
  upcomingDate,
  onSelectUpcomingDate,
  completedDate,
  onSelectCompletedDate,
  isLoading = false,
}: FixturesSidebarProps) {
  const today = todayIso();

  // ── DATE GUARDS ─────────────────────────────────────────────────
  // Upcoming: only today or future dates
  const handleUpcomingDate = (date: string) => {
    if (date >= today) onSelectUpcomingDate(date);
  };

  // Live/Completed: only today or past dates
  const handleCompletedDate = (date: string) => {
    if (date <= today) onSelectCompletedDate(date);
  };

  // Sort upcoming by time ascending
  const sortedUpcoming = useMemo(() =>
    [...upcomingFixtures].sort((a, b) => (a.time || "").localeCompare(b.time || "")),
    [upcomingFixtures]
  );

  // Sort past by time descending
  const sortedPast = useMemo(() =>
    [...pastFixtures].sort((a, b) => (b.time || "").localeCompare(a.time || "")),
    [pastFixtures]
  );

  return (
    <>
      {/* LEFT: Live & Completed Results */}
      <section className="fixtures-panel fixtures-sidebar-left">
        <div className="fixtures-container">
          <CalendarBar
            selectedDate={completedDate}
            onSelectDate={handleCompletedDate}
            maxDate={today}
          />

          {/* Live matches Section */}
          <div
            className={`fixture-section live-section-desktop ${
              liveFixtures.length === 0 && !isLoading ? "live-section-empty" : ""
            }`}
          >
            <h2 className="fixture-heading live-heading">
              <span className="live-dot-heading" />
              Live Now
              {liveFixtures.length > 0 && (
                <span className="live-count-badge">{liveFixtures.length}</span>
              )}
            </h2>
            <div className="fixture-list">
              {isLoading ? (
                <SkeletonCards count={2} type="live" />
              ) : liveFixtures.length > 0 ? (
                liveFixtures.map((m) => <LiveCard key={m.id} match={m} />)
              ) : (
                <div className="no-fixtures">
                  <span className="no-fixtures-icon">⚽</span>
                  <span>No matches live right now</span>
                </div>
              )}
            </div>
          </div>

          {/* Completed matches Section */}
          <div className="fixture-section completed-section-desktop">
            <h2 className="fixture-heading past-heading">
              <span className="heading-icon">
                <FiAward />
              </span>{" "}
              Completed Results
            </h2>
            <div className="fixture-list">
              {isLoading ? (
                <SkeletonCards count={3} type="past" />
              ) : sortedPast.length > 0 ? (
                sortedPast.map((m) => <PastCard key={m.id} match={m} />)
              ) : (
                <div className="no-fixtures">
                  <span className="no-fixtures-icon">📋</span>
                  <span>No completed matches for this date</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* RIGHT: Upcoming */}
      <section className="fixtures-panel fixtures-sidebar-right">
        <div className="fixtures-container">
          <CalendarBar
            selectedDate={upcomingDate}
            onSelectDate={handleUpcomingDate}
            minDate={today}
          />

          <div className="fixture-section">
            <h2 className="fixture-heading upcoming-heading">
              <span className="heading-icon">
                <FiCalendar
                  style={{ display: "inline-block", verticalAlign: "middle", marginTop: -2 }}
                />
              </span>{" "}
              Upcoming Matches
            </h2>
            <div className="fixture-list">
              {isLoading ? (
                <SkeletonCards count={4} type="upcoming" />
              ) : sortedUpcoming.length > 0 ? (
                sortedUpcoming.map((m) => <UpcomingCard key={m.id} match={m} />)
              ) : (
                <div className="no-fixtures">
                  <span className="no-fixtures-icon">📅</span>
                  <span>No upcoming matches for this date</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

/* ── Skeleton loading cards ────────────────────────────────────────── */
function SkeletonCards({ count, type }: { count: number; type: "live" | "past" | "upcoming" }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={`skeleton-card skeleton-card-${type}`} style={{ animationDelay: `${i * 0.12}s` }}>
          <div className="skeleton-row">
            <div className="skeleton-pill" />
            <div className="skeleton-pill skeleton-pill-sm" />
          </div>
          {type === "live" ? (
            <div className="skeleton-score-row">
              <div className="skeleton-team-block">
                <div className="skeleton-flag" />
                <div className="skeleton-name" />
              </div>
              <div className="skeleton-score-center">
                <div className="skeleton-digit" />
                <span className="skeleton-sep">–</span>
                <div className="skeleton-digit" />
              </div>
              <div className="skeleton-team-block skeleton-team-right">
                <div className="skeleton-name" />
                <div className="skeleton-flag" />
              </div>
            </div>
          ) : type === "upcoming" ? (
            <div className="skeleton-matchup-row">
              <div className="skeleton-team-block">
                <div className="skeleton-flag" />
                <div className="skeleton-name" />
              </div>
              <div className="skeleton-ko-pill" />
              <div className="skeleton-team-block skeleton-team-right">
                <div className="skeleton-name" />
                <div className="skeleton-flag" />
              </div>
            </div>
          ) : (
            <div className="skeleton-result-row">
              <div className="skeleton-team-block">
                <div className="skeleton-flag" />
                <div className="skeleton-name" />
              </div>
              <div className="skeleton-result-score">
                <div className="skeleton-digit skeleton-digit-sm" />
                <span className="skeleton-sep">–</span>
                <div className="skeleton-digit skeleton-digit-sm" />
              </div>
              <div className="skeleton-team-block skeleton-team-right">
                <div className="skeleton-name" />
                <div className="skeleton-flag" />
              </div>
            </div>
          )}
        </div>
      ))}
    </>
  );
}

/* ── Calendar Bar Component ─────────────────────────────────────────── */
interface CalendarBarProps {
  selectedDate: string;
  onSelectDate: (date: string) => void;
  minDate?: string;
  maxDate?: string;
}

function CalendarBar({ selectedDate, onSelectDate, minDate, maxDate }: CalendarBarProps) {
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

  const fmtIso = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

  const handlePrev = () => {
    const prev = new Date(currentDate);
    prev.setDate(currentDate.getDate() - 1);
    const iso = fmtIso(prev);
    if (!minDate || iso >= minDate) onSelectDate(iso);
    if (!maxDate || iso <= maxDate) onSelectDate(iso);
  };

  const handleNext = () => {
    const next = new Date(currentDate);
    next.setDate(currentDate.getDate() + 1);
    const iso = fmtIso(next);
    if (!minDate || iso >= minDate) onSelectDate(iso);
    if (!maxDate || iso <= maxDate) onSelectDate(iso);
  };

  return (
    <div className="calendar-bar">
      <button className="cal-nav-btn" onClick={handlePrev} aria-label="Previous day">
        <FiChevronLeft />
      </button>

      <div className="cal-dates-row">
        {dates.map((d) => {
          const iso = fmtIso(d);
          const isActive = iso === selectedDate;
          const isToday = iso === fmtIso(new Date());
          const isDisabled = (minDate && iso < minDate) || (maxDate && iso > maxDate);
          return (
            <button
              key={iso}
              className={`cal-date-btn ${isActive ? "active" : ""} ${isToday ? "today" : ""} ${isDisabled ? "disabled" : ""}`}
              onClick={() => !isDisabled && onSelectDate(iso)}
              disabled={!!isDisabled}
            >
              <span className="cal-day-name">
                {d.toLocaleDateString("en-US", { weekday: "short" })}
              </span>
              <span className="cal-day-num">{d.getDate()}</span>
            </button>
          );
        })}
      </div>

      <button className="cal-nav-btn" onClick={handleNext} aria-label="Next day">
        <FiChevronRight />
      </button>

      <div className="cal-picker-wrapper">
        <FiCalendar className="cal-picker-icon" />
        <input
          type="date"
          className="cal-date-picker-input"
          value={selectedDate}
          min={minDate}
          max={maxDate}
          onChange={(e) => {
            if (e.target.value) onSelectDate(e.target.value);
          }}
        />
      </div>
    </div>
  );
}

/* ── Real-time Match Clock ─────────────────────────────────────────── */
type MatchPhase = "pre" | "first_half" | "half_time" | "second_half" | "extra_time" | "full_time";

interface ClockState {
  phase: MatchPhase;
  display: string;        // e.g. "37'", "HT", "74'", "90+2'", "FT"
  progressPct: number;   // 0-100 for the progress bar
  isLive: boolean;
}

function useMatchClock(matchTime: string | undefined, matchDate: string): ClockState {
  const [state, setState] = useState<ClockState>({
    phase: "pre",
    display: "",
    progressPct: 0,
    isLive: false,
  });

  useEffect(() => {
    if (!matchTime || matchTime === "TBD") return;

    const tick = () => {
      try {
        // Parse match start in UTC: "2026-06-19" + "21:00" → "2026-06-19T21:00:00Z"
        const matchStart = new Date(`${matchDate}T${matchTime}:00Z`);
        const now = new Date();
        const diffMs = now.getTime() - matchStart.getTime();
        const totalSeconds = Math.floor(diffMs / 1000);
        const rawMinutes = Math.floor(totalSeconds / 60);

        if (diffMs < 0) {
          // Match hasn't started yet
          setState({ phase: "pre", display: "", progressPct: 0, isLive: false });
          return;
        }

        // Match periods (approximate):
        // 0-45 min → first half
        // 45-50 min → half-time break
        // 50-95 min → second half (kick-off at 50 assumed)
        // 95-105 min → extra time 1st
        // 105-120 min → extra time 2nd
        // > 120 → full time

        if (rawMinutes < 45) {
          // First half: 0-45
          const displayMin = rawMinutes + 1;
          setState({
            phase: "first_half",
            display: `${displayMin}'`,
            progressPct: Math.min((rawMinutes / 45) * 50, 50),
            isLive: true,
          });
        } else if (rawMinutes < 50) {
          // Half-time break
          setState({ phase: "half_time", display: "HT", progressPct: 50, isLive: true });
        } else if (rawMinutes < 95) {
          // Second half: offset is rawMinutes - 50, displayed from 46'
          const shMin = 46 + (rawMinutes - 50);
          const displayMin = shMin > 90 ? 90 : shMin;
          const extraMin = shMin > 90 ? shMin - 90 : 0;
          const display = extraMin > 0 ? `90+${extraMin}'` : `${displayMin}'`;
          setState({
            phase: "second_half",
            display,
            progressPct: 50 + Math.min(((rawMinutes - 50) / 45) * 50, 50),
            isLive: true,
          });
        } else if (rawMinutes < 120) {
          // Extra time
          const etMin = rawMinutes - 95 + 91;
          setState({
            phase: "extra_time",
            display: `${etMin}'`,
            progressPct: 100,
            isLive: true,
          });
        } else {
          // Full time — match over
          setState({ phase: "full_time", display: "FT", progressPct: 100, isLive: false });
        }
      } catch {
        setState({ phase: "pre", display: "", progressPct: 0, isLive: false });
      }
    };

    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [matchTime, matchDate]);

  return state;
}

/* ── Upcoming Card ─────────────────────────────────────────────────── */
function UpcomingCard({ match }: { match: Fixture }) {
  const dateStr = formatDate(match.date);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 30);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className={`upcoming-card-redesign ${visible ? "card-visible" : ""}`}>
      <div className="fc-meta-bar">
        <span className="fc-group-pill">{match.group}</span>
        <span className="fc-date-chip">
          <FiClock style={{ fontSize: 9, marginRight: 3, verticalAlign: "middle" }} />
          {dateStr}
        </span>
      </div>

      <div className="fc-matchup">
        <div className="fc-team fc-team-left">
          <span className="fc-flag">{match.team1.flag}</span>
          <span className="fc-name">{match.team1.name}</span>
        </div>

        <div className="fc-vs-center">
          <span className="fc-kickoff-time">{match.time || "TBD"}</span>
          <span className="fc-vs-label">KO</span>
        </div>

        <div className="fc-team fc-team-right">
          <span className="fc-name fc-name-right">{match.team2.name}</span>
          <span className="fc-flag">{match.team2.flag}</span>
        </div>
      </div>

      {match.venue && (
        <div className="fc-venue">
          <FiMapPin style={{ fontSize: 9, marginRight: 3, verticalAlign: "middle" }} />
          {match.venue}
        </div>
      )}
    </div>
  );
}

/* ── Live Card ─────────────────────────────────────────────────────── */
function LiveCard({ match }: { match: Fixture }) {
  const clock = useMatchClock(match.time, match.date);
  const [scoreFlash, setScoreFlash] = useState(false);
  const prevScore = useRef({ t1: match.team1.score ?? 0, t2: match.team2.score ?? 0 });

  useEffect(() => {
    const t1 = match.team1.score ?? 0;
    const t2 = match.team2.score ?? 0;
    if (t1 !== prevScore.current.t1 || t2 !== prevScore.current.t2) {
      setScoreFlash(true);
      prevScore.current = { t1, t2 };
      const timer = setTimeout(() => setScoreFlash(false), 1400);
      return () => clearTimeout(timer);
    }
  }, [match.team1.score, match.team2.score]);

  const t1Score = match.team1.score ?? 0;
  const t2Score = match.team2.score ?? 0;
  const t1Winning = t1Score > t2Score;
  const t2Winning = t2Score > t1Score;

  const isHT = clock.phase === "half_time";
  const isFT = clock.phase === "full_time";
  const showClock = clock.phase !== "pre" && clock.display !== "";

  return (
    <div className="live-card-redesign">
      {/* Animated top accent bar — only during live play */}
      {clock.isLive && <div className="live-card-glow-bar" />}

      {/* Header row */}
      <div className="fc-live-header">
        <span className="fc-group-pill fc-group-live">{match.group}</span>

        <div className={`fc-live-clock-badge ${isHT ? "fc-badge-ht" : isFT ? "fc-badge-ft" : ""}`}>
          {!isHT && !isFT && <span className="live-pulse-sm" />}
          <span className="fc-live-label">{isHT ? "HT" : isFT ? "FT" : "LIVE"}</span>
          {showClock && !isHT && !isFT && (
            <span className="fc-clock-time">{clock.display}</span>
          )}
        </div>
      </div>

      {/* Hero score */}
      <div className="fc-live-score-hero">
        {/* Team 1 */}
        <div className={`fc-live-team ${t1Winning ? "fc-live-team-winning" : ""}`}>
          <span className="fc-live-flag">{match.team1.flag}</span>
          <span className="fc-live-team-name">{match.team1.name}</span>
          {t1Winning && <span className="fc-winning-dot" />}
        </div>

        {/* Score block */}
        <div className={`fc-live-score-block ${scoreFlash ? "score-flash" : ""}`}>
          <span className={`fc-score-digit ${t1Winning ? "fc-score-winner" : ""}`}>{t1Score}</span>
          <span className="fc-score-sep">–</span>
          <span className={`fc-score-digit ${t2Winning ? "fc-score-winner" : ""}`}>{t2Score}</span>
        </div>

        {/* Team 2 */}
        <div className={`fc-live-team fc-live-team-right ${t2Winning ? "fc-live-team-winning" : ""}`}>
          {t2Winning && <span className="fc-winning-dot" />}
          <span className="fc-live-team-name fc-live-team-name-right">{match.team2.name}</span>
          <span className="fc-live-flag">{match.team2.flag}</span>
        </div>
      </div>

      {/* Match progress bar — shown for all phases except pre */}
      {clock.phase !== "pre" && (
        <div className="fc-match-progress-wrap">
          <div
            className={`fc-match-progress-bar ${isHT ? "fc-progress-ht" : isFT ? "fc-progress-ft" : ""}`}
            style={{ width: `${clock.progressPct}%` }}
          />
        </div>
      )}

      {/* Phase label below bar */}
      {(isHT || isFT) && (
        <div className="fc-phase-label">
          {isHT ? "⏸ Half Time" : "✅ Full Time"}
        </div>
      )}
    </div>
  );
}

/* ── Past Card ─────────────────────────────────────────────────────── */
function PastCard({ match }: { match: Fixture }) {
  const t1Score = match.team1.score ?? 0;
  const t2Score = match.team2.score ?? 0;
  const t1Winning = t1Score > t2Score;
  const t2Winning = t2Score > t1Score;
  const isDraw = t1Score === t2Score;

  return (
    <div className="past-card-redesign">
      <div className="fc-meta-bar">
        <span className="fc-group-pill">{match.group}</span>
        <span className="fc-ft-badge">FT</span>
      </div>

      <div className="fc-result-row">
        <div
          className={`fc-result-team ${
            t1Winning ? "fc-result-winner" : isDraw ? "fc-result-draw" : "fc-result-loser"
          }`}
        >
          <span className="fc-flag">{match.team1.flag}</span>
          <span className="fc-name">{match.team1.name}</span>
        </div>

        <div className="fc-result-score">
          <span className={`fc-rs-digit ${t1Winning ? "fc-rs-win" : isDraw ? "fc-rs-draw" : "fc-rs-lose"}`}>
            {t1Score}
          </span>
          <span className="fc-rs-sep">–</span>
          <span className={`fc-rs-digit ${t2Winning ? "fc-rs-win" : isDraw ? "fc-rs-draw" : "fc-rs-lose"}`}>
            {t2Score}
          </span>
        </div>

        <div
          className={`fc-result-team fc-result-team-right ${
            t2Winning ? "fc-result-winner" : isDraw ? "fc-result-draw" : "fc-result-loser"
          }`}
        >
          <span className="fc-name fc-name-right">{match.team2.name}</span>
          <span className="fc-flag">{match.team2.flag}</span>
        </div>
      </div>
    </div>
  );
}

/* ── Utilities ──────────────────────────────────────────────────────── */
function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr + "T12:00:00").toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}
