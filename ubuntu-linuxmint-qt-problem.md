# 📋 Problem Summary: `./LibrarianManagement` Crash Analysis

### 🔍 Symptoms
When executing `./LibrarianManagement`, the application immediately crashes with **`Aborted (core dumped)`**. The terminal log highlights two distinct errors:
1. `undefined symbol: g_task_set_static_name` inside `/usr/lib/x86_64-linux-gnu/gvfs/libgvfscommon.so`.
2. `Could not initialize GLX` and `Failed to finding matching FBConfig` triggered by the Qt/OpenGL subsystem.

---

### 🛠️ Root Causes

The crash is a chain reaction caused by **two overlapping issues**:

#### 1. Shared Library Mismatch (`GLib` / `GIO` Conflict)
* **The Cause:** The `LibrarianManagement` application package contains bundled, outdated versions of core GNOME libraries (such as `libglib-2.0.so` or `libgio-2.0.so`) within its runtime directory.
* **The Impact:** When launched, the application forces the OS to use these outdated internal libraries. However, the host operating system's modern network/file components (like `libgvfscommon.so`) depend on newer functions. Because it cannot locate the modern symbol `g_task_set_static_name` in the old library, the shared library initialization breaks.

#### 2. Graphics Subsystem Failure (`GLX` Initialization Breakdown)
* **The Cause:** The crash in the shared library framework cascades into the display pipeline, preventing the standard Mesa graphics driver (`swrast`/Intel driver) from mapping core framebuffers.
* **The Impact:** The application relies on modern Qt (likely Qt 6), which strict-requires hardware-accelerated 3D rendering (RHI) to draw its GUI. Since it fails to resolve a valid rendering configuration (`FBConfig`) via GLX or EGL, the windowing system aborts execution.

---

### 💡 Workarounds & Solutions

| Strategy | Execution Command | Purpose |
| :--- | :--- | :--- |
| **1. Dynamic Link Overriding** | `LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libglib-2.0.so.0 /usr/lib/x86_64-linux-gnu/libgio-2.0.so.0" ./LibrarianManagement` | Forces the binary to prioritize host system libraries, bypassing the corrupted runtime bundle and resolving the `undefined symbol` error. |
| **2. Software Vector Rasterization** | `LIBGL_ALWAYS_SOFTWARE=1 ./LibrarianManagement` | Bypass the physical GPU drivers by routing all OpenGL/GLX instructions directly through the host CPU engine. |
| **3. Combined Mitigation** | `LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libglib-2.0.so.0 /usr/lib/x86_64-linux-gnu/libgio-2.0.so.0" LIBGL_ALWAYS_SOFTWARE=1 ./LibrarianManagement` | Addresses the library mismatch and the graphics backend errors concurrently in one execution path. |
| **4. Purge Outdated Bundles** | Clean local application directory by running `mv libglib* libglib*.bak` and `mv libgio* libgio*.bak` | The ultimate structural fix: removes the outdated internal files entirely to natively rely on system libraries. |

---

### ✅ Permanent Source-Level & Packaging Resolution

The issues have been resolved directly in the project codebase:

1. **Packaging (`packaging/*.spec`)**:
   - Explicitly filters out `libglib*`, `libgio*`, `libgobject*`, and `libgmodule*` from `a.binaries` on Linux platforms. This prevents bundling outdated GLib/GIO into the executable and lets the binary link directly to host system libraries.

2. **Runtime Startup (`apps/common_linux_env.py` & `apps/*/main.py`)**:
   - In frozen Linux environments, `GIO_MODULE_DIR` is set to `""` before Qt/GIO loads, preventing conflicts with host GVFS dynamic modules.
   - Automatically defaults `LIBGL_ALWAYS_SOFTWARE=1` on Linux unless overridden by user environment variables, preventing Qt Quick GLX / FBConfig crashes.
