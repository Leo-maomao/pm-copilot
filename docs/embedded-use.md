# Repository Use

Keep PM Copilot as a repository tool or invoke its Codex plugin with an explicit checkout path. Host repositories are read-only evidence sources.

When PM Copilot sits inside a host repository, start the controller from its own checkout and let `project_workspace.py` resolve a run folder under the host project. Generated PRD artifacts stay in that run folder; no host code, configuration, or deployment state is changed.

Use the four supported workflows only: new PRD, implemented-feature PRD, partial PRD revision, and multi-PRD composition.
