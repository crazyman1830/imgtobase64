## 2025-12-18 - Keyboard Accessible Drag & Drop Zones
**Learning:** Drag & drop zones often rely solely on mouse interactions (click/drag). Making them keyboard-accessible requires adding `tabindex="0"`, `role="button"`, and mapping `Enter`/`Space` keys to the hidden file input's click event.
**Action:** Always ensure large interactive areas have keyboard handlers and visible focus states.

## 2025-12-23 - Immediate Feedback on Copy Actions
**Learning:** Relying solely on toast messages for copy actions separates the feedback from the user's locus of attention. Changing the button state provides immediate, contextual confirmation that feels more responsive.
**Action:** Implement "success state" transitions (text/icon/color) for copy buttons that revert after a short delay.
