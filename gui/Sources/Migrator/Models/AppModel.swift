import Foundation
import Observation
import AppKit

@MainActor
@Observable
final class AppModel {
    /// Model choices offered for commands that accept one. "default" means the
    /// account default (no --model passed).
    static let models = ["default", "sonnet", "opus", "haiku"]

    var sessions: [ChatSession] = []
    var selectedSessionID: ChatSession.ID?
    var selectedCommandID: String = AppCommand.registry[0].id
    var selectedModel: String = "default"
    var input: String = ""
    var isRunning = false
    var projectRoot: URL {
        didSet { UserDefaults.standard.set(projectRoot.path, forKey: Self.rootKey) }
    }

    private let store = Store()
    private var runner: ProcessRunner?

    init() {
        projectRoot = AppModel.resolveRoot()
        sessions = store.load()
        selectedSessionID = sessions.first?.id
    }

    // MARK: - Derived

    var selectedCommand: AppCommand { AppCommand.command(id: selectedCommandID) }

    var selectedSession: ChatSession? {
        guard let id = selectedSessionID else { return nil }
        return sessions.first { $0.id == id }
    }

    var rootIsValid: Bool {
        FileManager.default.fileExists(
            atPath: projectRoot.appendingPathComponent("scripts/single_claude_agent_migrate.sh").path
        )
    }

    // MARK: - Session management

    func newSession() {
        let session = ChatSession(title: "New request", commandID: selectedCommandID)
        sessions.insert(session, at: 0)
        selectedSessionID = session.id
        input = ""
        persist()
    }

    func deleteSession(_ id: ChatSession.ID) {
        sessions.removeAll { $0.id == id }
        if selectedSessionID == id { selectedSessionID = sessions.first?.id }
        persist()
    }

    func chooseProjectRoot() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        panel.directoryURL = projectRoot
        panel.prompt = "Use Folder"
        panel.message = "Pick the migration project root (the folder that contains scripts/)."
        if panel.runModal() == .OK, let url = panel.url {
            projectRoot = url
        }
    }

    // MARK: - Sending

    func send() {
        let raw = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty, !isRunning else { return }

        let (command, argument) = AppCommand.resolve(raw, fallback: selectedCommand)
        selectedCommandID = command.id

        if selectedSession == nil { newSession() }
        guard let id = selectedSessionID else { return }

        // Give a fresh session a meaningful title from its first request.
        if let index = sessions.firstIndex(where: { $0.id == id }),
           sessions[index].messages.isEmpty {
            sessions[index].title = title(for: command, argument: argument)
            sessions[index].commandID = command.id
        }

        append(ChatMessage(role: .user, text: raw), to: id)
        input = ""
        run(command: command, argument: argument, sessionID: id)
    }

    func stop() {
        runner?.terminate()
    }

    // MARK: - Run loop

    private func run(command: AppCommand, argument: String, sessionID: ChatSession.ID) {
        var environment = ProcessRunner.baseEnvironment()
        var spec = command.build(argument, projectRoot)
        if command.acceptsModel, selectedModel != "default" {
            spec.environment["CLAUDE_MODEL"] = selectedModel
        }
        for (key, value) in spec.environment { environment[key] = value }

        append(ChatMessage(role: .command, text: "$ " + display(spec)), to: sessionID)

        let runner = ProcessRunner(
            executable: spec.executable,
            arguments: spec.arguments,
            cwd: projectRoot,
            environment: environment
        )
        self.runner = runner
        isRunning = true

        Task {
            for await event in runner.events() {
                switch event {
                case let .line(line, stderr):
                    for item in StreamJSON.parse(line, preferJSON: command.streamsJSON) {
                        let role: MessageRole = (stderr && item.role == .output) ? .error : item.role
                        append(ChatMessage(role: role, text: item.text), to: sessionID)
                    }
                case let .exit(code):
                    if code == 0 {
                        append(ChatMessage(role: .system, text: "✓ finished (exit 0)"), to: sessionID)
                    } else {
                        append(ChatMessage(role: .error, text: "✗ exited with code \(code)"), to: sessionID)
                    }
                }
            }
            isRunning = false
            self.runner = nil
            persist()
        }
    }

    // MARK: - Helpers

    private func append(_ message: ChatMessage, to id: ChatSession.ID) {
        guard let index = sessions.firstIndex(where: { $0.id == id }) else { return }
        sessions[index].messages.append(message)
        sessions[index].updatedAt = .now
    }

    private func title(for command: AppCommand, argument: String) -> String {
        let trimmed = argument.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty { return command.title }
        return String(trimmed.prefix(80))
    }

    private func display(_ spec: CommandSpec) -> String {
        let name = spec.executable.lastPathComponent
        let prefix = spec.environment
            .sorted { $0.key < $1.key }
            .map { "\($0.key)=\($0.value)" }
        let parts = prefix + [name] + spec.arguments.map(Self.shellQuote)
        return parts.joined(separator: " ")
    }

    private static func shellQuote(_ value: String) -> String {
        if value.isEmpty { return "''" }
        let safe = CharacterSet(charactersIn:
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/=:")
        if value.unicodeScalars.allSatisfy({ safe.contains($0) }) { return value }
        return "'" + value.replacingOccurrences(of: "'", with: "'\\''") + "'"
    }

    private func persist() {
        store.save(sessions)
    }

    // MARK: - Root resolution

    private static let rootKey = "MigratorGUI.projectRoot"

    private static func resolveRoot() -> URL {
        let marker = "scripts/single_claude_agent_migrate.sh"
        let fm = FileManager.default

        if let saved = UserDefaults.standard.string(forKey: rootKey),
           fm.fileExists(atPath: URL(fileURLWithPath: saved).appendingPathComponent(marker).path) {
            return URL(fileURLWithPath: saved)
        }
        if let env = ProcessInfo.processInfo.environment["MIGRATOR_PROJECT_ROOT"] {
            return URL(fileURLWithPath: env)
        }
        var dir = URL(fileURLWithPath: fm.currentDirectoryPath)
        for _ in 0..<6 {
            if fm.fileExists(atPath: dir.appendingPathComponent(marker).path) { return dir }
            dir = dir.deletingLastPathComponent()
        }
        return URL(fileURLWithPath: fm.currentDirectoryPath)
    }
}
