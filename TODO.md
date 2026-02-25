# forma — feature backlog

Gaps identified by comparing Strava (Summit), Runna (Premium), and Garmin Connect+.

---

## Quick wins (low effort, high value)

- [ ] **Today's workout card** on overview — schedule domain model already has the data, just needs a web UI
- [ ] **Readiness score** on overview — CTL/ATL/Form is already computed, surface it as a single number
- [ ] **Streak tracking** — compute from existing workout data, show on overview
- [ ] **Effort score per workout** — TRIMP is already computed internally, surface it in the activity table/detail
- [ ] **Goal & race event display** — athlete model already has goals, just needs a UI card

---

## Analytics gaps

- [ ] **Pace / HR zones** — zone breakdown per workout and as a trend chart (Z1–Z5)
- [ ] **HR zone distribution** — you have avg HR per workout, but no zone split
- [ ] **Elevation trend chart** — activity detail shows elevation, no weekly/monthly trend
- [ ] **Long run detection & tracking** — tag and track long runs separately (key for marathon training)
- [ ] **Predicted race times** — Runna and Garmin both offer this; can be derived from pace trend + recent efforts

---

## Recovery & readiness

- [ ] **Daily readiness score** — wrap CTL/ATL/Form into a single daily score (Garmin style)
- [ ] **Recovery time recommendation** — post-workout suggestion based on effort and form
- [ ] **Sleep quality integration** — `sleep_quality` field already exists on Workout, never used

---

## Coaching & planning

- [ ] **Training plan web UI** — domain model fully exists (Schedule, ScheduledWorkout), no web pages at all
- [ ] **Auto-generated training plan** — given goal + current fitness, generate a plan (Runna/Garmin core feature)
- [ ] **Schedule adjustment suggestions** — `suggest_schedule_adjustment()` exists on Coach port, never wired up
- [ ] **Daily briefing on web** — currently CLI only (`fitness-coach briefing`), should be a web card

---

## Activity detail enhancements

- [ ] **Route map visualisation** — Strava API returns a polyline, render it on the activity detail page
- [ ] **Relative effort badge** — show per-activity effort score (TRIMP) on the activity list and detail

---

## Other

- [ ] **Gear / shoe mileage tracking** — not modelled at all; Strava and Garmin both track equipment wear
- [ ] **Strava webhook** — receive new activity events in real time instead of manual `sync`
