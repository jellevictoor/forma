# Fitness Coach

Personal AI fitness coach with Strava integration.

## Setup

```bash
cp .env.example .env
# Add your API keys to .env

uv sync
uv run fitness-coach setup --seed
```

## Commands

```bash
fitness-coach setup --seed  # Load your profile and schedule
fitness-coach profile       # View your profile
fitness-coach schedule      # View weekly schedule
fitness-coach chat          # Talk with your coach
fitness-coach briefing      # Get today's briefing
fitness-coach auth          # Authenticate with Strava
fitness-coach sync          # Sync workouts from Strava
fitness-coach workouts      # View recent workouts
```

## Strava Setup

1. Create an app at https://www.strava.com/settings/api
2. Set callback domain to `localhost`
3. Add client ID and secret to `.env`
4. Run `fitness-coach auth`
