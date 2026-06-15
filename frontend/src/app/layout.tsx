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
    <html lang="en" className={`${inter.variable} ${outfit.variable}`} suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5, viewport-fit=cover" />
        <meta name="theme-color" content="#0d0312" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <link rel="icon" href="/logo.png" />
      </head>
      <body>{children}</body>
    </html>
  );
}
