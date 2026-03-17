import Foundation
import SwiftUI

class AppSettings: ObservableObject {
    @Published var serverBaseURL: String {
        didSet {
            UserDefaults.standard.set(serverBaseURL, forKey: "serverBaseURL")
        }
    }

    init() {
        self.serverBaseURL = UserDefaults.standard.string(forKey: "serverBaseURL") ?? "http://192.168.1.1:8080"
    }
}
