# FormaWorkout — iOS Guided Workout App

A SwiftUI native iOS app that provides real-time guided workout execution, with exercise tracking, timer support, and local notifications.

## Features

- **Live Workout Guidance**: See each exercise, tap to mark done, get visual feedback
- **Exercise Phases**: Workouts organized into warmup, main, and cooldown phases
- **Duration Timers**: Automatically detects timed exercises (e.g., "5 min jog") and shows countdown
- **Local Notifications**: Get a notification when a timed exercise completes
- **Progress Tracking**: Visual progress bar showing completed vs. remaining exercises
- **Home WiFi Only**: Configurable server URL for connecting to your forma backend on your home network
- **No Authentication**: Single-user, home-network focused

## Project Structure

```
FormaWorkout/
  FormaWorkout/
    App/
      FormaWorkoutApp.swift          # @main entry point
    Models/
      AppSettings.swift              # Server URL storage
      WorkoutSessionState.swift      # Observable state
    Networking/
      APIClient.swift                # URLSession wrapper
      APIModels.swift                # Codable DTOs
    Notifications/
      NotificationManager.swift      # UNUserNotificationCenter wrapper
    Views/
      ContentView.swift              # Tab router
      TodayView.swift                # Workout start/status
      ExecutionView.swift            # Active workout, phase grouping
      ExerciseRowView.swift          # Single exercise with expand/collapse
      TimerView.swift                # Countdown timer for durations
      SettingsView.swift             # Server URL configuration
    Info.plist
```

## Getting Started

### Prerequisites

- Xcode 15+ (iOS 17+)
- forma backend running on home WiFi (e.g., `http://192.168.1.100:8080`)
- iPhone or iOS simulator

### Setup

1. **Clone and open**:
   ```bash
   open FormaWorkout/FormaWorkout.xcodeproj
   ```

2. **Configure server IP**:
   - Build and run on simulator or device
   - Go to Settings tab
   - Enter your forma server IP + port (e.g., `http://192.168.1.100:8080`)
   - URL is saved to `UserDefaults`

3. **Grant notification permission**:
   - App requests notification permission on first launch
   - Required for timer completion notifications

### Running

1. Open `FormaWorkout.xcodeproj` in Xcode
2. Select target: FormaWorkout
3. Select destination: iPhone simulator or connected device
4. Press ⌘R to build and run
5. On first launch, configure server URL in Settings
6. Navigate to Today tab and tap "Start Workout"

## API Integration

The app uses these backend endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/execution/sessions` | Start a new session |
| `GET` | `/api/execution/sessions/active` | Check for active session |
| `GET` | `/api/execution/sessions/{id}` | Get session by ID |
| `POST` | `/api/execution/sessions/{id}/exercises/{ex_id}/complete` | Mark exercise done |
| `POST` | `/api/execution/sessions/{id}/finish` | Complete the session |

**Session JSON format:**
```json
{
  "session_id": "uuid",
  "athlete_id": "athlete1",
  "date": "2026-03-16",
  "workout_type": "run",
  "started_at": "2026-03-16T09:00:00+00:00",
  "completed_at": null,
  "exercises": [
    {
      "id": "warmup-0",
      "phase": "warmup",
      "text": "5 min jog",
      "completed": false
    },
    {
      "id": "main-0",
      "phase": "main",
      "text": "3x10 squats",
      "completed": false
    }
  ]
}
```

## Key Components

### APIClient
Handles all HTTP communication with the backend using `URLSession` and async/await.

**Features:**
- Base URL configurable from settings
- JSON encoding/decoding via `Codable`
- Error handling with `APIError` enum
- Simple GET/POST without auth (home WiFi only)

### WorkoutSessionState
Observable state container for the current workout session.

**Responsibilities:**
- Loads active session on app launch
- Starts new sessions
- Marks exercises complete
- Finishes sessions
- Manages loading states and errors

### NotificationManager
Schedules and cancels local notifications for timed exercises.

**Behavior:**
- Schedule: triggers after duration elapses (e.g., 5 min = 300s)
- Cancel: called when exercise manually marked done before timer expires
- Sound + alert on completion

### TimerView
Displays countdown for timed exercises using `Timer.publish`.

**Extraction:**
- Regex pattern: `(\d+)\s*(?:min|sec)` to find duration in exercise text
- Automatically starts/stops timer when view appears/disappears
- Shows "Time's up!" when countdown reaches zero

### ExecutionView
Main workout tracking interface.

**Features:**
- Organized into phases (warmup/main/cooldown sections)
- Progress bar with completion count
- Expandable exercise rows with tap-to-complete
- Inline timer for duration exercises
- Finish button to end session

## Testing

### Manual Testing Checklist

1. **No server connection**:
   - Set invalid server URL in Settings
   - Try to start a workout → error handling shows message

2. **Start workout**:
   - Tap "Start Workout" → see session ID in console
   - Exercises appear with correct phases and text

3. **Mark exercises complete**:
   - Tap an exercise to expand
   - Tap "Mark as Completed"
   - Exercise shows checkmark, progress bar updates

4. **Timed exercises**:
   - Text containing "5 min" or "30 sec" shows timer
   - Timer counts down when exercise expanded
   - "Time's up!" appears when countdown reaches zero

5. **Finish workout**:
   - Tap "Finish Workout"
   - Completion screen appears
   - Can start new workout

6. **Resume active session**:
   - Start a workout, tap home
   - Open app again → "Resume" button or continue from where left off

## Environment Variables

None required. All configuration is in the app:
- Server URL: stored in `UserDefaults` under key `serverBaseURL`
- Notification permissions: requested on first launch

## Notes

- **No Background Sync**: App does not sync data when backgrounded
- **Single Athlete**: Hardcoded to `athlete1` (backend default)
- **Local Only**: Does not store workouts locally; relies on backend persistence
- **WiFi Only**: Designed for home WiFi; may not work on cellular

## Future Enhancements

- Background task to sync exercise completions
- Workout history view
- Custom workout creation UI
- Apple Watch companion app for quick exercise completion
- HealthKit integration for auto-calorie logging
