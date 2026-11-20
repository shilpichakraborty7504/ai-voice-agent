import datetime as dt

import requests
import streamlit as st

st.title("Asrani Clinic Appointment Booking Portal")
base_url = st.text_input("Backend URL", "http://localhost:4444").rstrip("/")


def error_detail(resp: requests.Response) -> str:
    """Return the readable `detail` message from a FastAPI error response."""
    try:
        return str(resp.json().get("detail", resp.text))
    except ValueError:
        return resp.text


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------
st.subheader("Schedule")

patient_name = st.text_input("Patient name")
reason = st.text_input("Reason")
start_date = st.date_input("Date", value=dt.date.today() + dt.timedelta(days=1))
start_time = st.time_input("Time", value=dt.time(9, 0))

if st.button("Schedule"):
    start_dt = dt.datetime.combine(start_date, start_time)
    payload = {
        "patient_name": patient_name.strip(),
        "reason": reason.strip() or None,
        "start_time": start_dt.isoformat(),
    }
    try:
        resp = requests.post(f"{base_url}/schedule_appointment/", json=payload, timeout=10)
        resp.raise_for_status()
        st.success("Scheduled")
    except requests.HTTPError:
        st.error(error_detail(resp))
    except requests.RequestException as exc:
        st.error(f"Schedule failed: {exc}")

# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Cancel")

cancel_name = st.text_input("Patient name to cancel", key="cancel_name")
cancel_date = st.date_input("Date to cancel", key="cancel_date", value=dt.date.today())

if st.button("Cancel appointments"):
    payload = {
        "patient_name": cancel_name.strip(),
        "date": cancel_date.isoformat(),
    }
    try:
        resp = requests.post(f"{base_url}/cancel_appointment/", json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json() if resp.content else {}
        st.success(f"Canceled: {data.get('canceled_count', 0)}")
    except requests.HTTPError:
        st.error(error_detail(resp))
    except requests.RequestException as exc:
        st.error(f"Cancel failed: {exc}")

# ---------------------------------------------------------------------------
# Check appointments
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Check appointments")

appointments_date = st.date_input(
    "Date to check appointments", key="check_appointment_date", value=dt.date.today()
)
if st.button("Check appointments"):
    try:
        params = {"date": appointments_date.isoformat()}
        resp = requests.get(f"{base_url}/list_appointments", params=params, timeout=10)
        resp.raise_for_status()
        st.dataframe(resp.json(), use_container_width=True, hide_index=True)
    except requests.RequestException as exc:
        st.warning(f"Could not load appointments: {exc}")

# ---------------------------------------------------------------------------
# Insights (product analytics)
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Insights")

if st.button("Load insights"):
    try:
        resp = requests.get(f"{base_url}/analytics", timeout=10)
        resp.raise_for_status()
        stats = resp.json()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total bookings", stats["total_appointments"])
        col2.metric("Active", stats["active_appointments"])
        col3.metric("Canceled", stats["canceled_appointments"])
        col4.metric("Cancellation rate", f"{stats['cancellation_rate'] * 100:.1f}%")

        st.markdown("**Busiest hours (active bookings)**")
        if stats["bookings_by_hour"]:
            st.bar_chart(stats["bookings_by_hour"])
        else:
            st.caption("No bookings yet.")

        st.markdown("**Top reasons for visit**")
        if stats["top_reasons"]:
            st.dataframe(stats["top_reasons"], use_container_width=True, hide_index=True)
        else:
            st.caption("No reasons recorded yet.")
    except requests.RequestException as exc:
        st.warning(f"Could not load insights: {exc}")