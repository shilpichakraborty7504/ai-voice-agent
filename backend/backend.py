"""FastAPI backend for the AI voice appointment agent.

The Vapi voice agent calls these endpoints as tools, so every error message
returned here is written to be read aloud to a caller.
"""

import datetime as dt
from collections import Counter

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import Appointment, get_db, init_db

init_db()

# Every appointment blocks a fixed-length slot. Two active appointments
# cannot start less than this many minutes apart.
SLOT_MINUTES = 30

# Hours the clinic offers appointments (used when listing open slots).
CLINIC_OPEN = dt.time(9, 0)
CLINIC_CLOSE = dt.time(17, 0)

#pydantic contracts

class AppointmentRequest(BaseModel):
    patient_name: str = Field(min_length=1)
    reason: str | None = None
    start_time: dt.datetime


class AppointmentResponse(BaseModel):
    id: int
    patient_name: str
    reason: str | None
    start_time: dt.datetime
    canceled: bool
    created_at: dt.datetime


class CancelAppointmentRequest(BaseModel):
    patient_name: str = Field(min_length=1)
    date: dt.date


class CancelAppointmentResponse(BaseModel):
    canceled_count: int


class AvailabilityRequest(BaseModel):
    date: dt.date


class AvailabilityResponse(BaseModel):
    date: dt.date
    booked_times: list[str]  # e.g. ["09:00", "10:30"]
    available_slots: list[str]  # open start times, e.g. ["09:30", "11:00"]
    available_ranges: list[str]  # free windows, e.g. ["9:30 AM to 11:00 AM"]
    message: str  # a sentence the voice agent can read out


class ReasonCount(BaseModel):
    reason: str
    count: int


class AnalyticsResponse(BaseModel):
    total_appointments: int
    active_appointments: int
    canceled_appointments: int
    cancellation_rate: float  # 0.0 to 1.0
    bookings_by_hour: dict[str, int]  # e.g. {"09:00": 4}
    top_reasons: list[ReasonCount]


def to_response(appointment: Appointment) -> AppointmentResponse:
    return AppointmentResponse(
        id=appointment.id,
        patient_name=appointment.patient_name,
        reason=appointment.reason,
        start_time=appointment.start_time,
        canceled=appointment.canceled,
        created_at=appointment.created_at,
    )


def day_bounds(day: dt.date) -> tuple[dt.datetime, dt.datetime]:
    start = dt.datetime.combine(day, dt.time.min)
    return start, start + dt.timedelta(days=1)


def compute_available_slots(day: dt.date, booked_starts: list[dt.datetime]) -> list[str]:
    """Open start times (HH:MM) between opening and closing time.

    A start time is open when every active appointment begins at least
    SLOT_MINUTES away from it, the same rule schedule_appointment enforces.
    """
    slot = dt.timedelta(minutes=SLOT_MINUTES)
    current = dt.datetime.combine(day, CLINIC_OPEN)
    close = dt.datetime.combine(day, CLINIC_CLOSE)

    free: list[str] = []
    while current + slot <= close:
        if all(abs(current - booked) >= slot for booked in booked_starts):
            free.append(current.strftime("%H:%M"))
        current += slot
    return free


def format_clock(t: dt.time) -> str:
    """12-hour clock text that sounds natural when spoken, e.g. '4:30 PM'."""
    return f"{t.hour % 12 or 12}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"


def compute_available_ranges(day: dt.date, free_slots: list[str]) -> list[str]:
    """Merge back-to-back open slots into free windows, e.g. '12:00 PM to 5:00 PM'.

    A window runs from the start of its first slot to the end of its last slot,
    so an appointment always fits inside it.
    """
    slot = dt.timedelta(minutes=SLOT_MINUTES)
    windows: list[list[dt.datetime]] = []

    for text in free_slots:
        start = dt.datetime.combine(day, dt.time.fromisoformat(text))
        if windows and start == windows[-1][1]:
            windows[-1][1] = start + slot  # extends the current window
        else:
            windows.append([start, start + slot])

    return [
        f"{format_clock(first.time())} to {format_clock(last.time())}"
        for first, last in windows
    ]


#API

app = FastAPI(title="AI Voice Agent - Appointment API")


@app.post("/schedule_appointment/", response_model=AppointmentResponse)
def schedule_appointment(request: AppointmentRequest, db: Session = Depends(get_db)):
    slot = dt.timedelta(minutes=SLOT_MINUTES)

    # Reject the booking if another active appointment is too close in time.
    clash = db.execute(
        select(Appointment)
        .where(Appointment.canceled.is_(False))
        .where(Appointment.start_time > request.start_time - slot)
        .where(Appointment.start_time < request.start_time + slot)
    ).scalars().first()

    if clash:
        raise HTTPException(
            status_code=409,
            detail=(
                f"That time is already taken (there is an appointment at "
                f"{clash.start_time:%H:%M}). Please choose a time at least "
                f"{SLOT_MINUTES} minutes away from it."
            ),
        )

    new_appointment = Appointment(
        patient_name=request.patient_name.strip(),
        reason=request.reason,
        start_time=request.start_time,
    )
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)
    return to_response(new_appointment)


@app.post("/cancel_appointment/", response_model=CancelAppointmentResponse)
def cancel_appointment(request: CancelAppointmentRequest, db: Session = Depends(get_db)):
    start_dt, end_dt = day_bounds(request.date)

    appointments = db.execute(
        select(Appointment)
        .where(Appointment.patient_name == request.patient_name.strip())
        .where(Appointment.start_time >= start_dt)
        .where(Appointment.start_time < end_dt)
        .where(Appointment.canceled.is_(False))
    ).scalars().all()

    if not appointments:
        raise HTTPException(
            status_code=404,
            detail="No appointment found for the given patient and date",
        )

    # Soft delete: keep the row so cancellations can be analysed later.
    for appointment in appointments:
        appointment.canceled = True

    db.commit()
    return CancelAppointmentResponse(canceled_count=len(appointments))


# `date` is a plain query parameter (GET /list_appointments?date=2026-11-20).
# A Pydantic model here would be read as a request body, which GET requests
# from the Streamlit app and from Vapi do not send.
@app.get("/list_appointments", response_model=list[AppointmentResponse])
def list_appointments(date: dt.date, db: Session = Depends(get_db)):
    start_dt, end_dt = day_bounds(date)

    appointments = db.execute(
        select(Appointment)
        .where(Appointment.canceled.is_(False))
        .where(Appointment.start_time >= start_dt)
        .where(Appointment.start_time < end_dt)
        .order_by(Appointment.start_time.asc())
    ).scalars().all()

    return [to_response(a) for a in appointments]


# POST with a JSON body, like the booking and cancel tools, because voice-agent
# tools send bodies reliably. `date` must be written YYYY-MM-DD.
@app.post("/check_availability/", response_model=AvailabilityResponse)
def check_availability(request: AvailabilityRequest, db: Session = Depends(get_db)):
    start_dt, end_dt = day_bounds(request.date)

    booked = db.execute(
        select(Appointment.start_time)
        .where(Appointment.canceled.is_(False))
        .where(Appointment.start_time >= start_dt)
        .where(Appointment.start_time < end_dt)
        .order_by(Appointment.start_time.asc())
    ).scalars().all()

    free = compute_available_slots(request.date, booked)
    ranges = compute_available_ranges(request.date, free)
    day_label = f"{request.date:%A %d %B %Y}"

    if ranges:
        message = f"Free times on {day_label}: " + ", ".join(ranges) + "."
    else:
        message = f"There are no open times on {day_label}."

    return AvailabilityResponse(
        date=request.date,
        booked_times=[b.strftime("%H:%M") for b in booked],
        available_slots=free,
        available_ranges=ranges,
        message=message,
    )


@app.get("/analytics", response_model=AnalyticsResponse)
def analytics(db: Session = Depends(get_db)):
    """Product metrics for the voice agent: volume, cancellations, peak hours."""
    appointments = db.execute(select(Appointment)).scalars().all()

    total = len(appointments)
    canceled = sum(1 for a in appointments if a.canceled)
    active = [a for a in appointments if not a.canceled]

    by_hour = Counter(a.start_time.strftime("%H:00") for a in active)
    reasons = Counter(
        a.reason.strip().lower() for a in appointments if a.reason and a.reason.strip()
    )

    return AnalyticsResponse(
        total_appointments=total,
        active_appointments=len(active),
        canceled_appointments=canceled,
        cancellation_rate=round(canceled / total, 3) if total else 0.0,
        bookings_by_hour=dict(sorted(by_hour.items())),
        top_reasons=[ReasonCount(reason=r, count=c) for r, c in reasons.most_common(5)],
    )


if __name__ == "__main__":
    # Run from the repo root:  python -m backend.backend
    uvicorn.run("backend.backend:app", host="0.0.0.0", port=4444, reload=True)