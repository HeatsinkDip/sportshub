"use client";

import ScrollVelocity from "./ScrollVelocity";

export default function Footer() {
  return (
    <footer className="site-footer">
      {/* Disclaimer scrolling velocity text */}
      <div className="disclaimer-scroll-wrapper">
        <ScrollVelocity
          texts={["⚠️ Disclaimer: This app does not host or stream World Cup IPTV channels; all streams are sourced from publicly available third-party providers."]}
          velocity={-20}
          className="disclaimer-velocity-text"
          numCopies={4}
        />
      </div>
    </footer>
  );
}
