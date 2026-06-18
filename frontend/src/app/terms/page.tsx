import type { Metadata } from "next";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import Link from "next/link";
import { FiArrowLeft } from "react-icons/fi";

export const metadata: Metadata = {
  title: "Terms of Service — D'one TV",
  description: "Terms of Service for D'one TV — Rules and guidelines for using our site.",
};

export default function TermsPage() {
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
          <h1>Terms of Service</h1>
          <p className="policy-date">Last updated: June 2026</p>

          <section>
            <h2>1. Acceptance of Terms</h2>
            <p>
              By accessing and using D'one TV ("the Site"), you accept and agree to be bound by
              these Terms of Service. If you do not agree to these terms, please do not use the Site.
            </p>
          </section>

          <section>
            <h2>2. Description of Service</h2>
            <p>
              D'one TV is a sports information and stream aggregation site that provides links to
              publicly available third-party live stream sources for informational and educational
              purposes. We do not host, upload, or store any video content on our servers.
            </p>
          </section>

          <section>
            <h2>3. User Responsibilities</h2>
            <p>You agree to use the Site only for lawful purposes and in accordance with these Terms. You agree NOT to:</p>
            <ul>
              <li>Use the Site in any way that violates applicable local, national, or international law or regulation</li>
              <li>Attempt to gain unauthorized access to any part of the Site</li>
              <li>Use automated bots or scrapers to access the Site</li>
              <li>Transmit any unsolicited commercial communications</li>
              <li>Impersonate or attempt to impersonate any person or entity</li>
            </ul>
          </section>

          <section>
            <h2>4. Third-Party Content</h2>
            <p>
              The Site aggregates links to streams from third-party providers. We have no control
              over the content, availability, or quality of these third-party streams. We are not
              responsible for any content delivered by third-party stream providers.
            </p>
            <p>
              If you believe any content linked to by this Site infringes your copyright,
              please review our{" "}
              <a href="/dmca">DMCA Policy</a> for information on how to submit a removal request.
            </p>
          </section>

          <section>
            <h2>5. Intellectual Property</h2>
            <p>
              The Site's design, layout, text, and original content are the property of D'one TV
              and are protected by applicable intellectual property laws. The stream links aggregated
              by this Site remain the property of their respective owners.
            </p>
          </section>

          <section>
            <h2>6. Disclaimers</h2>
            <p>
              THE SITE IS PROVIDED ON AN "AS IS" AND "AS AVAILABLE" BASIS WITHOUT ANY WARRANTIES
              OF ANY KIND. WE DO NOT WARRANT THAT THE SITE WILL BE UNINTERRUPTED, ERROR-FREE,
              OR FREE OF VIRUSES OR OTHER HARMFUL COMPONENTS.
            </p>
            <p>
              Stream availability depends entirely on third-party providers and may change without
              notice. We make no guarantees about the availability of any specific stream.
            </p>
          </section>

          <section>
            <h2>7. Limitation of Liability</h2>
            <p>
              TO THE FULLEST EXTENT PERMITTED BY LAW, D'ONE TV SHALL NOT BE LIABLE FOR ANY
              INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING FROM
              YOUR USE OF, OR INABILITY TO USE, THE SITE.
            </p>
          </section>

          <section>
            <h2>8. Governing Law</h2>
            <p>
              These Terms shall be governed by and construed in accordance with applicable law,
              without regard to its conflict of law provisions.
            </p>
          </section>

          <section>
            <h2>9. Changes to Terms</h2>
            <p>
              We reserve the right to modify these Terms at any time. We will notify you of any
              changes by posting the new Terms on this page with an updated date. Your continued
              use of the Site after any changes constitutes your acceptance of the new Terms.
            </p>
          </section>

          <section>
            <h2>10. Contact</h2>
            <p>
              For questions about these Terms, please contact us at:{" "}
              <a href="mailto:contact@donetv.com">dip.kundu2015@gmail.com</a>
            </p>
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}
