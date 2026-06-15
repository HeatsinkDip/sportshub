"use client";

import Image from "next/image";

export default function Header() {
  return (
    <header className="site-header">
      <div className="header-inner">
        <div className="header-meta">
          <span className="tournament-badge">FIFA World Cup 2026</span>
        </div>
        <div className="header-brand">
          <Image
            src="/logo.png"
            alt="D'one TV"
            width={180}
            height={60}
            className="header-logo"
            priority
          />
        </div>
        {/* <div className="header-meta">
          <span className="header-tagline">
            D&apos;one<span className="header-tagline-sub">SPORTS HUB</span>
          </span>
        </div> */}
      </div>
    </header>
  );
}
