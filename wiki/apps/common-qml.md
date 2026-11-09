# Common QML Components Library (`apps/common_qml/`)

The `apps/common_qml/` folder contains shared, production-tested QML components reusable across Student Management, Librarian Management, and Booth Kiosk apps.

---

## 1. Components Reference

### 1.1 `StyledSearchField.qml`
- Standardized text input with crisp white background, `#cbd5e1` border, blue focus ring, dark text `#0f172a`, and placeholder text.
- Replaces unstyled native `TextField` controls that render invisibly on certain Linux desktop themes or dark modes.
- Sizing invariants: `implicitWidth: Math.max(180, Math.round(contentWidth + leftPadding + rightPadding + 20))`, `implicitHeight: Math.max(38, Math.round(((font.pixelSize > 0 ? font.pixelSize : 14)) * 2.2))`, with 12px padding and vertical centering (`TextInput.AlignVCenter`). Guaranteed not to collapse under extreme UI downscaling (maintains `implicitWidth >= 120`, `implicitHeight >= 36`).
- **Signals**: `onAccepted`.

### 1.2 `PaginationBar.qml`
- Reusable pagination toolbar supporting first, previous, numbered pages, next, last, and summary info text (`หน้า X จาก Y (N รายการ)`).
- **Properties**:
  - `currentPage: int`
  - `totalPages: int`
  - `totalCount: int`
  - `countUnit: string` (e.g. `"รายการ"`, `"เล่ม"`)
- **Signals**: `pageRequested(int page)`.

### 1.3 `ActionFeedbackBanner.qml`
- Toast/notification banner providing visual confirmation of database actions.
- Automatically handles success (green background `#ecfdf5`) and error (red background `#fef2f2`) states.
- **Properties**: `text`, `isError`, `duration`.

### 1.4 `AuditLogView.qml`
- Standardized audit log viewer component displaying timestamp, actor, entity, action, and detail.
- **Properties**: `logList`, `logModel`.

### 1.5 `FirstLaunchDialog.qml`
- First-time wizard dialog greeting the user when database is empty.
- Provides choice between selecting an Excel roster file for initial import or creating a blank standard schema database.
- **ObjectNames**: `firstLaunchDialog`, `firstLaunchStatusText`, `firstLaunchImportBtn`, `firstLaunchBlankBtn`.

### 1.6 `SettingsView.qml`
- Visual display settings view allowing runtime customization of typography and interface proportions.
- Features:
  - Font family selector with system font presets (System Default, Noto Sans, Sarabun, TH Sarabun New, Segoe UI, Sukhumvit Set, Tahoma) and dynamic font lookup.
  - Font size adjustment slider and steppers constrained between 10px and 24px (default 14px).
  - UI scaling slider constrained between 50% (0.5x) and 150% (1.5x) with preset quick buttons (75%, 100%, 125%, 150%).
  - Live interactive preview card displaying typography hierarchy (headings, body, metadata, badges) in real time (modularized into `SettingsPreviewCard.qml`).
  - Global application typography propagation across all views via `Typography.js` and Qt application font sync (`setAppFont`).
  - Auto-loads persisted settings on `Component.onCompleted` from active adapter (`loadSettings`).
  - Manual persistence via "💾 บันทึกการตั้งค่า (Save Settings)" button (`btnSaveSettings`) invoking `saveSettings`.
  - Reset to factory defaults button (`btnResetSettings`) persisting defaults via `resetSettings`.
- **Properties**: `currentFontFamily`, `activeFontFamily`, `currentFontSize`, `currentUiScale`, `targetWindow`.
- **Functions**: `loadPersistedSettings()`, `saveSettings()`, `resetToDefaults()`, `applySettingsToWindow()`.
- **ObjectNames**: `settingsView`, `fontFamilyCombo`, `fontSizeSlider`, `btnFontSizeMinus`, `btnFontSizePlus`, `scaleSlider`, `btnResetSettings`, `btnSaveSettings`, `saveStatusText`, `previewCard`.

### 1.7 `Typography.js`
- Shared `.pragma library` script that maintains baseline font sizes and original font families across QML UI component trees.
- Recursively traverses QML node hierarchies to apply user-selected font families and scaling factors dynamically without requiring restart.
- Caches `currentConfig` across the library module to support immediate delegate lifecycle hooks.
- Automatically normalizes baseline font sizes (`extractBaselineSize`) and control heights (`recordBaseHeight`) by dividing current active scale factors, preventing double-scaling during lazy ListView delegate initialization.
- Preserves explicit monospace formatting for code/raw identifiers.
- **Functions**: `recordDefaults(obj)`, `applyToNode(obj, config)`, `applyToTree(root, config, skipNode)`, `applyToItem(item)`, `scale(basePx)`.

### 1.10 `Theme.js`
- Shared `.pragma library` script acting as the single theme-token source for all shared components — the QML equivalent of a `global.css` stylesheet.
- All color values in `common_qml/` components reference tokens from this file (e.g. `Theme.textPrimary`, `Theme.accentPrimary`); **edit a token here to retheme every shared component at once**.
- Token groups: surfaces (`surfaceWhite`, `surfaceSubtle`, `surfaceHover`), borders (`borderSubtle`, `borderDefault`, `borderLightBlue`), text (`textPrimary`, `textStrong`, `textSecondary`, `textMuted`, `textFaint`), accent (`accentPrimary`, `accentHover`, `accentMid`, `accentDeep`, `accentSurface`), success (`successBackground`, `successBorder`, `successText`, `successDot`, `successBright`), error (`errorBackground`, `errorBorder`, `errorText`, `errorDot`, `errorBright`).
- Current values are the app's existing slate/Tailwind-derived palette — changing a value is a deliberate design decision, not a refactor.
- Usage: `import "Theme.js" as Theme` (same-directory, or relative path from other directories, same as `Typography.js`).
- Scope: shared components only; app view files (`apps/*/qml/`) may still hold local hex values pending a future sweep to `Theme.js` tokens.

### 1.12 `StyledDialog.qml`
- Shared `Dialog` root providing the global popup/window style: white rounded background + hairline border (Theme tokens), bold 16px `Theme.textPrimary` header bound to `title` (collapses when title is empty), themed OK/Cancel footer (`StyledButton` Primary/Neutral) wired to `accepted()`/`rejected()`.
- Footer auto-hides when `standardButtons` has no Ok/Cancel bits (e.g. `Dialog.Close`, `Dialog.NoButton`); dialogs that need custom footer buttons use `standardButtons: Dialog.NoButton` and keep their own in-content footer RowLayout.
- Defaults provided: `modal: true`, `closePolicy: Popup.CloseOnEscape`, `anchors.centerIn: parent`, `padding: 16`.
- All app popups (13 dialogs across the four action-dialog files, plus `FirstLaunchDialog`) use `StyledDialog`; raw `Dialog {` no longer appears in `apps/*/qml/`. `FileDialog` (OS-native) is intentionally excluded.

### 1.11 `StyledButton.qml` & `StyledComboBox.qml`
- `StyledButton`: shared `Button` root with `enum Variant { Primary, Neutral, Danger, Ghost }` (filled accent, white+slate-border, filled error-red, borderless). All colors come from `Theme.js`; dynamic variants are allowed (e.g. `variant: mode === 0 ? StyledButton.Primary : StyledButton.Neutral`).
- `StyledComboBox`: shared `ComboBox` root with the AGENTS Rule-7 alignment (left-align / VCenter, 12px padding) baked into `contentItem` and the dropdown `ItemDelegate`, so ad-hoc alignment styling in views is no longer required. `model`/`textRole`/`displayedText` pass through as real ComboBox properties.
  - The dropdown `popup` override **must** declare its own `contentItem: ListView { clip: true; implicitHeight: contentHeight; model: control.delegateModel; currentIndex: control.highlightedIndex; highlightMoveDuration: 0; T.ScrollBar.vertical: ScrollBar {} }` — in Qt Quick Controls 2 the options list is part of the *style's* popup; overriding `popup` without a ListView drops the option rows entirely (popup opens as an empty 0px box). Popup sizing: `implicitHeight: Math.min(implicitContentHeight + padding * 2, 240)` (240px cap with scroll).
  - The `delegate` **must** declare `required property var model` + `required property int index` and bind `text: model[control.textRole]` — the ComboBox machinery injects row data into the delegate's declared `model` property; without the declaration (and the `text` binding) rows render with empty text. Works for object models (`textRole` picks the role) and plain string models (rows arrive wrapped as objects).
  - Both contracts regression-tested in `tests/test_ui_librarian.py::test_category_dropdown_renders_options`. Test gotcha: dynamically created delegates are not reachable via `window.findChildren(...)` (QML scene-graph parents ≠ QObject child tree) — fetch row items via `QQmlExpression(ctx, listView, "itemAt(x, y)")`.
- All app views and dialogs use these (plus `StyledTextInput`/`StyledSearchField`); raw `Button`/`TextField`/`ComboBox` with custom backgrounds no longer appear in `apps/*/qml/`. Non-standard styling (e.g. orange/purple status chips, red-border validation states, gradient backgrounds) is preserved by passing a custom `background`/`contentItem` through on the styled component.

### 1.8 `StyledTextInput.qml`
- Standardized text input field with white background, `#cbd5e1` border, blue focus ring (`#2563eb`), dark text `#0f172a`, and WCAG AA placeholder text `#64748b`.
- Sizing invariants: `implicitWidth: Math.max(120, Math.round(contentWidth + leftPadding + rightPadding + 20))`, `implicitHeight: Math.max(38, Math.round(((font.pixelSize > 0 ? font.pixelSize : 14)) * 2.2))`, `leftPadding: 12`, `rightPadding: 12`, `verticalAlignment: TextInput.AlignVCenter`, and `background.implicitHeight: control.implicitHeight`.
- Provides mouse selection (`selectByMouse: true`, `selectionColor: "#bfdbfe"`, `selectedTextColor: "#0f172a"`).

### 1.9 `BundledFonts.qml` & Built-in Font Assets (`apps/common_qml/fonts/`)
- Declares QML `FontLoader` instances for bundled fonts shipped with the application binaries:
  - `NotoSansThai-Regular.ttf` & `NotoSansThai-Bold.ttf`
  - `THSarabunNew.ttf` & `THSarabunNew-Bold.ttf`
  - `THSarabun.ttf` & `THSarabun-Bold.ttf`
  - `Tahoma.ttf` & `Tahoma-Bold.ttf`
  - `SukhumvitSet.ttc`
- Registered at application startup via `core.shared.mock_qt.register_bundled_fonts()` using `QFontDatabase.addApplicationFont` with automatic `QFont.insertSubstitution` aliases for `"Noto Sans"` and `"Sarabun"`.
- Shipped out-of-the-box across all platforms without requiring host operating system font installations.

### 1.9 Responsive Table Delegate Typography Pattern
Because Qt Quick instantiates `ListView` delegates lazily when models are populated asynchronously (`model.append(...)`), table rows will bypass initial tree walkers unless dual-layer scaling is applied:
1. **Reactive Property Binding**: Root `ApplicationWindow` exposes `fontScale` and `appFontFamily`. Delegates bind font sizes directly to `Math.max(min, Math.round(base * (window.fontScale || 1.0)))`.
2. **Lifecycle Hook**: Delegates invoke `Component.onCompleted: Typography.applyToItem(this)` to ensure custom families and height scales are applied instantly on creation.
3. **Dynamic Row & Header Heights**: Tables must calculate `implicitHeight: Math.max(minH, Math.round(rowContent.implicitHeight + pad))` and `height: implicitHeight` rather than hardcoded pixel dimensions.

---

## 2. QML Engine Integration
All application entry points (`apps/*/main.py`) configure the import path for `apps/common_qml` both in development and PyInstaller frozen modes:

```python
common_qml_dir = os.path.join(sys._MEIPASS, "apps", "common_qml") \
    if getattr(sys, "frozen", False) else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "common_qml"))
engine.addImportPath(common_qml_dir)
engine.addImportPath(os.path.dirname(common_qml_dir))
```

And in QML files:
```qml
import "../../common_qml"
```
