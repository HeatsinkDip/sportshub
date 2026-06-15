import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
});

export const metadata: Metadata = {
  title: "D'one TV — FIFA World Cup 2026™ Live Streaming",
  description:
    "Watch FIFA World Cup 2026 live streams from multiple channels. Free IPTV streaming hub powered by iptv-org.",
  keywords: [
    "FIFA World Cup 2026",
    "IPTV",
    "live streaming",
    "football",
    "soccer",
    "World Cup live",
  ],
  openGraph: {
    title: "D'one TV — FIFA World Cup 2026™ Live",
    description: "Watch World Cup 2026 live streams from 28+ channels",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${outfit.variable}`}>
      <head>
        <link rel="icon" href="/logo.png" />
      </head>
      <body>{children}</body>
    </html>
  );
}
