import Foundation

class APIClient {
    let baseURL: String

    init(baseURL: String) {
        self.baseURL = baseURL
    }

    func getActiveSession() async throws -> ExecutionSession? {
        let url = URL(string: "\(baseURL)/api/execution/sessions/active")!
        let (data, response) = try await URLSession.shared.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        if httpResponse.statusCode == 200 && data.count > 0 {
            return try JSONDecoder().decode(ExecutionSession.self, from: data)
        }
        return nil
    }

    func startSession(date: String, workoutType: String) async throws -> ExecutionSession {
        let url = URL(string: "\(baseURL)/api/execution/sessions")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let payload = StartSessionRequest(date: date, workoutType: workoutType)
        request.httpBody = try JSONEncoder().encode(payload)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard httpResponse.statusCode == 201 else {
            throw APIError.requestFailed(statusCode: httpResponse.statusCode)
        }

        return try JSONDecoder().decode(ExecutionSession.self, from: data)
    }

    func getSession(sessionId: String) async throws -> ExecutionSession {
        let url = URL(string: "\(baseURL)/api/execution/sessions/\(sessionId)")!
        let (data, response) = try await URLSession.shared.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw APIError.requestFailed(statusCode: httpResponse.statusCode)
        }

        return try JSONDecoder().decode(ExecutionSession.self, from: data)
    }

    func completeExercise(sessionId: String, exerciseId: String) async throws -> ExecutionSession {
        let url = URL(string: "\(baseURL)/api/execution/sessions/\(sessionId)/exercises/\(exerciseId)/complete")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw APIError.requestFailed(statusCode: httpResponse.statusCode)
        }

        return try JSONDecoder().decode(ExecutionSession.self, from: data)
    }

    func finishSession(sessionId: String) async throws -> ExecutionSession {
        let url = URL(string: "\(baseURL)/api/execution/sessions/\(sessionId)/finish")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw APIError.requestFailed(statusCode: httpResponse.statusCode)
        }

        return try JSONDecoder().decode(ExecutionSession.self, from: data)
    }
}

enum APIError: LocalizedError {
    case invalidResponse
    case requestFailed(statusCode: Int)
    case decodingError

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid server response"
        case .requestFailed(let code):
            return "Request failed with status code \(code)"
        case .decodingError:
            return "Failed to decode response"
        }
    }
}
