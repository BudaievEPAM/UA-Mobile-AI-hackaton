import SwiftUI

struct MessageRow: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: message.role.symbol)
                .foregroundStyle(message.role.tint)
                .frame(width: 18)
                .padding(.top, 1)

            VStack(alignment: .leading, spacing: 3) {
                if let label = message.role.label {
                    Text(label)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(message.role.tint)
                }
                Text(message.text)
                    .font(message.role.monospaced
                          ? .system(.callout, design: .monospaced)
                          : .callout)
                    .foregroundStyle(textColor)
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .modifier(BubbleBackground(role: message.role))
            }
        }
    }

    private var textColor: Color {
        switch message.role {
        case .toolResult, .output: return .secondary
        case .error:               return .red
        default:                   return .primary
        }
    }
}

/// Subtle backgrounds: user requests and tool calls get a tinted card; agent
/// prose and plain output stay flush with the transcript.
private struct BubbleBackground: ViewModifier {
    let role: MessageRole

    func body(content: Content) -> some View {
        switch role {
        case .user:
            content
                .padding(.vertical, 7).padding(.horizontal, 11)
                .background(Color.accentColor.opacity(0.12), in: RoundedRectangle(cornerRadius: 9))
        case .tool, .command:
            content
                .padding(.vertical, 6).padding(.horizontal, 10)
                .background(.quaternary.opacity(0.5), in: RoundedRectangle(cornerRadius: 8))
        case .toolResult:
            content
                .padding(.vertical, 6).padding(.horizontal, 10)
                .background(.quaternary.opacity(0.3), in: RoundedRectangle(cornerRadius: 8))
        case .error:
            content
                .padding(.vertical, 6).padding(.horizontal, 10)
                .background(Color.red.opacity(0.10), in: RoundedRectangle(cornerRadius: 8))
        default:
            content
        }
    }
}
