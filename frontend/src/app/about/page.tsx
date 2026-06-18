import type { Metadata } from "next";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import Link from "next/link";
import { FiArrowLeft } from "react-icons/fi";

export const metadata: Metadata = {
  title: "About D'one TV — FIFA World Cup 2026 Live Streaming",
  description:
    "Learn about D'one TV — a free sports streaming aggregator for FIFA World Cup 2026 live matches.",
};

export default function AboutPage() {
  return (
    <div className="app-root">
      <Header />

      <main className="policy-page">
        <div className="back-btn-wrapper">
          <Link href="/" className="back-to-home">
            <FiArrowLeft /> Back to Stream
          </Link>
        </div>

        <div className="policy-container">
          <h1>About D&apos;one TV</h1>

          <section>
            <h2>Who We Are</h2>
            <p>
              D'one TV is a free sports streaming aggregator focused on the FIFA World Cup 2026™.
              We bring together publicly available live stream links from across the internet into
              one easy-to-use interface, so football fans around the world can follow their
              favourite matches.
            </p>
          </section>

          <section>
            <h2>What We Do</h2>
            <p>
              Our platform aggregates stream links from publicly available third-party providers,
              IPTV directories, and open-source playlists. We do not host, store, or produce
              any video content ourselves — we simply index and organize publicly available
              streams in one place.
            </p>
            <p>Features include:</p>
            <ul>
              <li>🎯 Live stream aggregation from 30+ channels worldwide</li>
              <li>📅 Live match fixtures, results, and upcoming schedules</li>
              <li>📊 Live match scores and real-time updates</li>
              <li>📺 Multiple server fallbacks for each channel</li>
              <li>📱 Fully responsive — works on mobile, tablet, and desktop</li>
            </ul>
          </section>

          <section>
            <h2>Disclaimer</h2>
            <p>
              D'one TV is an independent aggregator and is not affiliated with, endorsed by, or
              officially connected to FIFA, any football governing body, or any broadcaster.
              The FIFA World Cup™ name and brand are the property of FIFA.
            </p>
            <p>
              All stream links on this site point to content hosted on third-party servers.
              We are not responsible for the content, quality, or legality of third-party streams.
              If you are a rights holder and have concerns about a link on our site, please visit
              our <a href="/dmca">DMCA page</a>.
            </p>
          </section>

          <section>
            <h2>Contact</h2>
            <p>
              For general inquiries:{" "}
              <a href="mailto:contact@donetv.com">dip.kundu2015@gmail.com</a>
            </p>
            <p>
              For copyright / DMCA requests:{" "}
              <a href="mailto:dmca@donetv.com">dip.kundu2015@gmail.com</a>
            </p>
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}
