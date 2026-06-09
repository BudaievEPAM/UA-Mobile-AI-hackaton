import Foundation

/// Persists sessions to ~/Library/Application Support/MigratorGUI/sessions.json
/// so the "recent requests" list survives restarts.
struct Store: Sendable {
    let url: URL

    init() {
        let base = FileManager.default
            .urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
            .appendingPathComponent("MigratorGUI", isDirectory: true)
        try? FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        url = base.appendingPathComponent("sessions.json")
    }

    func load() -> [ChatSession] {
        guard let data = try? Data(contentsOf: url),
              let sessions = try? JSONDecoder().decode([ChatSession].self, from: data) else {
            return []
        }
        return sessions
    }

    func save(_ sessions: [ChatSession]) {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        guard let data = try? encoder.encode(sessions) else { return }
        try? data.write(to: url, options: .atomic)
    }
}
