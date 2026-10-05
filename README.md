# Lumberfi Commission Platform

A full-stack, enterprise-grade Sales Incentive Compensation Management platform built with **FastAPI**, **MongoDB Atlas**, and **React + TypeScript (Vite)**.

---

## Architecture Overview

```text
Browser
  │
  ▼
Render Static Site (React + Vite + Recharts)
  │
  ▼ HTTPS REST APIs (/api/*)
Render Free Web Service (FastAPI + Uvicorn)
  │
  ▼ PyMongo Connection (TLS)
MongoDB Atlas (Cloud Database)
```

- **Calculations Core**: Validated parity calculation engine producing 100% exact parity with historical financial models.
- **Server-Side RBAC**: Strict role-scoped access control for `Admin`, `Manager`, and `Account Executive (AE)`.
- **JWT Authentication**: Secure bcrypt password hashing and signed HS256 tokens.
- **Interactive Visualizations**: Executive KPI summaries, team performance breakdowns, and monthly revenue/commission/payout trajectories.

---

## Local Development

### Prerequisites
- Python 3.13+
- Node.js 18+ and npm

### 1. Backend Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your MongoDB Atlas URI and JWT_SECRET

# Run FastAPI with live reload
uvicorn backend.app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install

# Start Vite dev server (proxies /api to http://127.0.0.1:8000)
npm run dev
```

Visit `http://localhost:5173` in your browser.

---

## Deployment to Render (Free Tier)

The application is structured for independent deployment of the backend and frontend on Render's free tier.

### Prerequisites: MongoDB Atlas Network Access
1. Open your **MongoDB Atlas** dashboard.
2. Go to **Network Access** → **IP Access List**.
3. Add IP Address: `0.0.0.0/0` (Allow access from anywhere, required because Render free web services use dynamic outbound IP addresses).
4. Verify your database user credentials and copy your connection string (`MONGODB_URI`).

---

### Method 1: Automated Blueprint Deployment (`render.yaml`)
1. In the **Render Dashboard**, click **New +** → **Blueprint**.
2. Connect your Git repository.
3. Render reads `render.yaml` and initializes:
   - **`lumberfi-backend`** (Python Web Service)
   - **`lumberfi-frontend`** (Static Site)
4. When prompted, fill in the secret environment variables:
   - `MONGODB_URI`: Your MongoDB Atlas connection URI.
   - `CORS_ORIGINS`: Set to your frontend static site URL (e.g., `https://lumberfi-frontend.onrender.com`).
   - `VITE_API_URL`: Set to your backend web service URL (e.g., `https://lumberfi-backend.onrender.com`).
5. Click **Apply**.

---

### Method 2: Manual Dashboard Configuration

#### 1. Backend Web Service
In Render Dashboard, click **New +** → **Web Service**:
- **Name**: `lumberfi-backend`
- **Region**: Oregon (or nearest to your Atlas cluster)
- **Branch**: `main`
- **Root Directory**: *(leave blank — repository root)*
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- **Instance Type**: `Free`
- **Health Check Path**: `/health`

**Backend Environment Variables**:
| Variable | Value / Description |
|---|---|
| `PYTHON_VERSION` | `3.13.0` |
| `MONGODB_URI` | `mongodb+srv://<user>:<password>@cluster.mongodb.net/lumberfi?retryWrites=true&w=majority` |
| `JWT_SECRET` | 32+ character random string (e.g. generated via `openssl rand -hex 32`) |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` |
| `DEFAULT_DEMO_PASSWORD` | `demo123` |
| `CORS_ORIGINS` | Your frontend Render URL (e.g. `https://lumberfi-frontend.onrender.com`) |

Click **Create Web Service**. Once deployed, copy your backend service URL (e.g., `https://lumberfi-backend.onrender.com`).

---

#### 2. Frontend Static Site
In Render Dashboard, click **New +** → **Static Site**:
- **Name**: `lumberfi-frontend`
- **Branch**: `main`
- **Root Directory**: `frontend`
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `dist`

**Frontend Environment Variables**:
| Variable | Value / Description |
|---|---|
| `VITE_API_URL` | Your Render backend URL from above (e.g. `https://lumberfi-backend.onrender.com`) |

Click **Create Static Site**.

---

### Connecting CORS Between Services
After the frontend static site is created:
1. Copy the frontend URL (e.g. `https://lumberfi-frontend.onrender.com`).
2. Go to your `lumberfi-backend` service → **Environment**.
3. Set `CORS_ORIGINS` to `https://lumberfi-frontend.onrender.com`.
4. Render will automatically redeploy the backend with the new allowed origin.

---

## Health Check & Verification

- **API Health Endpoint**: `GET /health`
  - Response: `{"status": "ok"}`
  - HTTP Status: `200 OK`
- **Automated Regression Suite**:
  ```bash
  python -m pytest backend/tests/ -v
  ```
- **Frontend Production Build**:
  ```bash
  npm --prefix frontend run build
  ```
