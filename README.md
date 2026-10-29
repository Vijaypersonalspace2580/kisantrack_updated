# KisanTrak — Track • Work • Earn

An offline-first, mobile-friendly tractor work record prototype inspired by the supplied reference image. Includes a PWA-style frontend and a separate FastAPI/SQL backend starter.

## Included
- Green mobile-friendly dashboard, work history, customer list, reports and settings.
- Admin login with persistent signed-in state on the device; when cloud API is configured, admin registration/login is validated by the backend. Local cached login remains available offline after a successful cloud login.
- Customer lookup by phone, timed hourly jobs, fixed-price trolley and travelling jobs, drafts, payment entries with extra-paid tracking, allocated per-work payment/balance status, payment history, admin-confirmed deletion, CSV reports and JSON backups. Ploughing is removed from the work-type list.
- Service worker caches the frontend for repeat visits while hosted over HTTP/HTTPS.
- FastAPI API with admin authentication, SQLAlchemy models, customer/work/payment endpoints, and authenticated per-admin cloud snapshot sync (`GET/PUT /api/sync`). SQLite is for local testing; use managed PostgreSQL for persistent hosted data.
- Custom SVG app icon and install manifest.

## Quick start — frontend
For the best offline/PWA experience, serve the `frontend` folder over localhost or HTTPS (not by opening `index.html` as a `file://` URL). For example:

```bash
cd frontend
python -m http.server 5500
```

Open http://localhost:5500. On first launch choose **First-time Setup** and create the admin account. Records are saved locally first. For cloud sync, deploy the backend, set `API_BASE` near the top of `frontend/app.js` to your HTTPS backend URL, redeploy the static frontend, then register/login while online. The app merges local and cloud records by ID on sync; keep regular JSON backups.

## Run the backend API
Python 3.10+ recommended:

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Set a persistent SECRET_KEY and CORS_ORIGINS before deployment.
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs. Health endpoint: http://127.0.0.1:8000/api/health.

For PostgreSQL, set `DATABASE_URL` to a SQLAlchemy PostgreSQL URL. Configure `SECRET_KEY` as a long random secret and `CORS_ORIGINS` as the exact frontend origin(s). Deploy behind HTTPS. Do not commit secrets or database credentials to Git.

## Recent fixes from the user review
- Additional payments above the current due are accepted only after confirmation and shown as extra paid; outstanding balance never displays as a negative amount.
- Payment totals are reflected in work history, customer summaries, and reports. Deleting work recalculates work value and due/extra-paid totals while retaining payment audit entries.
- Travelling and trolley use a manually entered fixed price and hide start/end/duration fields.
- Added owner name and current date in the top bar, plus a Back button throughout app sections.

## Cloud sync setup (required for cross-device backup)
1. Deploy `backend/` as a Render **Web Service**. Build: `pip install -r requirements.txt`. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`.
2. Attach a managed PostgreSQL database and set `DATABASE_URL` to its SQLAlchemy connection URL. Set `SECRET_KEY` to a long random value that remains unchanged between deploys. Set `CORS_ORIGINS` to the exact HTTPS URL of your Render static frontend (no trailing slash).
3. In `frontend/app.js`, change `const API_BASE='';` to `const API_BASE='https://YOUR-BACKEND.onrender.com';` (no trailing slash). Commit/push and redeploy the static site.
4. Open the frontend online, choose **First-time Setup** to create the cloud admin, and then use that phone/password on other devices. Back up local-only records before enabling cloud sync.
5. Click **Admin & Settings → Sync now**. After a successful login, local changes sync when online and remain local while offline.

## Important limitations — read before real use
- Cloud sync stores a per-admin app snapshot in the configured database. Keep regular JSON backups. Use managed PostgreSQL, not Render's ephemeral local filesystem, for production data.
- Browser localStorage is not tamper-proof, is not a substitute for server-side authorization, and may be cleared by the browser/device owner. The local admin password protects the app UI, not the underlying device data against a determined user.
- A cloud database cannot guarantee that data is impossible to delete. Use least-privilege database accounts, automated backups, restricted admin permissions, audit logs, and tested restore procedures. Never store passwords as plain text.
- Payment records are marked unverified by default; an admin must confirm actual receipt. A UPI screenshot or user statement alone is not proof of settlement.
- Time billing uses elapsed hours × rate, including fractional hours. Confirm your preferred rounding rule (per minute, nearest 15 minutes, or round up) before using it for actual customer billing.
- Fingerprint authentication is not implemented in this starter. Real biometric login requires a platform authenticator/WebAuthn flow and a secure backend.

## Deploying
- Static frontend: host the contents of `frontend/` on any HTTPS static host.
- API: deploy `backend/` with build command `pip install -r requirements.txt` and start command `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- Set `SECRET_KEY`, `CORS_ORIGINS`, and a managed PostgreSQL `DATABASE_URL` in the backend environment.
- Before real production use, test frontend authentication + sync, payment verification, backup retention, and server-side audit logging.


## Latest fixes (payment/history review)
- The Record payment dialog X button closes without requiring an amount to be entered.
- Removed admin verification labels and verification badges from payment history.
- Payment inputs and price inputs accept whole rupees only; monetary displays round to whole rupees, and hourly estimates show hours/minutes rather than decimal hours.
- Work history shows the remaining balance (not a separate allocated-paid figure) and shows extra paid separately where applicable.

## Latest interface updates
- Work History now has only a Delete action per work record and shows the balance without customer extra-payment details.
- Payment History is a separate navigation section with All, Cash-only, and UPI-only filters plus search.
- Add payment is available on each customer card, directly below due amount; extra paid is shown on customer cards only.
- Work rates, default prices, and received payment amounts require whole rupees. Fractional hourly totals are rounded to the nearest rupee before saving/displaying.
- Login/setup screen has a more polished branded header and stronger visual hierarchy.


## Latest fixes (owner-approved extra credit)
- A payment is split into the portion applied to the current outstanding work and any extra credit. Extra credit is not automatically applied to work recorded later.
- Extra credit can be applied to an existing due only by selecting **Approve extra credit** on the customer card and confirming with the admin password.
- Every recorded payment remains visible in the separate Payment History section, including its payment mode, amount, applied portion, and unapplied extra credit. Owner-approved extra credit is labelled in the history.
- The dashboard greeting uses the registered admin name and changes between Good morning, Good afternoon, and Good evening according to the device's local time.
- The service-worker cache version was bumped so installed copies can fetch the updated frontend assets.
