import Foundation

class WorkoutSessionState: ObservableObject {
    @Published var currentSession: ExecutionSession?
    @Published var isLoading = false
    @Published var error: String?
    @Published var showLoadingHUD = false

    private var apiClient: APIClient?

    func setAPIClient(_ client: APIClient) {
        self.apiClient = client
    }

    @MainActor
    func loadActiveSession() async {
        guard let client = apiClient else { return }
        isLoading = true
        defer { isLoading = false }

        do {
            currentSession = try await client.getActiveSession()
        } catch {
            self.error = error.localizedDescription
        }
    }

    @MainActor
    func startNewSession(date: String, workoutType: String) async {
        guard let client = apiClient else { return }
        showLoadingHUD = true
        defer { showLoadingHUD = false }

        do {
            currentSession = try await client.startSession(date: date, workoutType: workoutType)
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    @MainActor
    func completeExercise(exerciseId: String) async {
        guard let client = apiClient, let session = currentSession else { return }

        do {
            currentSession = try await client.completeExercise(sessionId: session.sessionId, exerciseId: exerciseId)
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    @MainActor
    func finishWorkout() async {
        guard let client = apiClient, let session = currentSession else { return }
        showLoadingHUD = true
        defer { showLoadingHUD = false }

        do {
            currentSession = try await client.finishSession(sessionId: session.sessionId)
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }
}
