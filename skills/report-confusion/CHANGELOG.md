# Changelog

## [1.1.0] - 2026-11-03
### Added
- Reuses the "Make it yours" in-place pattern: stays in the active view and chat without spawning a new chat tab.
- Drag-to-select area crop: interactive rectangle selection instead of full-screen grabs.
- Cross-platform and mobile support: handles web and mobile touch pointer crops dropped into `tools/screens/`, with CLI interactive capture fallback on desktop.
- Dependency check command (`confusion.py check` / `/report-confusion check`) that names missing requirements before filing.
- Store listing metadata (`store-listing.json`), Claude Code plugin manifest (`plugin.json`), and slash commands.
- Clear attribution for GitHub CLI `gh`.

## [1.0.0] - 2026-11-02
### Added
- Initial version: screenshot grab, code diagnosis, and issue filing.
