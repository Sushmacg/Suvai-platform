# Suvai

Mobile app for a nankhatai street stall. Customers browse the menu, order, track orders and review products they bought. The owner (admin) manages stall sessions, stock, orders, expenses, sales analytics, a demand forecast and an AI assistant.

## Stack

- Backend: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, JWT auth with rotating refresh tokens, Argon2
- ML: pandas, scikit-learn (HistGradientBoostingRegressor) vs baselines
- Assistant: LangChain + Groq, admin only, read-only tools
- Mobile: React Native (Expo SDK 58), TypeScript, React Navigation

## Backend setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # then edit .env: DATABASE_URL, SECRET_KEY, GROQ_API_KEY, ADMIN_* values
alembic upgrade head
python -m app.db.seed         # creates the admin from ADMIN_NAME / ADMIN_PHONE / ADMIN_PASSWORD
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API docs: http://127.0.0.1:8000/docs . All routes are under `/api/v1`.

Tests (need a configured `.env`):

```powershell
cd backend
python -m pytest -q
```

## Mobile setup

```powershell
cd mobile
npm install
$env:EXPO_PUBLIC_API_URL = "http://<laptop-ip>:8000/api/v1"
npx expo start
```

Open the QR code in Expo Go. Phone and laptop must be on the same Wi-Fi (or the phone hotspot).

## Roles

- Customer: sign up, menu, product detail and reviews, cart and orders, stall schedule and nearest stalls.
- Admin: dashboard, orders and status updates, stall sessions, stock, expenses, forecast, assistant. The admin account is created only by the seed script.

## Sales forecast

```powershell
cd backend
python -m scripts.generate_sales_data --days 540   # generated demo data (marked and removable, see --clear)
python -m app.ml.train
python -m app.ml.evaluate
```

The sales data used for training is generated, not real. It proves the pipeline works end to end. On the generated 540 days the model beat the best baseline by 5.43% MAE. This is not evidence about real demand.

## Notes

- No payments in this version.
- Maps: stalls open in Google Maps through a link built from coordinates. No API key is needed.
- Secrets live only in `backend/.env`, which is git-ignored.