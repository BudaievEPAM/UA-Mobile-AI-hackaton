import Foundation

/// Turns one raw output line into zero or more chat messages. For Claude
/// `stream-json` runs it interprets the event schema into readable bubbles;
/// anything else (plain shell scripts, the runner's own banner lines) is shown
/// verbatim.
enum StreamJSON {
    struct Item: Sendable {
        let role: MessageRole
        let text: String
    }

    static func parse(_ line: String, preferJSON: Bool) -> [Item] {
        let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty { return [] }

        if preferJSON, trimmed.first == "{",
           let data = trimmed.data(using: .utf8),
           let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            return interpret(object)
        }
        return [Item(role: .output, text: line)]
    }

    // MARK: - stream-json interpretation

    private static func interpret(_ object: [String: Any]) -> [Item] {
        guard let type = object["type"] as? String else { return [] }
        switch type {
        case "system":
            guard (object["subtype"] as? String) == "init" else { return [] }
            let model = object["model"] as? String ?? "?"
            let tools = (object["tools"] as? [Any])?.count ?? 0
            return [Item(role: .system, text: "● session started · model \(model) · \(tools) tools")]

        case "assistant":
            return contentBlocks(object).compactMap { block in
                guard let kind = block["type"] as? String else { return nil }
                if kind == "text", let text = block["text"] as? String {
                    let clean = text.trimmingCharacters(in: .whitespacesAndNewlines)
                    return clean.isEmpty ? nil : Item(role: .assistant, text: clean)
                }
                if kind == "tool_use" {
                    let name = block["name"] as? String ?? "tool"
                    let summary = toolInputSummary(block["input"] as? [String: Any])
                    return Item(role: .tool, text: summary.isEmpty ? name : "\(name)  ·  \(summary)")
                }
                return nil
            }

        case "user":
            return contentBlocks(object).compactMap { block in
                guard (block["type"] as? String) == "tool_result" else { return nil }
                let text = toolResultText(block["content"])
                return text.isEmpty ? nil : Item(role: .toolResult, text: truncate(text, 600))
            }

        case "result":
            let isError = (object["is_error"] as? Bool) ?? false
            var bits: [String] = []
            if let cost = object["total_cost_usd"] as? Double { bits.append(String(format: "$%.3f", cost)) }
            if let ms = object["duration_ms"] as? Double { bits.append(String(format: "%.0fs", ms / 1000)) }
            if let turns = object["num_turns"] as? Int { bits.append("\(turns) turns") }
            let meta = bits.isEmpty ? "" : "  ·  " + bits.joined(separator: "  ·  ")
            if isError {
                let detail = object["result"] as? String ?? object["subtype"] as? String ?? "error"
                return [Item(role: .error, text: "✗ \(detail)\(meta)")]
            }
            return [Item(role: .system, text: "✓ done\(meta)")]

        default:
            return []
        }
    }

    private static func contentBlocks(_ object: [String: Any]) -> [[String: Any]] {
        guard let message = object["message"] as? [String: Any],
              let content = message["content"] as? [[String: Any]] else { return [] }
        return content
    }

    private static func toolInputSummary(_ input: [String: Any]?) -> String {
        guard let input else { return "" }
        for key in ["command", "file_path", "path", "pattern", "query", "url", "description"] {
            if let value = input[key] as? String, !value.isEmpty {
                return truncate(value.replacingOccurrences(of: "\n", with: " "), 140)
            }
        }
        if let data = try? JSONSerialization.data(withJSONObject: input),
           let json = String(data: data, encoding: .utf8) {
            return truncate(json, 140)
        }
        return ""
    }

    private static func toolResultText(_ content: Any?) -> String {
        if let string = content as? String { return string }
        if let blocks = content as? [[String: Any]] {
            return blocks.compactMap { $0["text"] as? String }.joined(separator: "\n")
        }
        return ""
    }

    private static func truncate(_ string: String, _ max: Int) -> String {
        string.count <= max ? string : String(string.prefix(max)) + " …"
    }
}
