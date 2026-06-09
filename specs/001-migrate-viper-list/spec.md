# Feature Specification: Migrate VIPER List module to a TCA feature

**Feature Branch**: `001-migrate-viper-list`

**Created**: 2026-06-05

**Status**: Draft

**Input**: User description: "Migrate the VIPER List module from VIPER-SWIFT into a TCA feature: load upcoming todos grouped by near-term date relation, no-content state, modal Add, reload on save"

## Migration Context *(mandatory for migration specs)*

- **Source feature**: `workspace/input/VIPER-SWIFT/VIPER-SWIFT/Classes/Modules/List/**` (+ shared `Common/Model/{TodoItem,NearTermDateRelation}`, `Common/Categories/NSCalendar+CalendarAdditions`, `Common/Clock/*`).
- **Source architecture**: VIPER — components: `ListInteractor`(+IO), `ListPresenter`, `ListViewController`/`ListViewInterface`, `ListWireframe`, `ListDataManager` (CoreData), `UpcomingDisplayDataCollection`.
- **Target TCA module**: `Features/List` (depends on: `Core/SharedModels`, `Core/Persistence`).
- **Component mapping** (cite `knowledge/viper-to-tca.md`):

  | Source component | → TCA target |
  |---|---|
  | `ListInteractor.findUpcomingItems` + `ListDataManager` (CoreData) | `@Dependency(\.todosClient).fetch` + `@Dependency(\.date)` |
  | `ListPresenter` + `UpcomingDisplayDataCollection` (sectioning) | `ListFeature` reducer + pure `upcomingSections(...)` in `SharedModels` |
  | `NSCalendar+CalendarAdditions.nearTermRelationForDate` | pure `nearTermRelation(for:relativeToToday:)` in `SharedModels` |
  | `ListViewInterface.showNoContentMessage` | `State.isEmpty` → no-content view |
  | `ListWireframe.presentAddInterface` | `delegate(.addTodoRequested)` handled by parent (App) `@Presents` sheet |
  | `AddModuleDelegate.addModuleDidSaveAddAction` | parent sends `List.refresh` after `Add.delegate(.saved)` |

- **Behavior to preserve**: load upcoming items relative to "today"; group/sort into Today → Tomorrow → Later This Week → Next Week, dropping empty/out-of-range; show a no-content state when there are none; request the Add screen; reload after a save.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See upcoming todos grouped by when they're due (Priority: P1)

A person opens the app and immediately sees their upcoming todos organized into clear, time-based
groups (Today, Tomorrow, Later This Week, Next Week) so they know what needs attention soonest.

**Why this priority**: This is the core value of the screen; without it there is no list.

**Independent Test**: Seed a few todos with different due dates, open the list, and verify they
appear under the correct groups in the correct order.

**Acceptance Scenarios**:

1. **Given** todos due today, tomorrow, and next week, **When** the list loads, **Then** they appear under "Today", "Tomorrow", and "Next Week" sections in that order.
2. **Given** a todo due in the past or far future, **When** the list loads, **Then** it is not shown (out of range).
3. **Given** no upcoming todos, **When** the list loads, **Then** a no-content message is shown.

### User Story 2 - Add a new todo (Priority: P2)

A person taps "Add", enters a name and due date on a modal screen, and saves — the new todo then
appears in the list.

**Why this priority**: Adding items is required to make the list useful over time, but the list is
viewable without it.

**Independent Test**: From the list, open Add, save an item, and verify the list reflects it.

**Acceptance Scenarios**:

1. **Given** the list is open, **When** the user taps Add, **Then** a modal Add screen is presented.
2. **Given** the Add screen with a valid name, **When** the user taps Save, **Then** the item is persisted and the list reloads showing it.
3. **Given** the Add screen, **When** the user taps Cancel, **Then** the screen dismisses and the list is unchanged.

### Edge Cases

- A todo due late on the last day of the week vs. the first day of next week is grouped by week boundary, not raw day count.
- Saving with an empty name does nothing (no item created).
- Loading while a previous load is in flight shows a loading state without duplicate sections.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The list MUST load upcoming todos relative to the current date when it appears.
- **FR-002**: The list MUST group todos into Today / Tomorrow / Later This Week / Next Week, in that order, omitting empty groups.
- **FR-003**: The list MUST exclude todos that are in the past or beyond next week.
- **FR-004**: The list MUST show a no-content state when there are no upcoming todos.
- **FR-005**: Users MUST be able to request an Add screen from the list.
- **FR-006**: When a todo is saved, the system MUST persist it and the list MUST reload to reflect it.
- **FR-007**: Cancelling Add MUST leave the list unchanged.

### Key Entities *(include if feature involves data)*

- **Todo**: a task with a name and a due date.
- **Near-term date relation**: the classification of a due date relative to today (today, tomorrow, later this week, next week, out of range), which determines its group and order.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of todos with due dates in the next-week window appear in the correct group (verified by automated tests over representative dates).
- **SC-002**: Date-grouping logic is covered by automated tests for each relation (today/tomorrow/later-this-week/next-week/out-of-range).
- **SC-003**: A saved todo appears in the list without a manual refresh.
- **SC-004**: The migrated screen reproduces the source app's grouping and ordering for the same inputs.

## Assumptions

- "Upcoming" spans from today through the end of next week (matches the source's date window).
- Persistence is abstracted behind a client; an in-memory implementation is acceptable for v1, with CoreData backing deferred.
- The Add screen is presented modally (the source used a custom modal transition; a standard modal is acceptable).
- The shipping app targets iOS; modules may also build on macOS for test validation.
