# forma

Personal fitness dashboard with Strava integration and AI coaching.

![Home](screenshot-home.png)

## Features

- **Dashboard** — weekly volume, recent activities, progress overview
- **Analytics** — per-sport charts and trends
- **Plan** — AI-generated weekly training plans based on your schedule
- **Progress** — long-term tracking across running, strength, and climbing
- **Goal coaching** — AI advice tied to your active goals
- **Activity detail** — GPS maps, heart rate zones, lap breakdowns
- **iOS companion app** — guided workout execution with timers (FormaWorkout/)

## Quick start

```bash
cp .env.example .env
# Fill in your Strava and Gemini API keys

docker compose up
```

App runs at [http://localhost:8080](http://localhost:8080).

## Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (e.g. `postgresql://forma:forma@localhost:5433/forma`) |
| `STRAVA_CLIENT_ID` | Strava API client ID |
| `STRAVA_CLIENT_SECRET` | Strava API client secret |
| `STRAVA_ACCESS_TOKEN` | OAuth access token |
| `STRAVA_REFRESH_TOKEN` | OAuth refresh token |
| `GEMINI_API_KEY` | Google Gemini API key (free at aistudio.google.com) |

## Strava setup

1. Create an app at https://www.strava.com/settings/api
2. Set callback domain to `localhost`
3. Add `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` to `.env`
4. Run `uv run fitness-coach auth` to get tokens

## Development

```bash
uv sync
uv run uvicorn forma.__main__:app --reload --port 8080

uv run pytest          # run all tests
uv run ruff check      # lint
```

## Stack

- **Backend**: Python, FastAPI, PostgreSQL
- **Frontend**: Jinja2 templates, Tailwind CSS, D3.js
- **AI**: Google Gemini 2.5 Flash
- **Sync**: Strava API
- **iOS**: SwiftUI (FormaWorkout/)