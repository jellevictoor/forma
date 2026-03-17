import Foundation

struct ExecutionExercise: Codable, Identifiable {
    let id: String
    let phase: String
    let text: String
    var completed: Bool

    enum CodingKeys: String, CodingKey {
        case id, phase, text, completed
    }
}

struct ExecutionSession: Codable, Identifiable {
    let sessionId: String
    let athleteId: String
    let date: String
    let workoutType: String
    var exercises: [ExecutionExercise]
    let startedAt: String
    let completedAt: String?

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case athleteId = "athlete_id"
        case date
        case workoutType = "workout_type"
        case exercises
        case startedAt = "started_at"
        case completedAt = "completed_at"
    }

    var id: String { sessionId }

    var isCompleted: Bool { completedAt != nil }
}

struct PlannedDay: Codable, Identifiable {
    let day: String
    let workoutType: String
    let intensity: String
    let durationMinutes: Int
    let description: String
    let exercises: [String: [String]]?

    enum CodingKeys: String, CodingKey {
        case day
        case workoutType = "workout_type"
        case intensity
        case durationMinutes = "duration_minutes"
        case description
        case exercises
    }

    var id: String { day }
}

struct StartSessionRequest: Codable {
    let date: String
    let workoutType: String
}
