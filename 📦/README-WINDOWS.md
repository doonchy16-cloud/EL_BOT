# EL Bot — Windows Package

Phase 5 produces two x64 Windows artifacts:

- `EL-Bot-Setup-0.5.0-x64.exe` — installer;
- `EL-Bot-Portable-0.5.0-x64.exe` — portable application.

## Included

- Electron desktop runtime;
- EL Bot's 44 engine sources;
- EL Bot UI and Phase-5 visual layer;
- embedded Python 3.12 runtime used by the deterministic engines;
- identity/icon assets.

## Intentionally not included

Ollama and `qwen2.5vl:7b` are external temporary intelligence providers and are not bundled into the Windows application. Their size and replaceable-provider role make them inappropriate to hide inside the EL Bot installer.

EL Bot must still launch and perform deterministic work without Ollama. Features that require local vision/AI must report an unavailable-provider state rather than pretending they succeeded.

## Source launcher

`▶️.cmd` remains the development/source launcher. Packaged users should use the installed **EL Bot** shortcut or the portable executable instead.
