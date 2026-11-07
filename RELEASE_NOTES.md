# Release notes

## 0.2.0 (upcoming)

This release focuses on a more maintainable application structure and a more
comfortable reading experience across restarts.

### Added

- Saved reader preferences, including the last page, theme, layout, zoom, and
  window size.
- Recovery from invalid or incomplete settings and bookmark files.
- A script and AppStream metadata for building an AppImage package.
- Automated tests for settings, bookmarks, PDF handling, rendering, themes, and
  window state.

### Changed

- Split configuration, theme handling, and page rendering into dedicated
  modules.
- Improved PDF path discovery and page dimension caching.
