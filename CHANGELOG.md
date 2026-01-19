# Changelog

All notable changes to TAXY will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-19

### Added
- Initial TAXY release based on kTAY8 project
- YOLOv8 AI-powered nozzle detection
- Klipper extension with `KTAY_*` commands (fixed naming to avoid Klipper parsing issues)
- Bulletproof `install.sh` with proper function ordering
- Complete documentation (README, troubleshooting, naming rationale)
- TAXY-prefixed macros for clean user experience
- Legacy compatibility macros for kTAY8 migration
- Systemd service integration
- Live AI detection preview
- Camera mm/px calibration
- Tool offset measurement

### Fixed
- Command naming issue: `KTAY8_*` → `KTAY_*` to avoid Klipper "Malformed command" error
- Install script function definition order (functions now defined before use)
- Statistics module import conflict (local implementation instead of stdlib)
- Python cache issues (proper venv handling)

### Changed
- Renamed project from kTAY8 to TAXY for clarity
- Updated all internal references (ktay8 → taxy)
- Improved server architecture with persistent DetectionManager
- Enhanced error handling and logging

## Credits

- Based on [kTAY8](https://github.com/DRPLAB-prj/kTAY8) by DRPLAB
- Inspired by [kTAMV](https://github.com/TypQxQ/kTAMV) by TypQxQ
- Community contributions and feedback
