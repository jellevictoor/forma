import SwiftUI

struct ExerciseRowView: View {
    let exercise: ExecutionExercise
    let isExpanded: Bool
    var onTap: () -> Void
    var onComplete: () -> Void

    @State private var expandedHeight: CGFloat = 0
    @State private var timerSeconds: Int?

    var body: some View {
        VStack(spacing: 0) {
            // Exercise header
            HStack(spacing: 12) {
                if exercise.completed {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 24))
                        .foregroundColor(.green)
                } else {
                    Circle()
                        .strokeBorder(Color.gray, lineWidth: 2)
                        .frame(width: 24, height: 24)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text(exercise.text)
                        .font(.body)
                        .lineLimit(2)
                        .fontWeight(exercise.completed ? .regular : .semibold)
                        .opacity(exercise.completed ? 0.6 : 1.0)

                    if isExpanded && !exercise.completed {
                        if let seconds = timerSeconds {
                            TimerView(initialSeconds: seconds)
                        }
                    }
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .foregroundColor(.gray)
                    .rotationEffect(.degrees(isExpanded ? 90 : 0))
            }
            .contentShape(Rectangle())
            .onTapGesture(perform: onTap)
            .padding(.horizontal)
            .padding(.vertical, 12)

            // Expanded content
            if isExpanded && !exercise.completed {
                VStack(spacing: 12) {
                    Divider()

                    Button(action: {
                        onComplete()
                        NotificationManager.shared.cancelNotification(for: exercise.id)
                    }) {
                        Text("Mark as Completed")
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.green)
                            .foregroundColor(.white)
                            .cornerRadius(8)
                    }
                    .padding(.horizontal)
                    .padding(.bottom, 12)
                }
            }
        }
        .onAppear {
            extractTimerDuration()
        }
    }

    private func extractTimerDuration() {
        let pattern = "(\\d+)\\s*(?:min|sec)"
        if let regex = try? NSRegularExpression(pattern: pattern) {
            let range = NSRange(exercise.text.startIndex..<exercise.text.endIndex, in: exercise.text)
            if let match = regex.firstMatch(in: exercise.text, range: range) {
                if let range = Range(match.range(at: 1), in: exercise.text) {
                    if let duration = Int(exercise.text[range]) {
                        let seconds = exercise.text.contains("sec") ? duration : (duration * 60)
                        timerSeconds = seconds
                    }
                }
            }
        }
    }
}

#Preview {
    ExerciseRowView(
        exercise: ExecutionExercise(id: "main-0", phase: "main", text: "3x10 goblet squat @ 24 kg", completed: false),
        isExpanded: true,
        onTap: {},
        onComplete: {}
    )
}
