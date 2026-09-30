# Changelog

## 0.2.0

- Non-destructive automatic background-removal draft
- Foreground mask stored separately from original pixels
- Original / result / mask preview modes
- Restore brush and erase brush
- Transparent or custom-color background
- Mask review heuristics without fake confidence scores
- Explicit “누끼 확정” gate before background-removed export
- Editing a confirmed mask returns it to review-required state
- Rotating a photo invalidates and clears its old mask safely
- Automatic PNG selection for transparent output
- Background removal runs off the UI thread
- First automatic removal may download a compact local model; later use is cached locally

## 0.1.0

- GitHub-ready initial scaffold
- Multi-image and folder import
- Per-image and batch output settings
- Ratio / ID-photo-style / print / frame presets
- px/mm/cm/inch + DPI conversion
- Fill / Fit / Custom crop modes
- Zoom and X/Y manual crop controls
- EXIF orientation handling
- JPEG / PNG / WebP export
- Windows PyInstaller build
- GitHub Actions build and tag release workflows
