import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import DotField from "@/components/DotField";

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
    <html lang="en" className={`${inter.variable} ${outfit.variable}`} suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5, viewport-fit=cover" />
        <meta name="theme-color" content="#0d0312" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        {/* Google AdSense: publisher verification meta tag */}
        <meta name="google-adsense-account" content="ca-pub-9012667878288069" />
        <link rel="icon" href="/logo.png" />
      </head>
      <body>
        <div className="background-field-wrapper">
          <DotField />
        </div>
        {children}
        {/*
          Google AdSense — using Next.js Script for correct placement in final HTML.
          strategy="afterInteractive" ensures it loads after page is interactive
          and appears in the source HTML that Google's crawler reads.
        */}
        <Script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9012667878288069"
          crossOrigin="anonymous"
          strategy="afterInteractive"
        />
      </body>
    </html>
  );
}
