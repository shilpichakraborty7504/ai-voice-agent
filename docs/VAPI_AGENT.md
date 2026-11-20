# Vapi Agent Configuration

This page documents how the voice agent is set up, so the prompt and tools live in the repo and not only in the Vapi dashboard.

> **Check this against your dashboard.** Edit anything below that differs from what you actually configured, and add your real provider and model choices.

## Agent settings

| Setting | Value |
|---|---|
| Speech-to-text | Deepgram Nova 3 (General, English) |
| LLM | OpenAI GPT-6 Luna |
| Voice | Vapi "Sagar" (v2) |
| First message | "Hi. My name is Akash from Asrani Clinic. How can I help you today?" |

## System prompt

```text
You are a friendly, concise phone assistant for Dubai Hospital's appointment desk.
You can do three things: check available times, book an appointment, and cancel an
appointment. If the caller asks for anything else, politely say you cannot help
with that and offer to connect them with the front desk.

Rules:
- Ask for one piece of information at a time.
- Today's date and time is {{now}}. Use it to turn words like "tomorrow" or
  "next Monday" into a real date. Always send dates to tools as YYYY-MM-DD.
- To check availability, call the availability tool with the date, then read out
  two or three open times. Do not read the whole list.
- To book, collect: the patient's full name, the reason for the visit, the date,
  and the time. Appointments last 30 minutes.
- Before booking or canceling, read the details back and ask the caller to confirm.
- To cancel, collect the patient's full name and the appointment date, then confirm.
- If a tool returns an error, explain it in one short, friendly sentence and offer
  a next step (for example, suggest another time if the slot is taken).
- Never invent availability or confirm a booking before the tool succeeds.
- Do not discuss medical advice. Keep every reply to one or two short sentences.
```

`{{now}}` is a Vapi dynamic variable for the current date and time. Without it the agent can guess the wrong date or year, and bookings end up on the wrong day.

## Tools

All tools call the FastAPI backend through the ngrok HTTPS URL, and all are `POST` requests with a JSON body. Keep the trailing slash on every URL, because without it FastAPI redirects the request.

### `check_doctor_availability`

- **Method and URL:** `POST {NGROK_URL}/check_availability/`
- **When to use:** when the caller asks what times are free on a date
- **Body:**

```json
{
  "date": "YYYY-MM-DD"
}
```

- **Returns:** `booked_times`, `available_slots` and a `message` sentence the agent can read out
- **Possible errors:** `422` (date missing or not in YYYY-MM-DD format; describe the format in the parameter description)

### `schedule_appointment`

- **Method and URL:** `POST {NGROK_URL}/schedule_appointment/`
- **When to use:** after the caller confirms name, reason, date and time
- **Body:**

```json
{
  "patient_name": "string",
  "reason": "string or null",
  "start_time": "ISO 8601 date-time, for example 2026-11-20T10:00:00"
}
```

- **Possible errors:** `409` (slot is taken; the message tells the agent which time clashes), `422` (missing or badly formatted field)

### `cancel_appointment`

- **Method and URL:** `POST {NGROK_URL}/cancel_appointment/`
- **When to use:** after the caller confirms name and date
- **Body:**

```json
{
  "patient_name": "string",
  "date": "YYYY-MM-DD"
}
```

- **Possible errors:** `404` (no matching appointment)

