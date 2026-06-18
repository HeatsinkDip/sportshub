"use client";

import Link from "next/link";
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

      <div className="footer-nav" style={{ padding: "8px 24px", marginTop: "4px" }}>
        <div className="footer-left">
          <span>&copy; {new Date().getFullYear()} D'one TV. All rights reserved.</span>
        </div>
        <div className="footer-right" style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <Link href="/about" className="footer-link">About</Link>
          <span>&bull;</span>
          <Link href="/privacy-policy" className="footer-link">Privacy Policy</Link>
          <span>&bull;</span>
          <Link href="/terms" className="footer-link">Terms</Link>
          <span>&bull;</span>
          <Link href="/dmca" className="footer-link">DMCA</Link>
        </div>
      </div>
    </footer>
  );
}
