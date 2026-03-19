# Quick Start — iOS Guided Workout Execution

## 60-Second Setup

### Backend
```bash
cd /Users/jelle/projects/forma
uv run serve
# Server starts on http://0.0.0.0:8080
```

### iOS App
```bash
cd FormaWorkout
open FormaWorkout.xcodeproj
# In Xcode: ⌘R to build and run
```

### Configure & Test
1. **Settings tab** → Enter server URL: `http://localhost:8080` (simulator) or `http://192.168.1.X:8080` (device/WiFi)
2. **Grant notification permission** when prompted
3. **Today tab** → "Start Workout"
4. **Tap exercises** to expand, then "Mark as Completed"
5. **Finish Workout** to end session

---

## What Works

✅ **Start a workout** — Exercises load from backend
✅ **Mark exercises done** — Real-time updates
✅ **Timed exercises** — Countdown timer with notifications
✅ **Resume sessions** — Reopen app, pick up where you left off
✅ **Error handling** — Network errors show user-friendly messages
✅ **Notifications** — Local alerts when timers expire

---

## Architecture

```
iOS App (SwiftUI)
    ↓ HTTP (async/await)
Backend API (FastAPI)
    ↓ Services
Domain Models + PostgreSQL
```

---

## Files to Know

### Backend (7 new files)
- `domain/execution_session.py` — Data model
- `ports/execution_session_repository.py` — Storage interface
- `adapters/postgres_execution_session.py` — Database
- `application/workout_execution_service.py` — Business logic
- `adapters/web/routes/execution.py` — API endpoints
- `adapters/web/app.py` — CORS + routing (modified)
- `adapters/web/dependencies.py` — Dependency injection (modified)

### iOS (12 Swift files + Info.plist)
- **App**: `FormaWorkoutApp.swift`
- **Models**: `AppSettings`, `WorkoutSessionState`
- **Networking**: `APIClient`, `APIModels`
- **Notifications**: `NotificationManager`
- **Views**: `ContentView`, `TodayView`, `ExecutionView`, `ExerciseRowView`, `TimerView`, `SettingsView`

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/execution/sessions` | Start new session |
| `GET` | `/api/execution/sessions/active` | Resume in-progress |
| `GET` | `/api/execution/sessions/{id}` | Get session |
| `POST` | `/api/execution/sessions/{id}/exercises/{ex_id}/complete` | Mark done |
| `POST` | `/api/execution/sessions/{id}/finish` | End session |

---

## Testing

```bash
# Backend tests (197 tests, all passing)
uv run pytest -q

# Code quality
uv run ruff check

# Watch server logs
uv run serve
```

---

## Troubleshooting

**"Invalid server response"**
- Check URL in Settings (include http:// and :port)
- Verify backend is running
- Try `curl http://localhost:8080/api/execution/sessions/active`

**"No exercises loading"**
- Backend needs plan cache for today
- Ensure `WorkoutPlanningService` has generated a plan

**"Timer not appearing"**
- Exercise text must contain duration: "5 min jog" or "30 sec rest"
- Regex pattern: `(\d+)\s*(?:min|sec)`

**"Notification never fires"**
- Check Settings > Apps > FormaWorkout > Notifications enabled
- Simulator may not show banner if app is open

---

## Documentation

- **Full setup guide**: `iOS_SETUP.md`
- **iOS app details**: `FormaWorkout/README.md`
- **Implementation notes**: `IMPLEMENTATION_SUMMARY.md`
- **Backend principles**: `CLAUDE.md`

---

## Next Steps

1. ✅ Backend running with all 197 tests passing
2. ✅ iOS app compiles and runs
3. ✅ Can start a workout and mark exercises complete
4. 🔄 Test on physical device on home WiFi
5. 💡 Consider enhancements: offline mode, workout history, Apple Watch

---

**Questions?** Check the full documentation files listed above.
