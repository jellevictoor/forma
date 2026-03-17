import SwiftUI

struct ContentView: View {
    @EnvironmentObject var settings: AppSettings
    @EnvironmentObject var workoutSession: WorkoutSessionState
    @State var selectedTab: Int = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            TodayView()
                .tabItem {
                    Label("Today", systemImage: "calendar")
                }
                .tag(0)

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .tag(1)
        }
        .environmentObject(settings)
        .environmentObject(workoutSession)
        .onAppear {
            let apiClient = APIClient(baseURL: settings.serverBaseURL)
            workoutSession.setAPIClient(apiClient)
            Task {
                await workoutSession.loadActiveSession()
            }
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(AppSettings())
        .environmentObject(WorkoutSessionState())
}
