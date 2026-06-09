import Foundation
import SwiftUI

/// Who/what produced a line in the chat transcript.
enum MessageRole: String, Codable, Sendable {
    case user        // what the operator typed
    case command     // the resolved shell command we launched ("$ …")
    case assistant   // the migration agent's prose
    case tool        // a tool the agent invoked (Bash/Read/Edit/…)
    case toolResult  // truncated output of a tool call
    case output      // raw stdout/stderr from a plain script
    case system      // lifecycle notes (session started / finished)
    case error       // failures / non-zero exits

    var symbol: String {
        switch self {
        case .user:       return "person.crop.circle"
        case .command:    return "chevron.right.square"
        case .assistant:  return "sparkles"
        case .tool:       return "wrench.and.screwdriver"
        case .toolResult: return "arrow.turn.down.right"
        case .output:     return "text.alignleft"
        case .system:     return "info.circle"
        case .error:      return "exclamationmark.triangle"
        }
    }

    var tint: Color {
        switch self {
        case .user:       return .accentColor
        case .command:    return .secondary
        case .assistant:  return .purple
        case .tool:       return .teal
        case .toolResult: return .secondary
        case .output:     return .secondary
        case .system:     return .green
        case .error:      return .red
        }
    }

    var label: String? {
        switch self {
        case .user:       return "You"
        case .command:    return nil
        case .assistant:  return "Agent"
        case .tool:       return "Tool"
        case .toolResult: return nil
        case .output:     return nil
        case .system:     return nil
        case .error:      return "Error"
        }
    }

    var monospaced: Bool {
        switch self {
        case .command, .tool, .toolResult, .output: return true
        default: return false
        }
    }
}

struct ChatMessage: Identifiable, Codable, Sendable {
    var id = UUID()
    var role: MessageRole
    var text: String
    var date: Date = .now
}

/// One conversation. The operator keeps appending requests to the same session
/// to "sequently append new functionality" on top of a migration.
struct ChatSession: Identifiable, Codable, Sendable {
    var id = UUID()
    var title: String
    var commandID: String
    var messages: [ChatMessage] = []
    var createdAt: Date = .now
    var updatedAt: Date = .now
}
