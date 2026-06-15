# Deployment Guide — D'one TV

This guide outlines how to deploy the **Next.js frontend** on Vercel and the **FastAPI backend** on a persistent hosting platform (like Render or Railway).

---

## 1. Deploying the Backend (FastAPI)

Since the backend performs background scraping (refreshing playlists and fixtures every 10 minutes) and caches stream channels in memory, it requires a **persistent hosting service**. Do not deploy it directly to Vercel Serverless Functions.

We recommend using **Render** (free/paid tier) or **Railway** (paid tier).

### Deploying on Render (Web Service)
1. Sign up/Log in to [Render](https://render.com/).
2. Click **New** -> **Web Service**.
3. Connect your GitHub repository containing the project.
4. Configure the following settings:
   *   **Name**: `sportshub-backend` (or similar)
   *   **Language**: `Python 3`
   *   **Root Directory**: `backend` (very important: set this to the subfolder `backend` where python code lives)
   *   **Build Command**: `pip install -r requirements.txt`
   *   **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Click **Create Web Service**.
6. Once deployed, Render will provide a URL. Your actual deployed backend URL is: `https://sportshub-backend-ha1v.onrender.com`. Copy this URL for the frontend configuration.

### Deploying on Railway
1. Sign up/Log in to [Railway](https://railway.app/).
2. Click **New Project** -> **Deploy from GitHub Repo**.
3. Select your repository.
4. In the service settings, configure:
   *   **Root Directory**: `backend`
   *   **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Railway will automatically build and deploy the app, exposing a public URL.

---

## 2. Deploying the Frontend (Next.js) on Vercel

Vercel is the native platform for Next.js and handles frontend deployment perfectly.

1. Sign up/Log in to [Vercel](https://vercel.com/).
2. Click **Add New** -> **Project**.
3. Import your GitHub repository.
4. Configure the following settings:
   *   **Framework Preset**: `Next.js`
   *   **Root Directory**: `frontend` (very important: set this to the subfolder `frontend` where the Next.js files live)
5. Expand the **Environment Variables** section and add:
   *   **Key**: `NEXT_PUBLIC_API_URL`
   *   **Value**: `https://sportshub-backend-ha1v.onrender.com`
6. Click **Deploy**.
7. Once deployment is complete, Vercel will give you a public URL (e.g., `https://sportshub.vercel.app`).

---

## 3. CORS Configuration (Optional Security Polish)

In `backend/main.py`, CORS is configured to allow all origins (`*`) by default, which works immediately out-of-the-box. If you want to restrict access to only your production frontend:
1. Open `backend/main.py`.
2. Locate the `CORSMiddleware` configuration around line 62.
3. Update `allow_origins` to include your Vercel URL:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "http://localhost:3000",
           "https://your-vercel-domain.vercel.app",  # Add your live frontend URL here
       ],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
