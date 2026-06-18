import type { Metadata } from "next";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import Link from "next/link";
import { FiArrowLeft } from "react-icons/fi";

export const metadata: Metadata = {
  title: "DMCA & Copyright — D'one TV",
  description: "DMCA Policy for D'one TV. Submit copyright removal requests here.",
};

export default function DmcaPage() {
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
          <h1>DMCA & Copyright Policy</h1>
          <p className="policy-date">Last updated: June 2026</p>

          <section>
            <h2>Our Position on Copyright</h2>
            <p>
              D'one TV respects the intellectual property rights of others. We do not host,
              upload, or store any video content on our servers. Our site aggregates links to
              streams that are publicly accessible on the internet from third-party providers.
            </p>
          </section>

          <section>
            <h2>Digital Millennium Copyright Act (DMCA)</h2>
            <p>
              In accordance with the Digital Millennium Copyright Act of 1998, we will respond
              promptly to claims of copyright infringement committed using our website if such
              claims are reported to us.
            </p>
          </section>

          <section>
            <h2>How to Submit a DMCA Takedown Notice</h2>
            <p>
              If you are a copyright owner, or authorized to act on behalf of a copyright owner,
              and you believe that content linked to from our Site infringes your copyright,
              please send a notice to us containing the following information:
            </p>
            <ol>
              <li>A physical or electronic signature of the copyright owner or authorized representative</li>
              <li>Identification of the copyrighted work claimed to be infringed</li>
              <li>The specific URL(s) on our Site linking to the alleged infringing content</li>
              <li>Your contact information (name, address, telephone number, email address)</li>
              <li>
                A statement that you have a good faith belief that the use of the material is not
                authorized by the copyright owner, its agent, or the law
              </li>
              <li>
                A statement that the information in the notification is accurate and, under penalty
                of perjury, that you are the copyright owner or authorized to act on their behalf
              </li>
            </ol>
          </section>

          <section>
            <h2>Send DMCA Notices To</h2>
            <p>
              Email: <a href="mailto:dmca@donetv.com">dmca@donetv.com</a>
            </p>
            <p>
              We will review all valid DMCA notices and remove links to allegedly infringing
              content within 48 hours of receipt.
            </p>
          </section>

          <section>
            <h2>Counter-Notice</h2>
            <p>
              If you believe that content was incorrectly removed, you may submit a counter-notice
              to the email address above. Counter-notices must meet the requirements set forth in
              the DMCA.
            </p>
          </section>

          <section>
            <h2>Repeat Infringers</h2>
            <p>
              It is our policy to disable access to users who are repeat copyright infringers in
              appropriate circumstances.
            </p>
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}
