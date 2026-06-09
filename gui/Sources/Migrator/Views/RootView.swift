import SwiftUI

struct RootView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        NavigationSplitView {
            SidebarView()
                .navigationSplitViewColumnWidth(min: 230, ideal: 270, max: 360)
        } detail: {
            ChatView()
        }
        .toolbar {
            ToolbarItem(placement: .navigation) {
                Button { model.newSession() } label: {
                    Label("New Request", systemImage: "square.and.pencil")
                }
                .help("Start a new request (⌘N)")
            }
            ToolbarItem(placement: .primaryAction) {
                Button { model.chooseProjectRoot() } label: {
                    Label(model.projectRoot.lastPathComponent, systemImage: "folder")
                }
                .help("Project root: \(model.projectRoot.path)")
            }
        }
        .navigationTitle("Migrator")
    }
}
