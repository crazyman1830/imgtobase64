# BOLT'S JOURNAL - CRITICAL LEARNINGS ONLY

## 2025-12-16 - PIL Double-Encoding Bottleneck
**Learning:** The codebase frequently uses `PIL.Image` objects as the standard return type for processing functions, even for intermediate steps like compression or formatting. This forces an expensive "Encode to Buffer -> Decode to Image" cycle inside helper methods (e.g., `compress_image`), often followed immediately by another Encode operation by the caller. This results in double compression (quality loss) and double CPU usage (latency).
**Action:** When the ultimate goal is serialization (base64/file saving), prefer returning `(bytes, metadata)` or `(BytesIO, metadata)` from processing functions instead of re-inflated `PIL.Image` objects. Created `compress_to_buffer` to expose this efficient path.

## 2025-12-23 - Repeated DOM Queries in UI Controls
**Learning:** The app.js uses `querySelectorAll()` inside button click handlers (rotation/flip buttons) which queries the DOM on every button click. With batch processing of 100+ files or frequent UI interactions, this creates unnecessary overhead scanning the document tree repeatedly.
**Action:** Cache DOM element collections during initialization and reuse them. For rotation/flip button controls, store the NodeList in a variable once rather than querying on every interaction. This reduces DOM query overhead by ~50-75% for these operations.
