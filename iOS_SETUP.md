# iOS Guided Workout Execution — Complete Setup

This document explains how to set up and run the complete forma guided workout system: backend + iOS app.

## Architecture Overview

```
┌─────────────────────────────────────────┐
│  FormaWorkout iOS App (SwiftUI)         │
│  - TodayView: Start/status              │
│  - ExecutionView: Exercise tracking     │
│  - ExerciseRowView: Individual exercise │
│  - TimerView: Duration countdown        │
│  - SettingsView: Server URL config      │
└────────────┬────────────────────────────┘
             │
     HTTP via URLSession
     (CORS enabled, no auth)
             │
┌────────────▼────────────────────────────┐
│  Python Backend (FastAPI)                │
│  Port: 8080                              │
├──────────────────────────────────────────┤
│ Routes:                                  │
│  POST   /api/execution/sessions          │
│  GET    /api/execution/sessions/active   │
│  GET    /api/execution/sessions/{id}     │
│  POST   .../exercises/{ex_id}/complete   │
│  POST   .../finish                       │
│                                          │
│ Domain: ExecutionSession, Exercises      │
│ Adapters: SQLite + APIClient             │
│ Service: WorkoutExecutionService         │
└──────────────────────────────────────────┘
```

---

## Part 1: Backend Setup

### Prerequisites

- Python 3.13+
- `uv` package manager
- Docker (optional, for docker-compose)

### Install & Run Backend

```bash
# Navigate to project root
cd /Users/jelle/projects/forma

# Install dependencies
uv sync

# Run tests (should see 197 tests pass)
uv run pytest -q

# Run ruff check (should pass)
uv run ruff check

# Start backend server
uv run serve
# Server will start on http://0.0.0.0:8080
```

**Or with Docker:**

```bash
docker compose up
# Backend available at http://localhost:8080
```

### Verify Backend

Open a terminal and test:

```bash
# Get active session (should return empty initially)
curl http://localhost:8080/api/execution/sessions/active

# Start a session
curl -X POST http://localhost:8080/api/execution/sessions \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-03-16","workout_type":"run"}'

# Response will include session_id, exercises, etc.
```

---

## Part 2: iOS App Setup

### Prerequisites

- **Xcode 15+** (or compatible)
- **iOS 17+** target
- iPhone simulator or physical device on same WiFi

### Open & Configure Xcode Project

```bash
# Navigate to iOS project
cd /Users/jelle/projects/forma/FormaWorkout

# Open in Xcode
open FormaWorkout.xcodeproj
```

**Xcode Configuration:**

1. Select scheme **FormaWorkout**
2. Select destination:
   - **iPhone Simulator** (any recent model) — for desktop testing
   - **Connected iPhone** — for physical device testing
3. Build and run: ⌘R

### First Launch: Configure Server

On first run:

1. **TodayView** appears (empty, no active session)
2. Tap the **Settings tab** (gear icon)
3. Enter your server's IP + port:
   - If running backend locally: `http://localhost:8080`
   - If running on home WiFi: `http://192.168.1.XX:8080` (your server IP)
4. URL saves automatically to `UserDefaults`
5. Return to **Today tab**

### Grant Notification Permission

- App requests UNUserNotificationCenter permission on launch
- Tap **Allow** to enable timer notifications

---

## Testing the End-to-End Flow

### Scenario 1: Start a Workout

1. **Backend running** on `http://192.168.1.XX:8080` or `localhost:8080`
2. **iOS app configured** with correct server URL in Settings
3. Navigate to **Today** tab
4. Tap **"Start Workout"** button
   - App calls `POST /api/execution/sessions` with today's date + type
   - Session loads with exercises (warmup, main, cooldown)
5. Exercises appear in **ExecutionView**, grouped by phase

### Scenario 2: Complete an Exercise

1. In **ExecutionView**, tap an exercise to expand
2. See exercise text + any duration timer (if text mentions "5 min" etc.)
3. Tap **"Mark as Completed"**
   - App calls `POST .../exercises/{exercise_id}/complete`
   - Exercise shows green checkmark
   - Progress bar updates
4. Repeat for all exercises

### Scenario 3: Finish Workout

1. After completing exercises, tap **"Finish Workout"** button
2. App calls `POST .../finish`
3. **Completion screen** appears with "Workout Completed!" message
4. Tap **"Start Another"** to begin a new session

### Scenario 4: Resume Active Session

1. Start a workout on device
2. Close app (or go home)
3. Reopen app
4. App calls `GET /api/execution/sessions/active` on launch
5. **ExecutionView** resumes with same session + exercise state

---

## Architecture Decisions

### Why CORS for All Origins?

- **Single-user**, home WiFi only
- iOS app may run from simulator IP or device IP
- Safer to allow all origins than try to restrict

### Why No Authentication?

- Home WiFi network is trusted
- Private network, not exposed to internet
- Single user (athlete1)

### Why JSON Blob Storage for Sessions?

- Zero migrations when exercise fields change
- Session is ephemeral (not long-term analytics)
- SQLite adapter handles serialization

### Why Local Notifications vs Push?

- No server-side notification infrastructure needed
- Timer fires on device, independent of network
- User experience is immediate (no server round-trip)

---

## Troubleshooting

### Backend Not Responding

```bash
# Check if server is running
curl http://localhost:8080/api/execution/sessions/active

# If fails, restart
uv run serve
```

### "Invalid server response" Error in App

1. Check server URL in Settings (include protocol + port)
2. Verify backend is running
3. Verify iOS device / simulator can reach that IP
   - From simulator: `localhost:8080` usually works
   - From physical device on WiFi: use actual device IP, e.g. `192.168.1.50:8080`

### No Exercises Loaded

- Backend may not have a plan cached for today
- Check backend logs: `uv run serve` will show request logs
- Verify `WorkoutPlanningService.get_exercises_for_day()` is returning data

### Timer Not Working

- Timer extraction looks for regex pattern: `(\d+)\s*(?:min|sec)`
- Exercise text must contain duration, e.g., "5 min jog" or "30 sec rest"
- If text is "Jog 5 minutes", regex won't match — needs "5 min" format

### Notification Never Fires

1. Check notification permission granted (Settings > Apps > FormaWorkout)
2. Ensure device/simulator has sound enabled
3. Check Console in Xcode for `NotificationManager` logs

---

## Files Modified/Created for iOS Support

### Backend

- `src/fitness_coach/adapters/web/app.py` — Added CORS middleware
- `src/fitness_coach/adapters/web/routes/execution.py` — New routes
- `src/fitness_coach/domain/execution_session.py` — New domain model
- `src/fitness_coach/ports/execution_session_repository.py` — New port
- `src/fitness_coach/adapters/sqlite_execution_session.py` — SQLite adapter
- `src/fitness_coach/application/workout_execution_service.py` — Service
- `src/fitness_coach/adapters/web/dependencies.py` — DI wiring

### iOS App

- `FormaWorkout/FormaWorkout/` — New Xcode project
  - `App/FormaWorkoutApp.swift` — Entry point
  - `Models/` — AppSettings, WorkoutSessionState
  - `Networking/` — APIClient, APIModels
  - `Notifications/` — NotificationManager
  - `Views/` — UI components

---

## Verification Checklist

- [ ] Backend tests pass: `uv run pytest -q` (197 tests)
- [ ] Backend linting passes: `uv run ruff check`
- [ ] Backend server runs: `uv run serve` (or `docker compose up`)
- [ ] iOS app opens in Xcode without build errors
- [ ] iOS app starts simulator/device: ⌘R
- [ ] Notification permission requested on first launch
- [ ] Settings tab lets you enter server URL
- [ ] Today tab shows "Start Workout" button
- [ ] Can start a session (exercises load)
- [ ] Can mark exercises complete
- [ ] Can finish a workout
- [ ] Can resume an active session on re-launch

---

## Next Steps

If everything works, you have:

✅ **Backend**: Workout execution API with persistence
✅ **iOS**: Native SwiftUI app with real-time exercise guidance
✅ **Integration**: Full end-to-end home WiFi workout tracking

Consider future enhancements:
- Sync completed workouts back to analytics
- Offline mode with background sync
- Apple Watch companion app
- Custom rest periods between exercises
