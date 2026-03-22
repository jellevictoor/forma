# forma — feature backlog

---

## Done

- [x] **Today's workout card** on overview — "Up next" card with Not today action
- [x] **Readiness score** — Form widget (FRESH/TRAINING/BUILDING + TSB) on overview
- [x] **Streak tracking** — week-based streak on overview KPIs
- [x] **Effort score per workout** — perceived effort picker + display on dashboard
- [x] **Goal & race event display** — goal card on overview with milestone countdown
- [x] **HR zone distribution** — zone gauge + time distribution on activity detail
- [x] **Training plan web UI** — full /plan page with 7-day plan, exercises, schedule template
- [x] **Auto-generated training plan** — LLM-generated plans with exercises
- [x] **Route map visualisation** — Leaflet map on activity detail with pace/HR overlay
- [x] **Relative effort badge** — HR zone badge on activity detail
- [x] **Training alerts** — volume spike, no rest day, consecutive hard days, goal drift
- [x] **Plan adherence** — Done/Missed/Swapped badges per planned day
- [x] **Not today plan swap** — constraint-aware day swap with instant feedback
- [x] **Contextual insights** — form zone streak, 30-day fitness trend
- [x] **Fitness trajectory** — summary cards on progress page
- [x] **LiteLLM integration** — provider-agnostic LLM calls
- [x] **System prompts in DB** — editable from admin console
- [x] **Admin redesign** — 3 tabs with charts, user health, prompts editor
- [x] **Mobile responsive** — all pages work on 375px
- [x] **Smoke test suite** — 25 real-DB integration tests
- [x] **Weekly recap removed** — replaced by training alerts + contextual insights
- [x] **Rolling 12-month training log** — GitHub-style heatmap
- [x] **Plan: layman fitness labels** — "Well rested" instead of "CTL/ATL/Form"
- [x] **Plan: removed weekly cap** — not needed at this stage
- [x] **Plan: sport dot alignment** — aligned with title text
- [x] **Plan: rationale moved to top** — concise, explains "why" before the days
- [x] **Goal: fixed weekly volume chart order** — oldest on left, newest on right
- [x] **Goal: removed confusing "490 days ago"** — shows "Target date passed" instead
- [x] **Daily briefing on web** — training alerts + form widget serve this purpose
- [x] **Removed unused mood/sleep_quality fields** — dead code cleanup
- [x] **Analytics sport switch** — client-side, no full page reload

---

## Still relevant (not done yet)

### Analytics
- [x] **HR zones trend chart** — weekly Z1-Z5 stacked bar chart on progress page
- [x] **Long run detection** — domain logic + API endpoint, >=60min or >=10km
- [x] **Predicted race times** — Riegel formula from best PR, shown on progress page
- [x] **Not today: only today/tomorrow** — hidden on future days (UX fix)

### Recovery & readiness
- [x] **Daily readiness number** — 0-100 score on dashboard (60% form + 40% fitness)
- [x] **Recovery time recommendation** — shown on activity detail page (~Xh + suggestion)

### Coaching
- [x] **Schedule adjustment suggestions** — detects missed scheduled days, shows banner on plan page

### Infrastructure
- [ ] **Strava webhook** — register a webhook subscription at `https://www.strava.com/api/v3/push_subscriptions`. Strava sends POST to a callback URL on every new activity. Needs: a public endpoint (Cloudflare tunnel handles this), a `POST /api/strava/webhook` route that verifies the subscription and triggers a single-activity sync. Replaces manual sync for new activities; backfill still needed for history.

### UI fixes
- [x] Weekly volume chart — most recent week highlighted (was oldest)
- [x] Goal milestone timeline — solid circle backgrounds hide the line
- [x] Admin model selection — dropdown per service on Prompts tab

- [x] Dashboard mobile friendly — fixed in earlier commit
- [x] Bauhaus strip restored — dark (#1C1A15) replaces teal to avoid clash
- [x] Admin page — removed redundant "admin" badge above title
