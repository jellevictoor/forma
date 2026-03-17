import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var settings: AppSettings
    @State private var showAlert = false
    @State private var alertMessage = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Server Configuration") {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Server Base URL")
                            .font(.caption)
                            .foregroundColor(.secondary)

                        TextField("http://192.168.1.x:8080", text: $settings.serverBaseURL)
                            .textContentType(.URL)
                            .autocorrectionDisabled()
                            .textInputAutocapitalization(.never)
                            .font(.system(.body, design: .monospaced))

                        Text("Enter the IP address and port of your forma server on the home WiFi network.")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(.vertical, 8)
                }

                Section("About") {
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("App Version")
                            Spacer()
                            Text("1.0.0")
                                .foregroundColor(.secondary)
                        }

                        HStack {
                            Text("Built for")
                            Spacer()
                            Text("forma")
                                .foregroundColor(.secondary)
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

#Preview {
    SettingsView()
        .environmentObject(AppSettings())
}
