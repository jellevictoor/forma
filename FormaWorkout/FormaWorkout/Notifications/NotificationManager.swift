import UserNotifications

class NotificationManager {
    static let shared = NotificationManager()

    private var pendingNotifications: [String] = []

    func scheduleDurationNotification(for exerciseId: String, durationSeconds: Int) {
        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: TimeInterval(durationSeconds), repeats: false)
        let content = UNMutableNotificationContent()
        content.title = "Time's up"
        content.body = "Tap to continue to the next exercise"
        content.sound = .default

        let request = UNNotificationRequest(identifier: exerciseId, content: content, trigger: trigger)
        UNUserNotificationCenter.current().add(request) { _ in }
        pendingNotifications.append(exerciseId)
    }

    func cancelNotification(for exerciseId: String) {
        UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: [exerciseId])
        pendingNotifications.removeAll { $0 == exerciseId }
    }

    func cancelAllNotifications() {
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
        pendingNotifications.removeAll()
    }
}
