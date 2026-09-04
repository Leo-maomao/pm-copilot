# Changelog

## 7.0.3 - 2026-09-04

- Removed the legacy runtime environment override from the Codex plugin. It
  now resolves only the installed personal-marketplace source and launches its
  MCP bridge with Python 3, preventing stale global runtimes from being used.

## 7.0.2 - 2026-09-04

- Removed the user-visible Codex runtime-path requirement. The plugin now
  resolves its installed source checkout and starts PRD workflows through MCP.

## 7.0.1 - 2026-09-04

- Restored the local Codex plugin release hook without restoring a copied
  global runtime: version commits refresh the plugin cachebuster and reinstall
  the personal-marketplace plugin from the repository checkout.

## 7.0.0 - 2026-09-04

- Reduced PM Copilot to four PRD workflows: new PRD, implemented-feature PRD,
  scoped PRD revision, and one-or-more-source PRD composition.
- Kept the local PRD manager, verified frontend figures, the Codex plugin, and
  on-demand multi-agent evidence and review work.
- Removed legacy provider adapters, global-runtime distribution, standalone UI
  delivery, generic PM artifacts, evaluation portfolios, and historical
  compatibility paths.
- Removed the remaining unreferenced workspace-identity and implemented-feature
  placeholder modules, obsolete standalone UI reconstruction guide, and empty
  ignored runtime directories.
