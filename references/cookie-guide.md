# Cookie Guide

Use a browser session that the user controls.

For ordinary users, prefer the local browser-login helper:

```bash
bash scripts/bootstrap_env.sh
.venv/bin/python scripts/xhs_auth.py login --channel chrome --verbose --wait-auto
.venv/bin/python scripts/xhs_auth.py status --json
```

The helper uses an installed Chrome/Edge/Chromium by default, so the user does not wait for a browser download. Prefer `--channel chrome` when Chrome is installed.
If no controllable installed browser is found, stop and ask the user to install Chrome/Edge/Chromium or explicitly allow the optional skill-local Playwright Chromium fallback.

```bash
.venv/bin/python scripts/xhs_auth.py login --channel chrome --wait-auto
.venv/bin/python scripts/xhs_auth.py login --executable-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --wait-auto
.venv/bin/python scripts/xhs_auth.py login --browser-mode auto --auto-install-browser --wait-auto
```

The system default browser should not be used for normal skill auth because automatic auth export requires a Playwright-controlled Chromium-family browser.
The optional fallback downloads Chromium into `<skill-dir>/.browsers/`, not as a system Chrome/Edge installation.

The helper opens a visible browser, waits for the user to log in, extracts only Xiaohongshu cookies, and stores them in `<skill-dir>/.secrets/xhs_cookie.txt`.
It also writes non-secret metadata to `<skill-dir>/.secrets/xhs_auth_meta.json`, including saved time, key-cookie presence, and latest live API check status.
By default, `login` and `status` do not print cookie values. Use `--show-redacted` only for local debugging when the user explicitly asks.

When guiding a non-technical user in Codex, do not ask them to copy cookies manually. Say:

```text
请在弹出的小红书页面完成登录, 登录成功后我会自动继续采集。
```

Manual fallback:

1. Open Xiaohongshu Web and sign in.
2. Open browser DevTools.
3. Go to Network, select Fetch/XHR, then refresh or perform a search.
4. Choose a real `GET` or `POST` request under `edith.xiaohongshu.com`.
5. Ignore `OPTIONS` preflight requests.
6. Copy the `cookie` request header value.
7. Store it locally as `XHS_COOKIE` without placing it in shell history.

Example:

```bash
read -s XHS_COOKIE
export XHS_COOKIE
```

Do not paste cookies into source files, commit history, shared logs, or generated reports.
Do not display raw or redacted cookies in Codex conversation unless explicitly requested for debugging.
Do not add automated login, stealth, CAPTCHA bypass, or browser fingerprint evasion to this skill.
