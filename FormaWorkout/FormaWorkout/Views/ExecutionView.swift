import SwiftUI

struct ExecutionView: View {
    @EnvironmentObject var workoutSession: WorkoutSessionState
    @State var session: ExecutionSession
    @State var expandedExerciseId: String?

    var warmupExercises: [ExecutionExercise] {
        session.exercises.filter { $0.phase == "warmup" }
    }

    var mainExercises: [ExecutionExercise] {
        session.exercises.filter { $0.phase == "main" }
    }

    var cooldownExercises: [ExecutionExercise] {
        session.exercises.filter { $0.phase == "cooldown" }
    }

    var completedCount: Int {
        session.exercises.filter { $0.completed }.count
    }

    var body: some View {
        ZStack {
            VStack(spacing: 16) {
                // Progress bar
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Progress")
                            .font(.headline)
                        Spacer()
                        Text("\(completedCount)/\(session.exercises.count)")
                            .foregroundColor(.secondary)
                    }

                    ProgressView(value: Float(completedCount), total: Float(session.exercises.count))
                        .tint(.green)
                }
                .padding()
                .background(Color(.systemGray6))
                .cornerRadius(8)

                ScrollView {
                    VStack(spacing: 0) {
                        // Warmup phase
                        if !warmupExercises.isEmpty {
                            PhaseSection(
                                title: "Warmup",
                                exercises: warmupExercises,
                                expandedId: $expandedExerciseId,
                                onComplete: completeExercise
                            )
                        }

                        // Main phase
                        if !mainExercises.isEmpty {
                            PhaseSection(
                                title: "Main",
                                exercises: mainExercises,
                                expandedId: $expandedExerciseId,
                                onComplete: completeExercise
                            )
                        }

                        // Cooldown phase
                        if !cooldownExercises.isEmpty {
                            PhaseSection(
                                title: "Cooldown",
                                exercises: cooldownExercises,
                                expandedId: $expandedExerciseId,
                                onComplete: completeExercise
                            )
                        }
                    }
                }

                // Finish button
                Button(action: finishWorkout) {
                    Text("Finish Workout")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
                .padding()
            }
            .padding()
            .navigationTitle("Workout")
            .navigationBarTitleDisplayMode(.inline)

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

    private func completeExercise(_ exerciseId: String) {
        Task {
            await workoutSession.completeExercise(exerciseId: exerciseId)
            // Update local session
            if let index = session.exercises.firstIndex(where: { $0.id == exerciseId }) {
                session.exercises[index].completed = true
            }
        }
    }

    private func finishWorkout() {
        Task {
            await workoutSession.finishWorkout()
        }
    }
}

struct PhaseSection: View {
    let title: String
    let exercises: [ExecutionExercise]
    @Binding var expandedId: String?
    var onComplete: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(title)
                .font(.headline)
                .foregroundColor(.secondary)
                .padding(.horizontal)
                .padding(.vertical, 12)

            VStack(spacing: 0) {
                ForEach(exercises) { exercise in
                    ExerciseRowView(
                        exercise: exercise,
                        isExpanded: expandedId == exercise.id,
                        onTap: {
                            expandedId = expandedId == exercise.id ? nil : exercise.id
                        },
                        onComplete: {
                            onComplete(exercise.id)
                        }
                    )

                    if exercise.id != exercises.last?.id {
                        Divider()
                            .padding(.horizontal)
                    }
                }
            }

            Divider()
                .padding(.vertical, 8)
        }
    }
}

#Preview {
    let session = ExecutionSession(
        sessionId: "session1",
        athleteId: "athlete1",
        date: "2026-03-16",
        workoutType: "run",
        exercises: [
            ExecutionExercise(id: "warmup-0", phase: "warmup", text: "5 min jog", completed: false),
            ExecutionExercise(id: "main-0", phase: "main", text: "3x10 squats", completed: false),
        ],
        startedAt: "2026-03-16T09:00:00",
        completedAt: nil
    )
    ExecutionView(session: session)
        .environmentObject(AppSettings())
        .environmentObject(WorkoutSessionState())
}
