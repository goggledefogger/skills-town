# Changelog

## 1.2.1
Fixed the skill's description, which broke its header so installers skipped it (2026-11-04).

## [1.2.0] - 2026-11-04
### Changed
- Renamed to AstroHuh. The command is now `/astrohuh` (and `/astrohuh check`).
- The `/confusing` alias is removed.
- Before asking, the skill tells the member who reads a report and what to expect.
- Says plainly when the member's GitHub account cannot file to that repo.
- When it can't, the report is kept in Astrolabe's own reports on this computer (`astrohuh.py draft` and `save`), the same place the Tell Dan and Danny button keeps them.

## [1.1.0] - 2026-11-03
### Added
- Reuses the "Make it yours" in-place pattern: stays in the active view and chat without starting a new chat tab.
- Drag-select crop on a Mac desktop, or paste a screenshot (works anywhere, including a phone).
- Dependency check command (`confusion.py check` / `/report-confusion check`) that names missing requirements before filing.
- Store listing metadata (`store-listing.json`), Claude Code plugin manifest (`plugin.json`), and slash commands.
- Clear attribution for GitHub CLI `gh`.

## [1.0.0] - 2026-11-02
### Added
- Initial version: screenshot grab, code diagnosis, and issue filing.
