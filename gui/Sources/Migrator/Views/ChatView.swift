import SwiftUI

struct ChatView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        VStack(spacing: 0) {
            if let session = model.selectedSession, !session.messages.isEmpty {
                transcript(session)
            } else {
                EmptyChatView()
            }
            Divider()
            InputBar()
        }
        .navigationTitle(model.selectedSession?.title ?? "Migrator")
        .navigationSubtitle(model.isRunning ? "Running…" : "Idle")
    }

    private func transcript(_ session: ChatSession) -> some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    ForEach(session.messages) { message in
                        MessageRow(message: message)
                            .id(message.id)
                    }
                    Color.clear.frame(height: 1).id(Self.bottomID)
                }
                .padding(16)
            }
            .onChange(of: session.messages.count) {
                withAnimation(.easeOut(duration: 0.15)) {
                    proxy.scrollTo(Self.bottomID, anchor: .bottom)
                }
            }
            .onAppear {
                proxy.scrollTo(Self.bottomID, anchor: .bottom)
            }
        }
    }

    private static let bottomID = "transcript-bottom"
}

private struct EmptyChatView: View {
    @Environment(AppModel.self) private var model

    private let examples: [(command: String, text: String, label: String)] = [
        ("analyze", "", "Analyze the source app in workspace/input"),
        ("migrate", "", "Run the default VIPER → TCA migration"),
        ("build", "", "Build + test the generated project"),
    ]

    var body: some View {
        VStack(spacing: 18) {
            Spacer()
            Image(systemName: "arrow.triangle.2.circlepath")
                .font(.system(size: 44))
                .foregroundStyle(.tertiary)
            VStack(spacing: 4) {
                Text("Drive a migration")
                    .font(.title2.weight(.semibold))
                Text("Pick a command below, type a request, and watch the scripts run.")
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            VStack(spacing: 8) {
                ForEach(examples, id: \.label) { example in
                    Button {
                        model.selectedCommandID = example.command
                        model.input = example.text
                    } label: {
                        HStack {
                            Image(systemName: AppCommand.command(id: example.command).symbol)
                            Text(example.label)
                            Spacer()
                        }
                        .padding(.vertical, 8)
                        .padding(.horizontal, 12)
                        .frame(maxWidth: 380)
                        .background(.quaternary.opacity(0.5), in: RoundedRectangle(cornerRadius: 8))
                    }
                    .buttonStyle(.plain)
                }
            }
            if !model.rootIsValid {
                Label(
                    "scripts/ not found in the selected project root — pick the folder via the toolbar.",
                    systemImage: "exclamationmark.triangle"
                )
                .font(.callout)
                .foregroundStyle(.orange)
                .padding(.top, 8)
            }
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(24)
    }
}
