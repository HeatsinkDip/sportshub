const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Server {
  url: string;
  name: string;
  quality: string;
  referrer: string;
  user_agent: string;
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

export async function fetchFixtures(): Promise<FixturesData> {
  try {
    const res = await fetch(`${API_BASE}/api/fixtures`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch fixtures:", err);
    return { upcoming: [], past: [], live: [] };
  }
}

export function getProxyStreamUrl(server: Server): string {
  const params = new URLSearchParams({ url: server.url });
  if (server.referrer) params.set("referrer", server.referrer);
  if (server.user_agent) params.set("user_agent", server.user_agent);
  return `${API_BASE}/api/proxy-stream?${params.toString()}`;
}
