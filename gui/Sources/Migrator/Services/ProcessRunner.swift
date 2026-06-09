import Foundation

enum RunEvent: Sendable {
    case line(String, stderr: Bool)
    case exit(Int32)
}

/// Launches a child process and streams its merged stdout/stderr as an
/// `AsyncStream` of lines, finishing with the exit code. `@unchecked Sendable`
/// because it owns non-Sendable Foundation types (Process/Pipe) but only mutates
/// them from its own work; access is funnelled through `terminate()`.
final class ProcessRunner: @unchecked Sendable {
    private let process = Process()
    private let outPipe = Pipe()
    private let errPipe = Pipe()

    init(executable: URL, arguments: [String], cwd: URL, environment: [String: String]) {
        process.executableURL = executable
        process.arguments = arguments
        process.currentDirectoryURL = cwd
        process.environment = environment
        process.standardOutput = outPipe
        process.standardError = errPipe
    }

    func terminate() {
        if process.isRunning { process.terminate() }
    }

    func events() -> AsyncStream<RunEvent> {
        AsyncStream { continuation in
            let task = Task.detached { [self] in
                do {
                    try process.run()
                } catch {
                    continuation.yield(.line("✗ failed to launch: \(error.localizedDescription)", stderr: true))
                    continuation.yield(.exit(-1))
                    continuation.finish()
                    return
                }

                await withTaskGroup(of: Void.self) { group in
                    group.addTask {
                        do {
                            for try await line in self.outPipe.fileHandleForReading.bytes.lines {
                                continuation.yield(.line(line, stderr: false))
                            }
                        } catch {}
                    }
                    group.addTask {
                        do {
                            for try await line in self.errPipe.fileHandleForReading.bytes.lines {
                                continuation.yield(.line(line, stderr: true))
                            }
                        } catch {}
                    }
                    await group.waitForAll()
                }

                process.waitUntilExit()
                continuation.yield(.exit(process.terminationStatus))
                continuation.finish()
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    /// Inherit the caller's environment (so `claude`, `npx`, `tuist`, the `.env`
    /// fallback, etc. all resolve) and make sure common tool dirs are on PATH.
    static func baseEnvironment() -> [String: String] {
        var env = ProcessInfo.processInfo.environment
        let home = env["HOME"] ?? NSHomeDirectory()
        let prepend = ["/opt/homebrew/bin", "/usr/local/bin", "\(home)/.local/bin"]
        let existing = env["PATH"] ?? "/usr/bin:/bin:/usr/sbin:/sbin"
        env["PATH"] = (prepend + [existing]).joined(separator: ":")
        return env
    }
}
