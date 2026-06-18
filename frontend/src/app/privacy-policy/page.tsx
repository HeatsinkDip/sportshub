import type { Metadata } from "next";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import Link from "next/link";
import { FiArrowLeft } from "react-icons/fi";

export const metadata: Metadata = {
  title: "Privacy Policy — D'one TV",
  description: "Privacy Policy for D'one TV — How we collect and use your data.",
};

export default function PrivacyPolicyPage() {
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
          <h1>Privacy Policy</h1>
          <p className="policy-date">Last updated: June 2026</p>

          <section>
            <h2>1. Introduction</h2>
            <p>
              Welcome to D'one TV ("we," "our," or "us"). We are committed to protecting your personal
              information and your right to privacy. This Privacy Policy explains how we collect, use,
              and share information about you when you use our website at donetv.com (the "Site").
            </p>
          </section>

          <section>
            <h2>2. Information We Collect</h2>
            <p>We collect information you provide directly to us, and information collected automatically:</p>
            <ul>
              <li><strong>Log Data:</strong> When you visit our Site, our servers automatically record information including your IP address, browser type, pages visited, and the date/time of your visit.</li>
              <li><strong>Cookies:</strong> We use cookies and similar tracking technologies to improve your browsing experience. You can instruct your browser to refuse all cookies or to indicate when a cookie is being sent.</li>
              <li><strong>Usage Data:</strong> We collect information about how you interact with the Site, such as which channels you click and how long you watch.</li>
            </ul>
          </section>

          <section>
            <h2>3. How We Use Your Information</h2>
            <p>We use the information we collect to:</p>
            <ul>
              <li>Operate and improve the Site</li>
              <li>Monitor and analyze usage and trends</li>
              <li>Detect and prevent fraudulent activity</li>
              <li>Comply with legal obligations</li>
            </ul>
          </section>

          <section>
            <h2>4. Advertising — Google AdSense</h2>
            <p>
              We use Google AdSense to display advertisements on our Site. Google AdSense uses cookies
              to serve ads based on your prior visits to this and other websites. You may opt out of
              personalized advertising by visiting{" "}
              <a href="https://www.google.com/settings/ads" target="_blank" rel="noopener noreferrer">
                Google Ads Settings
              </a>.
            </p>
            <p>
              Google's use of advertising cookies enables it and its partners to serve ads to you based
              on your visit to our site and/or other sites on the Internet.
            </p>
          </section>

          <section>
            <h2>5. Third-Party Links and Streams</h2>
            <p>
              Our Site aggregates publicly available stream links from third-party sources. We do not
              host, store, or control any of these streams. We are not responsible for the privacy
              practices of any third-party stream providers.
            </p>
          </section>

          <section>
            <h2>6. Data Retention</h2>
            <p>
              We retain log data for up to 30 days for security and debugging purposes. We do not sell
              your personal information to third parties.
            </p>
          </section>

          <section>
            <h2>7. Your Rights</h2>
            <p>
              Depending on your location, you may have the right to access, correct, or delete personal
              data we hold about you. To exercise these rights, please contact us at the email address
              below.
            </p>
          </section>

          <section>
            <h2>8. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. We will notify you of any changes
              by posting the new policy on this page with an updated date.
            </p>
          </section>

          <section>
            <h2>9. Contact Us</h2>
            <p>
              If you have any questions about this Privacy Policy, please contact us at:{" "}
              <a href="mailto:contact@donetv.com">dip.kundu2015@gmail.com</a>
            </p>
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}
