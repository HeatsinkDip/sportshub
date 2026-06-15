const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Server {
  url: string;
  name: string;
  quality: string;
  referrer: string;
  user_agent: string;
  license_type?: string;
  license_key?: string;
}

export interface Channel {
  id: string;
  name: string;
  category: string;
  logo: string;
  quality: string;
  servers: Server[];
}

export interface Team {
  name: string;
  code: string;
  flag: string;
  score?: number;
}

export interface Fixture {
  id: number;
  group: string;
  date: string;
  time?: string;
  team1: Team;
  team2: Team;
  venue?: string;
  status: "upcoming" | "live" | "completed";
}

export interface FixturesData {
  upcoming: Fixture[];
  past: Fixture[];
  live: Fixture[];
}

export async function fetchChannels(): Promise<Channel[]> {
  try {
    const res = await fetch(`${API_BASE}/api/channels`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.channels || [];
  } catch (err) {
    console.error("Failed to fetch channels:", err);
    return [];
  }
}

export async function fetchFixtures(date?: string): Promise<FixturesData> {
  try {
    const tzOffset = new Date().getTimezoneOffset(); // minutes behind UTC (e.g. -330 for IST)
    const params = new URLSearchParams();
    if (date) params.set("date", date);
    params.set("tz_offset", String(tzOffset));
    const url = `${API_BASE}/api/fixtures?${params.toString()}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch fixtures:", err);
    return { upcoming: [], past: [], live: [] };
  }
}

export function isBdixOrLocal(urlStr: string): boolean {
  try {
    const url = new URL(urlStr);
    const host = url.hostname.toLowerCase();
    
    // Check for loopback and local ranges
    if (
      host === "localhost" ||
      host === "127.0.0.1" ||
      host.startsWith("10.") ||
      host.startsWith("192.168.")
    ) {
      return true;
    }
    
    // Check 172.16.x.x to 172.31.x.x
    const parts = host.split(".");
    if (parts.length === 4) {
      const first = parseInt(parts[0], 10);
      const second = parseInt(parts[1], 10);
      if (first === 172 && second >= 16 && second <= 31) {
        return true;
      }
    }
    
    return false;
  } catch (e) {
    const lower = urlStr.toLowerCase();
    return lower.startsWith("http://10.") || lower.startsWith("http://192.168.");
  }
}

function stringToHex(str: string): string {
  return Array.from(new TextEncoder().encode(str))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

export function getProxyStreamUrl(server: Server): string {
  if (isBdixOrLocal(server.url)) {
    return server.url;
  }

  const isDash = server.url.includes(".mpd") || server.url.includes("mpd");

  if (isDash) {
    const config = {
      referrer: server.referrer || "",
      user_agent: server.user_agent || "",
    };
    const hexConfig = stringToHex(JSON.stringify(config));
    const hexUrl = stringToHex(server.url);
    return `${API_BASE}/api/proxy-stream/c/${hexConfig}/${hexUrl}/`;
  }

  const params = new URLSearchParams({ url: server.url });
  if (server.referrer) params.set("referrer", server.referrer);
  if (server.user_agent) params.set("user_agent", server.user_agent);
  return `${API_BASE}/api/proxy-stream?${params.toString()}`;
}
