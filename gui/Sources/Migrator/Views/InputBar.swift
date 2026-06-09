import SwiftUI

struct InputBar: View {
    @Environment(AppModel.self) private var model
    @FocusState private var focused: Bool

    var body: some View {
        @Bindable var model = model

        VStack(spacing: 8) {
            HStack(alignment: .bottom, spacing: 8) {
                commandPicker

                if model.selectedCommand.acceptsModel {
                    modelPicker
                }

                TextField(model.selectedCommand.placeholder, text: $model.input, axis: .vertical)
                    .textFieldStyle(.plain)
                    .lineLimit(1...6)
                    .font(.callout)
                    .padding(.vertical, 7)
                    .padding(.horizontal, 10)
                    .background(.quaternary.opacity(0.4), in: RoundedRectangle(cornerRadius: 9))
                    .focused($focused)
                    .onSubmit(send)

                if model.isRunning {
                    Button(role: .destructive, action: model.stop) {
                        Label("Stop", systemImage: "stop.fill")
                    }
                    .controlSize(.large)
                    .keyboardShortcut(".", modifiers: .command)
                } else {
                    Button(action: send) {
                        Label("Send", systemImage: "arrow.up.circle.fill")
                    }
                    .controlSize(.large)
                    .buttonStyle(.borderedProminent)
                    .keyboardShortcut(.return, modifiers: .command)
                    .disabled(model.input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }

            HStack(spacing: 6) {
                Image(systemName: "info.circle")
                Text("Type a request and press ⌘↵. Prefix with a /keyword (\(slashHints)) to switch command.")
                Spacer()
            }
            .font(.caption2)
            .foregroundStyle(.tertiary)
        }
        .padding(12)
        .onAppear { focused = true }
    }

    private var commandPicker: some View {
        @Bindable var model = model
        return Menu {
            Picker("Command", selection: $model.selectedCommandID) {
                ForEach(AppCommand.registry) { command in
                    Label(command.title, systemImage: command.symbol).tag(command.id)
                }
            }
            .pickerStyle(.inline)
            .labelsHidden()
        } label: {
            Label(model.selectedCommand.title, systemImage: model.selectedCommand.symbol)
        }
        .menuStyle(.borderlessButton)
        .fixedSize()
        .controlSize(.large)
    }

    private var modelPicker: some View {
        @Bindable var model = model
        return Menu {
            Picker("Model", selection: $model.selectedModel) {
                ForEach(AppModel.models, id: \.self) { name in
                    Text(name == "default" ? "Account default" : name).tag(name)
                }
            }
            .pickerStyle(.inline)
            .labelsHidden()
        } label: {
            Label(
                model.selectedModel == "default" ? "Model" : model.selectedModel,
                systemImage: "cpu"
            )
        }
        .menuStyle(.borderlessButton)
        .fixedSize()
        .controlSize(.large)
        .help("Model for the migration agent")
    }

    private var slashHints: String {
        AppCommand.registry.map(\.slash).joined(separator: ", ")
    }

    private func send() {
        model.send()
        focused = true
    }
}
