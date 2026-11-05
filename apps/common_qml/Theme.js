.pragma library

// Single theme-token source for shared QML components ("global.css" equivalent).
// Edit a token here to retheme every component that imports this file.
// Values are the app's current palette (slate/Tailwind-derived); do not
// change them without a deliberate design decision.

// Surfaces
var surfaceWhite = "#ffffff"        // card / panel backgrounds
var surfaceSubtle = "#f8fafc"       // subtle fills (page tint, zebra row)
var surfaceHover = "#f1f5f9"        // hover states, inactive tracks

// Borders & dividers
var borderSubtle = "#e2e8f0"        // hairline dividers
var borderDefault = "#cbd5e1"       // input & button borders
var borderLightBlue = "#bfdbfe"     // accent-colored borders, text selection

// Text
var textPrimary = "#0f172a"         // near-black main text
var textStrong = "#1e293b"          // headings / emphasized
var textSecondary = "#334155"       // body text
var textMuted = "#64748b"           // secondary / placeholder
var textFaint = "#94a3b8"           // disabled / faintest

// Accent (blue)
var accentPrimary = "#2563eb"       // primary buttons, focus, active page
var accentHover = "#1d4ed8"         // accent hover
var accentMid = "#3b82f6"           // accent 500 (banners, links)
var accentDeep = "#1e3a8a"          // deep accent text
var accentSurface = "#eff6ff"       // light-blue tinted surfaces

// Success (green)
var successBackground = "#dcfce7"
var successBorder = "#86efac"
var successText = "#166534"
var successDot = "#16a34a"
var successBright = "#10b981"

// Error (red)
var errorBackground = "#fee2e2"
var errorBorder = "#fca5a5"
var errorText = "#991b1b"
var errorDot = "#dc2626"
var errorBright = "#ef4444"
var errorDeep = "#b91c1c"           // pressed danger surfaces