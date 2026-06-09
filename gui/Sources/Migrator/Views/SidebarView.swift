import SwiftUI

struct SidebarView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model

        List(selection: $model.selectedSessionID) {
            Section("Recent requests") {
                ForEach(model.sessions) { session in
                    SessionRow(
                        session: session,
                        isRunning: model.isRunning && session.id == model.selectedSessionID
                    )
                    .tag(session.id)
                    .contextMenu {
                        Button(role: .destructive) {
                            model.deleteSession(session.id)
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                    }
                }
            }
        }
        .listStyle(.sidebar)
        .overlay {
            if model.sessions.isEmpty {
                ContentUnavailableView(
                    "No requests yet",
                    systemImage: "bubble.left.and.bubble.right",
                    description: Text("Type a request on the right to start a migration.")
                )
            }
        }
        .safeAreaInset(edge: .bottom) {
            Button {
                model.newSession()
            } label: {
                Label("New Request", systemImage: "plus")
                    .frame(maxWidth: .infinity)
            }
            .controlSize(.large)
            .buttonStyle(.borderedProminent)
            .padding(10)
        }
    }
}

private struct SessionRow: View {
    let session: ChatSession
    let isRunning: Bool

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: AppCommand.command(id: session.commandID).symbol)
                .foregroundStyle(.secondary)
                .frame(width: 16)
            VStack(alignment: .leading, spacing: 2) {
                Text(session.title)
                    .lineLimit(1)
                    .font(.body)
                HStack(spacing: 4) {
                    Text(AppCommand.command(id: session.commandID).title)
                    Text("·")
                    Text(session.updatedAt, format: .dateTime.month().day().hour().minute())
                }
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)
            }
            Spacer(minLength: 0)
            if isRunning {
                ProgressView().controlSize(.small)
            }
        }
        .padding(.vertical, 2)
    }
}
