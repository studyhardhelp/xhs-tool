# xhs-tool

Codex skill for authorized Xiaohongshu note research, normalization, and report generation.

## Python Compatibility

The command-line tools support Python 3.9 through current Python 3 releases. Python
3.0-3.8 are not supported because current browser, spreadsheet, and HTTP dependencies
no longer install reliably on those end-of-life versions.

Create the local environment with any Python 3.9+ interpreter:

```bash
PYTHON_BIN=python3 bash scripts/bootstrap_env.sh
```

If `python3` points to an older interpreter, provide an explicit executable, for example:

```bash
PYTHON_BIN=/path/to/python3.9 bash scripts/bootstrap_env.sh
```

See `SKILL.md` for workflows and command examples.
