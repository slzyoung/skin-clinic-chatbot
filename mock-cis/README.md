# Mock CIS (Clinic Information System) Service

FastAPI microservice that simulates an external **Clinic Information System (CIS)**. It pushes branch and doctor master data to the backend via **RSA-signed webhooks**.

---

## Key Features

- **Push-Only Event Architecture**: Sends real-time data pushes to the Backend Webhook endpoint (`POST /api/webhooks/cis`).
- **RSA Signature Security**: Signs raw JSON payloads with `keys/private_key.pem` (RSA-SHA256) and passes the signature in the `X-Signature` HTTP header.
- **Automated Startup & Hourly Sync**: Spawns a background task on container startup to push initial mock data to the backend and repeats every **1 hour** automatically.
- **Manual Trigger Endpoints**: Exposes FastAPI trigger endpoints for on-demand testing.

---

## Directory Structure

```text
mock-cis/
├── keys/
│   ├── private_key.pem       # RSA Private Key (used by mock-cis to sign payloads)
│   └── public_key.pem        # RSA Public Key (shared with backend for verification)
├── Dockerfile                # Container build definition
├── main.py                   # FastAPI application, mock datasets, RSA signing & background worker
└── requirements.txt          # Dependencies (fastapi, uvicorn, cryptography, httpx)
```

---

## Mock Master Data

### 1. Branches (Clinics)
- **Jakarta Central Clinic**: `11111111-1111-1111-1111-111111111111`
- **Bandung Main Clinic**: `22222222-2222-2222-2222-222222222222`
- **Surabaya Skin Care Center**: `33333333-3333-3333-3333-333333333333`
- **Bali Medical & Esthetics**: `44444444-4444-4444-4444-444444444444`
- **Yogyakarta Health & Wellness**: `55555555-5555-5555-5555-555555555555`

### 2. Doctors
- `DR-12345`: **Dr. Jane Doe, Sp.D.V.E.** (Jakarta)
- `DR-67890`: **Dr. John Smith, Sp.D.V.E.** (Jakarta & Bandung)
- `DR-11223`: **Dr. Amanda Prasetya** (Bandung & Yogyakarta)
- `DR-44556`: **Dr. Budi Santoso, Sp.B.P.R.E.** (Surabaya)
- `DR-77889`: **Dr. Citra Dewi** (Jakarta & Bali)
- `DR-99001`: **Dr. Edward Wijaya** (Surabaya & Bali)

---

## Automated Background Worker

When `mock-cis` boots up, `auto_sync_task()`:
1. Immediately pushes `bulk.sync` (all mock branches & doctors) to `BACKEND_WEBHOOK_URL` (with up to 5 retries if backend is initializing).
2. Runs a background loop pushing fresh updates every **1 hour (3600 seconds)**.

---

## Manual Trigger Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health status |
| `POST` | `/trigger/push-doctor?doctor_index=0` | Sign and push a single doctor (`doctor.upsert`) |
| `POST` | `/trigger/push-branch?branch_index=0` | Sign and push a single branch (`branch.upsert`) |
| `POST` | `/trigger/push-all` | Sign and push full bulk dataset (`bulk.sync`) |

---

## Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `BACKEND_WEBHOOK_URL` | `http://localhost:8000/api/webhooks/cis` | Target backend webhook URL (`http://backend:8000/api/webhooks/cis` in Docker) |

---

## Local Setup & Execution

### Running via Docker Compose
```bash
docker compose up --build mock-cis
```

### Standalone Run
```bash
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```
