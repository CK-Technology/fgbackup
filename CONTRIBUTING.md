# Contributing to fgbackup

Thanks for your interest in contributing to fgbackup! This guide covers the
basics for getting changes merged.

## Getting Started

1. Fork the repository on GitHub.
2. Clone your fork and create a feature branch from `main`:

```bash
git clone https://github.com/CK-Technology/fgbackup
cd fgbackup
git checkout -b feature/your-change
```

## Development Workflow

- Keep changes focused; one logical change per pull request.
- Match the existing code style and run the project's formatter/linter.
- Add or update tests for any behavior change.
- Update documentation under `docs/` when relevant.

## Commit Messages

Follow Conventional Commits:

```
type(scope): short description
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

## Pull Requests

Before opening a PR:

- Rebase on the latest `main`.
- Ensure the build, tests, and linters pass.
- Describe **what** changed and **why**.

## Reporting Bugs

Open an [issue](https://github.com/CK-Technology/fgbackup/issues) with steps to
reproduce, expected vs. actual behavior, and environment details.

## License

By contributing, you agree your contributions are licensed under the MIT License.
