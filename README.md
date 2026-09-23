# VELORA — Premium Women’s Fashion E-commerce Platform

Production-oriented internet-магазин женской одежды.

## Architecture

- **Backend**: FastAPI + SQLAlchemy 2 + PostgreSQL + Redis
- **Frontend**: React + Vite + TypeScript + Tailwind (PWA-ready)
- **Deployment**: Railway (Postgres + Redis already created by you)

## Project Structure

```
velora/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/             # Routers
│   │   ├── core/            # Config, security, database
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   └── ...
│   ├── alembic/             # Migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # React PWA
├── .env.example
├── railway.toml
└── README.md
```

## Railway Deployment (Backend)

You already have PostgreSQL and Redis services.

### 1. Create Backend Service

1. New → GitHub Repo → select this repository
2. Root Directory: `/` (or leave empty)
3. Railway will detect `railway.toml` and `backend/Dockerfile`

### 2. Link Services

- Link your existing **PostgreSQL** service → Railway injects `DATABASE_URL`
- Link your existing **Redis** service → Railway injects `REDIS_URL`

### 3. Set Environment Variables

Copy from `.env.example` and set at least:

```
SECRET_KEY=<generate long random string>
JWT_SECRET=<generate another long random string>
ADMIN_PHONE=+992XXXXXXXXX
ADMIN_PASSWORD=<strong password>
CORS_ORIGINS=https://your-frontend-domain.railway.app
APP_URL=https://your-frontend-domain.railway.app
API_URL=https://your-backend-domain.railway.app
```

Generate secrets:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Deploy

Railway will:
1. Build Docker image
2. Run `alembic upgrade head`
3. Start Uvicorn on `$PORT`

Health check: `GET /health`  
Readiness: `GET /ready`

### 5. Frontend (separate service recommended)

Create a second Railway service for frontend:

- Build command: `cd frontend && npm install && npm run build`
- Start command: `npx serve -s frontend/dist -l $PORT`
- Or use Cloudflare Pages / Vercel for static frontend.

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env with local DATABASE_URL and REDIS_URL
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Current Status (STAGE 1 + partial STAGE 2)

✅ Project structure  
✅ Backend foundation (FastAPI, config, security, logging)  
✅ Database models (users, products, inventory, cart, orders, finance, delivery, system)  
✅ Alembic setup  
✅ Health / Ready endpoints  
✅ Auth (register + login with JWT + Argon2)  
✅ Docker + railway.toml  
✅ Frontend skeleton (React + Vite + Tailwind + PWA + mobile nav)  
✅ .env.example + .gitignore + README  

### Next stages (to be continued)

- STAGE 3: Full RBAC + seed roles/permissions
- STAGE 4: Products, catalog, search, cart API
- STAGE 5–6: Balance, checkout, order state machine
- STAGE 7+: Full UI, Admin/Courier/Owner panels, delivery, AI, etc.

## Important Notes

- Money uses `NUMERIC(12,2)` + Python `Decimal` — never float.
- Inventory concurrency protected by reservations + row locking (to be fully implemented in services).
- No fake payments / GPS / AI in production code.
- Logo file was not present in the original prompt attachments — add `frontend/public/logo.png` when available.
- S3, Maps, AI, Push require external credentials (documented in `.env.example`).

## License

Private — VELORA project.
