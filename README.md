# D'one TV — FIFA World Cup 2026™ Live Streaming Hub

A premium, timezone-aware, high-performance web dashboard for live streaming the FIFA World Cup 2026™ (June 11 – July 19, 2026). It aggregates IPTV streams, dynamically translates schedules, overlays live scores, and provides low-latency video playback.

---

## 🚀 Key Features

### 📺 Advanced Live Streaming
* **IPTV Integration**: Parses M3U playlists, automatically backfilling missing stream metadata.
* **Low-Latency Video Playback**: Uses customized, low-buffer configurations for HLS.js and Dash.js to load streams quickly.
* **Custom CORS Proxy**: Proxies HLS (`.m3u8`) and DASH (`.mpd`) manifests and nested `.ts`/`.m4s` segments using a global connection pool, resolving browser cross-origin policy blocks.
* **Accurate Premium Logos**: Official, high-resolution logo mappings for premium sports channels (e.g., CCTV 5, ELTA Sports, Macao Sports/TDM, ColaTV).

### ⚽ Timezone-Aware Fixtures Dashboard
* **Dynamic World Cup Schedule**: Fetches official schedule and stadium metadata in real-time from the [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json/tree/master/2026) repository, updating every 15 minutes.
* **Live Score Overlays**: Integrates Sportmonks & Football-Data APIs to overlay live match statistics on top of the fixture schedule.
* **Automatic Timezone Shifts**: Converts UTC match datetimes to the user's browser local date and time using their local timezone offset (`tz_offset`).
* **Digital Header Clock**: Monospace live digital clock in the header tracking local time (HH:MM:SS) with an interactive cyber-neon glow.

### 📱 Premium Responsive Layout
* **Desktop Dashboard**: 3-column split view aligning with the video player height:
  * **Left Sidebar**: Live Matches & Completed Results (filterable by date via inline calendar).
  * **Center**: Low-latency Video Player & Carousel Channel Grid.
  * **Right Sidebar**: Upcoming Matches (filterable by date).
* **Mobile View**: Bottom navigation tab layout styled like a native mobile app:
  * **Live Stream**: Player + Channels Grid.
  * **Live Score**: Current Live-only Matches.
  * **Results**: Date-filterable Completed Matches.
  * **Upcoming Match**: Date-filterable Upcoming Matches.

---

## 🛠 Tech Stack

* **Backend**: FastAPI, Python 3.10+, HTTPX (Async Client), Uvicorn.
* **Frontend**: Next.js 15+ (App Router, Turbopack), React 19, TypeScript, Vanilla CSS (Glassmorphism & Cyberpunk Neon).

---

## ⚙️ Getting Started

### 1. Backend Setup (FastAPI)
Navigate to the backend directory, configure the environment, and start the uvicorn server.

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch FastAPI development server
python main.py
```
*The backend server will run on [http://localhost:8000](http://localhost:8000).*

### 2. Frontend Setup (Next.js)
Open a new terminal window, navigate to the frontend directory, install npm packages, and spin up the development build.

```bash
# Navigate to frontend
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```
*The web interface will run on [http://localhost:3000](http://localhost:3000).*

---

## 🗂 Project Structure

```
├── backend/
│   ├── main.py                # FastAPI main routes, stream proxies & refresh schedules
│   ├── fixtures_scraper.py    # Openfootball dynamic parser, timezone shift, API overlay
│   ├── m3u_parser.py          # IPTV playlist parser and custom channel logo mapping
│   ├── requirements.txt       # Python backend dependencies
│   └── channels_cache.json    # Local cached channels list (gitignored)
│
├── frontend/
│   ├── src/app/
│   │   ├── page.tsx           # Home dashboard & tab switcher
│   │   ├── layout.tsx         # Root layout with fonts
│   │   └── globals.css        # Layout grid, neon tokens & responsive styling
│   ├── src/components/
│   │   ├── Header.tsx         # Header navbar with local digital clock
│   │   ├── VideoPlayer.tsx    # Low-latency tuned HLS/DASH media player
│   │   ├── FixturesSidebar.tsx# Grouped completed/live/upcoming sidebars
│   │   └── ChannelGrid.tsx    # Channels selector carousel
│   └── src/lib/api.ts         # Frontend fetch client passing tz_offset
```
