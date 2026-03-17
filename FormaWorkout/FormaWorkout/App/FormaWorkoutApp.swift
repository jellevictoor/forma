import SwiftUI

@main
struct FormaWorkoutApp: App {
    @StateObject var settings = AppSettings()
    @StateObject var workoutSession = WorkoutSessionState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(settings)
                .environmentObject(workoutSession)
                .onAppear {
                    requestNotificationPermissions()
                }
        }
    }

    private func requestNotificationPermissions() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }
    }
}
