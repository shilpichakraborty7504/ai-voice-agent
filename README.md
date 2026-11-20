# AI Voice Agent for Hospital Appointments

A voice assistant that lets patients **check availability, book and cancel hospital appointments by phone**, with a staff portal and a small analytics layer on top.

Built with a [Vapi](https://vapi.ai) voice agent, a FastAPI backend, SQLite, and a Streamlit portal.

## Demo

[Watch the demo video](https://drive.google.com/file/d/10Q2kPipopsFktxIWK1p1MwKSjiOVPRyl/view?usp=sharing)

## The problem

Front-desk teams spend a large share of their day on repetitive calls: "Can I book tomorrow at 10?", "Please cancel my appointment." Patients call outside working hours and get no answer. This project explores whether a voice agent can handle these routine requests end to end, so staff can focus on patients who need a person.

More detail on users, metrics and trade-offs: [docs/PRODUCT_CASE_STUDY.md](docs/PRODUCT_CASE_STUDY.md)

## How it works

```mermaid
flowchart LR
    Caller([Patient on a call]) --> Vapi[Vapi voice agent<br/>speech-to-text, LLM, text-to-speech]
    Vapi -- "tool calls over HTTPS (ngrok tunnel)" --> API[FastAPI backend]
    API --> DB[(SQLite)]
    Staff([Front-desk staff]) --> UI[Streamlit portal]
    UI --> API
```

1. The patient speaks. Vapi turns speech into text and the LLM decides which tool to call.
2. Vapi calls the FastAPI endpoints (exposed to the internet with ngrok during development).
3. The backend validates the request, reads or writes SQLite, and returns a short message the agent can say back.
4. Staff use the Streamlit portal to schedule, cancel, view appointments and see usage insights.

The agent's prompt and tool definitions are documented in [docs/VAPI_AGENT.md](docs/VAPI_AGENT.md).

## Features

- **Check availability by voice:** returns the open 30-minute slots for a date, so the agent can offer real times instead of guessing
- **Book an appointment by voice** (name, reason, date and time)
- **Cancel an appointment** by patient name and date
- **Double-booking protection:** two active appointments cannot start less than 30 minutes apart; the API returns a clear message the agent can read out
- **Soft cancellation:** canceled appointments stay in the database so cancellation behaviour can be analysed
- **Insights:** total bookings, cancellation rate, busiest hours and top reasons for visit, via `/analytics` and the portal

## Tech stack

| Layer | Tool |
|---|---|
| Voice agent | Vapi (speech-to-text, LLM and text-to-speech configured in the Vapi dashboard) |
| API | FastAPI, Pydantic |
| Database | SQLite via SQLAlchemy |
| Staff portal | Streamlit |
| Dev tunnel | ngrok |

## API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/check_availability/` | Body `{"date": "YYYY-MM-DD"}`. Returns booked times, open slots and a sentence the agent can read out |
| POST | `/schedule_appointment/` | Book an appointment. Returns `409` if the slot is taken |
| POST | `/cancel_appointment/` | Cancel a patient's appointments on a date. Returns `404` if none found |
| GET | `/list_appointments?date=YYYY-MM-DD` | List active appointments for a day (used by the portal) |
| GET | `/analytics` | Bookings, cancellation rate, busiest hours, top reasons |

Open slots run from 09:00 to 17:00 and are set by `CLINIC_OPEN` and `CLINIC_CLOSE` in `backend/backend.py`. Interactive docs are available at `http://localhost:4444/docs` once the server is running.

## Run it locally

Developed and tested on Python 3.14 (see `.python-version`).

```bash
# 1. Create and activate a virtual environment, then install dependencies
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate         # macOS / Linux
pip install -r requirements.txt

# 2. Start the API from the repo root (port 4444)
python -m backend.backend

# 3. Start the staff portal in a second terminal
streamlit run frontend/dummy_frontend.py

# 4. To connect Vapi, expose the API in a third terminal and paste the HTTPS URL into your Vapi tools
ngrok http 4444
```

Run the example analysis queries against your local database:

```bash
python -m backend.db_demo
```

## Deployment and data persistence

Locally, the app stores data in a SQLite file, so nothing extra is needed.

Most free hosts reset their disk on every redeploy, which would wipe the appointments. To keep data, point the app at a hosted Postgres database (for example a free tier from Neon or Supabase) by setting one environment variable on your host:

```bash
DATABASE_URL=postgresql://user:password@host/dbname
```

The code is otherwise unchanged: if `DATABASE_URL` is set the app uses it, and if not it falls back to SQLite. Never commit this URL; it contains your password. Set it in your host's dashboard or in a local `.env` file (already in `.gitignore`).

## Design decisions

- **Errors are written for voice.** The agent reads API error messages aloud, so `409` and `404` responses are short, plain sentences rather than codes.
- **Tools take JSON bodies.** A GET lookup with a query parameter returned validation errors when called from the voice tool, so availability is a POST with a JSON body, matching the booking and cancel tools.
- **Soft delete over hard delete.** Keeping canceled rows makes cancellation rate and no-show style analysis possible later.
- **Fixed 30-minute slots.** The simplest rule that prevents double-booking. It does not yet support doctors, departments or different visit lengths (see roadmap).
- **SQLite for the prototype.** Zero setup. A production version would move to Postgres.

## Roadmap

- Reschedule an appointment in one call
- Enforce clinic hours when booking, and per-doctor and per-department availability
- SMS or WhatsApp confirmations and reminders
- Arabic and English support
- Call transcripts and outcome logging to measure booking completion rate
- Authentication on the API and handling of patient data (privacy and consent)

## Author

Shilpi Chakraborty
