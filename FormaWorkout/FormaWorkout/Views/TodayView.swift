import SwiftUI

struct TodayView: View {
    @EnvironmentObject var settings: AppSettings
    @EnvironmentObject var workoutSession: WorkoutSessionState
    @State var showExecutionView = false

    var body: some View {
        NavigationStack {
            ZStack {
                VStack(spacing: 20) {
                    if let session = workoutSession.currentSession {
                        if !session.isCompleted {
                            // Workout in progress
                            ExecutionView(session: session)
                        } else {
                            // Workout completed
                            VStack(spacing: 16) {
                                Image(systemName: "checkmark.circle.fill")
                                    .font(.system(size: 60))
                                    .foregroundColor(.green)

                                Text("Workout Completed!")
                                    .font(.title2)
                                    .fontWeight(.bold)

                                Text("Great work!")
                                    .foregroundColor(.secondary)

                                Button(action: {
                                    workoutSession.currentSession = nil
                                }) {
                                    Text("Start Another")
                                        .frame(maxWidth: .infinity)
                                        .padding()
                                        .background(Color.blue)
                                        .foregroundColor(.white)
                                        .cornerRadius(8)
                                }
                            }
                            .padding()
                        }
                    } else {
                        // No session — show today's planned workout or start new
                        VStack(spacing: 20) {
                            Text("Today's Workout")
                                .font(.title2)
                                .fontWeight(.bold)

                            VStack(alignment: .leading, spacing: 12) {
                                Text("Ready to get started?")
                                    .font(.headline)

                                Text("Let's do this!")
                                    .foregroundColor(.secondary)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding()
                            .background(Color(.systemGray6))
                            .cornerRadius(8)

                            Button(action: {
                                let today = ISO8601DateFormatter().string(from: Date()).prefix(10)
                                Task {
                                    await workoutSession.startNewSession(date: String(today), workoutType: "mixed")
                                }
                            }) {
                                Text("Start Workout")
                                    .frame(maxWidth: .infinity)
                                    .padding()
                                    .background(Color.green)
                                    .foregroundColor(.white)
                                    .cornerRadius(8)
                            }

                            Spacer()
                        }
                        .padding()
                    }
                }
                .navigationTitle("Today")

                if workoutSession.showLoadingHUD {
                    VStack {
                        ProgressView()
                            .scaleEffect(1.5)
                            .padding()
                            .background(Color(.systemGray6))
                            .cornerRadius(12)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color.black.opacity(0.2))
                }
            }
        }
    }
}

#Preview {
    TodayView()
        .environmentObject(AppSettings())
        .environmentObject(WorkoutSessionState())
}
