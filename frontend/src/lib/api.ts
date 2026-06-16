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

export const FALLBACK_CHANNELS: Channel[] = [
  {
    id: "win_sports_full_hd_",
    name: "WIN Sports (Full HD)",
    category: "featured",
    logo: "https://i.imgur.com/DuSSrHV.png",
    quality: "FHD",
    servers: [{ url: "https://1nyaler.streamhostingcdn.top/stream/32/index.m3u8", name: "Win Sports Custom", quality: "FHD", referrer: "", user_agent: "" }]
  },
  {
    id: "cctv_5_full_hd_",
    name: "CCTV 5 (Full HD)",
    category: "featured",
    logo: "https://upload.wikimedia.org/wikipedia/commons/d/d3/CCTVNewLogo.svg",
    quality: "FHD",
    servers: [{ url: "https://live12.szyac.com/live/35291799.m3u8", name: "CCTV Custom", quality: "FHD", referrer: "", user_agent: "" }]
  },
  {
    id: "elta_sports_fhd_",
    name: "ELTA Sports (FHD)",
    category: "featured",
    logo: "https://upload.wikimedia.org/wikipedia/commons/5/5b/ELTA_logo.svg",
    quality: "FHD",
    servers: [{ url: "https://live12.szyac.com/live/22457616.m3u8", name: "ELTA Sports Custom", quality: "FHD", referrer: "", user_agent: "" }]
  },
  {
    id: "macao_sports_fhd_",
    name: "Macao Sports (FHD)",
    category: "featured",
    logo: "https://static.wikia.nocookie.net/logopedia/images/2/2c/TDMSport.png",
    quality: "FHD",
    servers: [{ url: "https://live12.szyac.com/live/09139583.m3u8", name: "Macao Sports Custom", quality: "FHD", referrer: "", user_agent: "" }]
  },
  {
    id: "dazn_full_hd_",
    name: "DAZN (Full HD)",
    category: "featured",
    logo: "https://i.postimg.cc/VsW3Jsrz/logo-DAZN-Combat.png",
    quality: "FHD",
    servers: [{ url: "https://1nyaler.streamhostingcdn.top/stream/94/index.m3u8", name: "DAZN Custom", quality: "FHD", referrer: "", user_agent: "" }]
  },
  {
    id: "colatv",
    name: "ColaTV",
    category: "featured",
    logo: "https://colatv.app/favicon.png",
    quality: "FHD",
    servers: [{ url: "https://live05.msdht.app/live/24561735.m3u8", name: "ColaTV Custom", quality: "FHD", referrer: "", user_agent: "" }]
  }
];

export function xorHexEncrypt(data: string, key: number = 0x5A): string {
  let result = "";
  for (let i = 0; i < data.length; i++) {
    const xored = data.charCodeAt(i) ^ key;
    result += xored.toString(16).padStart(2, "0");
  }
  return result;
}

export function xorHexDecrypt(hexStr: string, key: number = 0x5A): string {
  try {
    let result = "";
    for (let i = 0; i < hexStr.length; i += 2) {
      const val = parseInt(hexStr.substring(i, i + 2), 16);
      result += String.fromCharCode(val ^ key);
    }
    return result;
  } catch (e) {
    return "";
  }
}

export async function fetchChannels(): Promise<Channel[]> {
  try {
    const res = await fetch(`${API_BASE}/api/channels`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.payload) {
      const decrypted = xorHexDecrypt(data.payload);
      const channels = JSON.parse(decrypted);
      return channels && channels.length > 0 ? channels : FALLBACK_CHANNELS;
    }
    return data.channels && data.channels.length > 0 ? data.channels : FALLBACK_CHANNELS;
  } catch (err) {
    console.error("Failed to fetch channels, using fallback list:", err);
    return FALLBACK_CHANNELS;
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

export function getProxyStreamUrl(server: Server): string {
  if (isBdixOrLocal(server.url)) {
    return server.url;
  }

  const config = {
    referrer: server.referrer || "",
    user_agent: server.user_agent || "",
  };
  const hexConfig = xorHexEncrypt(JSON.stringify(config));
  const hexUrl = xorHexEncrypt(server.url);
  return `${API_BASE}/api/proxy-stream/c/${hexConfig}/${hexUrl}/`;
}
