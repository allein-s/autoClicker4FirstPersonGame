"""macOS work-area query for overlay positioning.

Uses AppKit ``NSScreen.visibleFrame`` (which excludes the menu bar and Dock)
and converts from Cocoa's bottom-left origin to the top-left origin used by
Tkinter geometry. Returns ``(left, top, right, bottom)`` in pixels.
"""

from __future__ import annotations


def work_area() -> tuple[int, int, int, int]:
    try:
        from AppKit import NSScreen

        screen = NSScreen.mainScreen()
        full = screen.frame()
        visible = screen.visibleFrame()
        full_height = full.size.height
        left = int(visible.origin.x)
        right = int(visible.origin.x + visible.size.width)
        # Convert bottom-left origin (Cocoa) to top-left origin (Tk).
        top = int(full_height - (visible.origin.y + visible.size.height))
        bottom = int(full_height - visible.origin.y)
        return left, top, right, bottom
    except Exception:
        return 0, 0, 1440, 900
