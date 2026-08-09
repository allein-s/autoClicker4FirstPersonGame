"""macOS platform backend.

Implemented with `pynput` (Quartz under the hood) for input injection and the
global hotkey, and AppKit `NSScreen` for the work-area query. Launch-at-login
uses a LaunchAgent plist.

Runtime requirements (installed only on macOS via environment markers in
``requirements.txt``): ``pynput`` and ``pyobjc-framework-Cocoa``.

Permissions: macOS requires the app to be granted **Accessibility** and
**Input Monitoring** (System Settings -> Privacy & Security) before injected
input and the global hotkey work.
"""
