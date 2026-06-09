import Foundation

/// A concrete process invocation: what to launch, with which args and extra env.
struct CommandSpec: Sendable {
    var executable: URL = URL(fileURLWithPath: "/bin/bash")
    var arguments: [String]
    var environment: [String: String] = [:]
}

/// A user-facing command in the chat. The registry below is the single place to
/// add new functionality — drop in another entry and it shows up in the picker
/// and responds to its `/slash` keyword.
struct AppCommand: Identifiable, Sendable {
    let id: String
    let title: String
    let symbol: String
    let slash: String
    let placeholder: String
    /// When true, output is Claude `stream-json` and is parsed into readable bubbles.
    let streamsJSON: Bool
    /// When true, the input bar shows a Model picker and passes the choice through.
    var acceptsModel: Bool = false
    let build: @Sendable (_ argument: String, _ root: URL) -> CommandSpec

    static let registry: [AppCommand] = [
        AppCommand(
            id: "migrate", title: "Migrate", symbol: "wand.and.stars", slash: "/migrate",
            placeholder: "Describe the migration objective (blank → default demo)…",
            streamsJSON: true, acceptsModel: true
        ) { argument, _ in
            var args = ["scripts/claude_migrate.sh", "--no-pick"]
            if !argument.isEmpty { args.append(argument) }
            return CommandSpec(arguments: args, environment: ["OUTPUT_FORMAT": "stream-json"])
        },
        AppCommand(
            id: "swarm", title: "Swarm", symbol: "square.stack.3d.up", slash: "/swarm",
            placeholder: "Objective for the RUFLO hive-mind swarm…",
            streamsJSON: false
        ) { argument, _ in
            var args = ["scripts/swarm_migrate.sh"]
            if !argument.isEmpty { args.append(argument) }
            return CommandSpec(arguments: args)
        },
        AppCommand(
            id: "analyze", title: "Analyze", symbol: "chart.bar.doc.horizontal", slash: "/analyze",
            placeholder: "Repo path to analyze (blank → workspace/input)…",
            streamsJSON: false
        ) { argument, _ in
            var args = ["scripts/code_map.sh"]
            if !argument.isEmpty { args.append(argument) }
            return CommandSpec(arguments: args)
        },
        AppCommand(
            id: "build", title: "Build check", symbol: "hammer", slash: "/build",
            placeholder: "Output dir to build + test (blank → workspace/output)…",
            streamsJSON: false
        ) { argument, _ in
            var args = ["scripts/build_check.sh"]
            if !argument.isEmpty { args.append(argument) }
            return CommandSpec(arguments: args)
        },
        AppCommand(
            id: "shell", title: "Shell", symbol: "terminal", slash: "/sh",
            placeholder: "Run a shell command in the project root…",
            streamsJSON: false
        ) { argument, _ in
            CommandSpec(arguments: ["-lc", argument.isEmpty ? "true" : argument])
        },
    ]

    static func command(id: String) -> AppCommand {
        registry.first { $0.id == id } ?? registry[0]
    }

    /// Map raw input to (command, argument). A leading `/keyword` overrides the
    /// picker; otherwise the whole line is the argument for the selected command.
    static func resolve(_ raw: String, fallback: AppCommand) -> (AppCommand, String) {
        if raw.first == "/" {
            let parts = raw.split(separator: " ", maxSplits: 1, omittingEmptySubsequences: true)
            let token = String(parts.first ?? "")
            if let command = registry.first(where: { $0.slash == token }) {
                let argument = parts.count > 1
                    ? String(parts[1]).trimmingCharacters(in: .whitespacesAndNewlines)
                    : ""
                return (command, argument)
            }
        }
        return (fallback, raw)
    }
}
