"use client";

export default function Footer() {
  return (
    <footer className="site-footer">
      {/* Disclaimer */}
      <div className="disclaimer-bar">
        <span className="disclaimer-icon">⚠️</span>
        <span>
          <strong>Disclaimer:</strong> This application does not host or stream
          native channels. Data and streams are aggregated from publicly
          available indices.
        </span>
      </div>

      {/* Bottom Navigation Buttons */}
      {/* <div className="footer-nav"> */}
      <div className="footer-left">
        <a href="#" className="footer-btn">
          <span className="footer-badge">MENU</span>
          <span>BACK TO MENU</span>
        </a>
        <a href="#" className="footer-btn">
          <span className="footer-badge">RETURN</span>
          <span>PREVIOUS SCREEN</span>
        </a>
      </div>
      <div className="footer-right">
        <a href="#" className="footer-btn">
          <span className="footer-dot green"></span>
          <span>LIVE FIXTURES</span>
        </a>
        <a href="#" className="footer-btn">
          <span className="footer-dot yellow"></span>
          <span>STATS TRACKER</span>
        </a>
      </div>
    </footer>
  );
}
