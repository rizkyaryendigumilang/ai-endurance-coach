# Issue tracker: GitHub (with Local Markdown Fallback)

Issues and specs for this repo live as GitHub issues under `rizkyaryendigumilang/ai-endurance-coach`. When the `gh` CLI is available in the shell environment, use `gh` for all operations. When `gh` is not installed or available, fall back to local markdown issue files under `.scratch/issues/`.

## Conventions (GitHub CLI)

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --json number,title,body,labels,comments`.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Make an issue a sub-issue of a parent**: `gh issue create --parent <parent> ...`, or `gh issue edit <parent> --add-sub-issue <child>` afterwards (`gh` 2.94+). Older `gh`: `gh api --method POST repos/rizkyaryendigumilang/ai-endurance-coach/issues/<parent>/sub_issues -F sub_issue_id=<child-db-id>`. Without sub-issues, put `Part of #<parent>` at the top of the child body.
- **Blocking**: GitHub native issue dependencies. Add an edge with `gh issue create --blocked-by <n>,<n> ...` or `gh issue edit <child> --add-blocked-by <blocker>`. Older `gh`: `gh api --method POST repos/rizkyaryendigumilang/ai-endurance-coach/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`. Where dependencies are not available, fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Count open blockers**: `gh api repos/rizkyaryendigumilang/ai-endurance-coach/issues/<n> --jq .issue_dependencies_summary.blocked_by`.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: post the explanation with `gh issue comment <number> --body "..."`, then `gh issue close <number>`.

## Local Markdown Fallback (When `gh` is unavailable)

- Issues are stored as individual Markdown files in `.scratch/issues/<number>-<slug>.md`.
- File format includes YAML frontmatter with `title`, `status` (open/closed), `labels`, and `created_at`.
- List issues by globbing `.scratch/issues/*.md`.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## When a skill says "publish to the issue tracker"

Create a GitHub issue in `rizkyaryendigumilang/ai-endurance-coach` via `gh`, or write to `.scratch/issues/` if `gh` is not installed.

## When a skill says "fetch the relevant ticket"

Read it via `gh issue view <number>`, or read `.scratch/issues/<number>-*.md` if `gh` is not installed.
