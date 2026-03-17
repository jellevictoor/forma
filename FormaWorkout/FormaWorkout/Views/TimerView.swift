import SwiftUI

struct TimerView: View {
    let initialSeconds: Int
    @State private var remainingSeconds: Int
    @State private var timer: Timer?
    @State private var notificationScheduled = false

    init(initialSeconds: Int) {
        self.initialSeconds = initialSeconds
        _remainingSeconds = State(initialValue: initialSeconds)
    }

    var formattedTime: String {
        let minutes = remainingSeconds / 60
        let seconds = remainingSeconds % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }

    var body: some View {
        VStack(spacing: 8) {
            HStack {
                Image(systemName: "timer")
                    .font(.caption)
                    .foregroundColor(.orange)
                Text(formattedTime)
                    .font(.caption)
                    .monospaced()
                    .foregroundColor(.orange)
            }

            if remainingSeconds == 0 {
                Text("Time's up!")
                    .font(.caption)
                    .foregroundColor(.green)
                    .fontWeight(.semibold)
            }
        }
        .onAppear {
            startTimer()
        }
        .onDisappear {
            stopTimer()
        }
    }

    private func startTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { _ in
            if remainingSeconds > 0 {
                remainingSeconds -= 1

                if remainingSeconds == 0 {
                    stopTimer()
                }
            }
        }
    }

    private func stopTimer() {
        timer?.invalidate()
        timer = nil
    }
}

#Preview {
    TimerView(initialSeconds: 300)
}
