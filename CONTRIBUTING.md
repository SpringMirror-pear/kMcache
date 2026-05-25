# Contributing to kmcache

Thanks for contributing to `kmcache`.

## Before You Start

- open an issue first for large features, API changes, or behavioral changes
- keep changes scoped and reviewable
- do not include generated artifacts such as `dist/` or `__pycache__/`

## Branching

Base branch rules:

- branch from `develop` for normal work
- branch from `main` only for urgent `hotfix/*`
- use `release/0.x` only for release hardening

Recommended branch names:

- `feature/<scope>-<name>`
- `fix/<scope>-<name>`
- `docs/<name>`
- `refactor/<scope>-<name>`
- `test/<scope>-<name>`
- `chore/<name>`
- `hotfix/<name>`

## Commit Convention

Use:

```text
type(scope): short summary
```

Examples:

```text
feat(manager): add batch cache API
fix(redis): prevent duplicate refresh lock path
docs(readme): clarify branch strategy
test(config): cover env-based settings
```

Recommended types:

- `feat`
- `fix`
- `docs`
- `refactor`
- `test`
- `chore`
- `perf`
- `ci`
- `build`
- `revert`

## Development Checks

Run the repository checks before opening a pull request:

```bash
python scripts/check.py
```

At minimum, make sure:

- tests pass
- new behavior is covered by tests when appropriate
- README or changelog is updated for user-facing changes

## Pull Requests

- keep one logical change per pull request
- include context, behavior changes, and test coverage notes
- prefer squash merge unless preserving commit history is important
- avoid mixing refactors with behavior changes unless necessary

## Release Notes

If your change affects public APIs, packaging, configuration, or runtime behavior, update:

- `README.md`
- `README.zh-CN.md`
- `CHANGELOG.md`
- `CHANGELOG.zh-CN.md`
