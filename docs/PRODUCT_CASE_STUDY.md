# Product Case Study: AI Voice Agent for Hospital Appointments

• The agent first booked appointments for the wrong year (2027), because it didn't know today's date. Adding the current date to the prompt fixed it.
• A GET lookup returned validation errors from the voice tool, so availability became a POST with a JSON body.
• The agent read out every free slot one by one, which sounded unnatural. The backend now returns free time ranges, such as "12 PM to 5 PM".
• It tried to book before the time was confirmed, so the prompt now forbids that.

## 1. Problem

Booking, canceling and checking appointments is high-volume, repetitive work for a clinic front desk. Phone calls are also the only channel that works for patients who are older, busy, or not comfortable with apps. When the desk is busy or closed, those calls go unanswered.

**Problem statement:** *Patients who call to manage an appointment often can't get through quickly, and front-desk staff lose time to routine requests that follow a predictable pattern.*

## 2. Users

| User | What they want | What goes wrong today (assumed) |
|---|---|---|
| **Patient** | Book or cancel in under a minute, any time of day | Hold times, calls after hours, no confirmation |
| **Front-desk staff** | Fewer routine calls, an accurate schedule | Interrupted by calls, manual double-booking checks |
| **Clinic manager** | Full schedule, fewer no-shows, visibility into demand | No data on when and why patients book or cancel |

## 3. Why voice?

- Works for patients who won't or can't use an app or website
- Available outside working hours
- The tasks are narrow (book, cancel, list), which suits today's voice agents

Where voice is a poor fit: noisy environments, accents and name spelling, and anything involving sensitive details. These shape the risks below.

## 4. Goals and success metrics

**North-star metric:** *booking completion rate*, the share of booking calls that end in a confirmed appointment without human help.

| Metric | Why it matters | Where it comes from |
|---|---|---|
| Booking completion rate | Does the agent actually solve the problem? | Call outcomes (roadmap: call logging) |
| Cancellation rate | Signals friction or no-show risk | `/analytics` (built) |
| Busiest hours | Staffing and capacity planning | `/analytics` (built) |
| Top reasons for visit | Which services drive demand | `/analytics` (built) |
| Double-booking incidents | Trust in the system. Target: zero | Blocked by the API, returns `409` |
| Handoff to a human rate | Where the agent fails | Roadmap |
| Average call duration | Is it faster than calling the desk? | Vapi call data |

## 4b. What I built (MVP scope)

- Check availability, book and cancel appointments by voice through a Vapi agent
- Open-slot lookup, so the agent offers real times instead of guessing
- Double-booking prevention with fixed 30-minute slots
- Soft cancellation so canceled appointments stay analysable
- Staff portal with scheduling tools and an Insights view

## 5. What I chose not to build yet, and why

I ranked the next features with a simple RICE score (Reach x Impact x Confidence / Effort). **These scores are my own estimates for illustration; with real usage data I would replace them.**

| Feature | Reach (1-10) | Impact (1-3) | Confidence | Effort (weeks) | RICE |
|---|---|---|---|---|---|
| Call logging and outcome tracking | 10 | 2 | 80% | 1 | 16.0 |
| Reschedule in one call | 6 | 2 | 80% | 1 | 9.6 |
| SMS / WhatsApp reminders | 8 | 2 | 70% | 2 | 5.6 |
| Per-doctor availability | 9 | 3 | 60% | 4 | 4.1 |
| Arabic and English support | 7 | 3 | 50% | 4 | 2.6 |

Call logging ranks first because without it I cannot measure the north-star metric, so every other decision would be a guess. The other items are limited by effort or lower confidence.

## 6. Risks and open questions

- **Privacy:** appointment reasons can be sensitive health information. A real deployment needs consent, access control and a data-retention policy.
- **Misheard names and dates:** the agent should read details back and ask for confirmation before booking or canceling.
- **Cancel by name only:** anyone who knows a patient's name and date could cancel for them. A real version needs a second identifier.
- **Language and accents:** a Dubai clinic would need Arabic and English at minimum.
- **Over-trust:** the agent should hand off to a human for anything outside book, cancel and list.

## 7. How I would validate this

1. Run 20 scripted test calls (different accents, interruptions, ambiguous dates) and record booking completion and failure reasons.
2. Show the flow to one front-desk worker and ask what they would change.
3. Compare average handling time against a normal call to the desk.

## 8. What I learned

**What surprised me**
- A tool showing "Completed successfully" in Vapi only means the request was made,
  not that my backend answered correctly. Twice the agent said the service wasn't
  responding while Vapi showed a green tick, because my tunnel was offline or the
  request was rejected. I learned to check the backend's own logs.
- The agent didn't know today's date. It booked appointments for 2027 until I
  added the current date to the prompt, and the bookings looked "missing" in my
  portal because I was checking the wrong year.
- The agent read out every free slot one by one ("10, 10 30, 12..."), which sounded
  unnatural on a call. Asking it to summarise in the prompt was less reliable than
  having the backend return ready-made ranges, so I moved that logic into the API.

**Which changes mattered most**
- Adding today's date to the system prompt.
- Telling the agent not to book until the caller has confirmed an exact time. It
  had tried to book while still asking for availability.
- Returning times in 12-hour format, since "4:30 PM" sounds better spoken than "16:30".
- Giving the voice agent an availability endpoint that returns times only, so it
  never has to read out other patients' names or reasons.

**What broke in testing**
- A GET request with the date in the address returned validation errors from the
  voice tool, so I switched it to a POST with a JSON body, like my other tools.
- A missing trailing slash on a tool URL, and an ngrok tunnel that wasn't running.

**What I would do differently**
- Log every call and its outcome from the start, so I could measure booking
  completion rate instead of judging by feel.
- Write the test-call table first and run it after every prompt change.
- Deploy the API with a stable address earlier, instead of relying on a local tunnel.
- Enforce clinic hours when booking, and require a second detail (such as a phone
  number) before canceling.
