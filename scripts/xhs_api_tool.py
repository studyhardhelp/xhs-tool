#!/usr/bin/env python3
import argparse
import inspect
import json
import os
import stat
import sys
from pathlib import Path

from xhs_security import write_private_json


SCRIPT_DIR = Path(__file__).resolve().parent
RUNTIME_ROOT = SCRIPT_DIR / "runtime" / "spider_xhs_core"
ORIGINAL_CWD = Path.cwd()
DEFAULT_HTTP_TIMEOUT = 20.0
ALLOWED_METHODS = {
    "pc": {
        "get_homefeed_all_channel",
        "get_homefeed_recommend_by_num",
        "get_note_info",
        "get_note_out_comment",
        "get_search_keyword",
        "get_user_info",
        "get_user_note_info",
        "get_user_self_info2",
        "search_note",
        "search_some_note",
        "search_some_user",
        "search_user",
    }
}


def _read_json_arg(raw_params, raw_params_file, params_stdin=False):
    provided = sum(bool(value) for value in (raw_params, raw_params_file, params_stdin))
    if provided > 1:
        raise ValueError("Use exactly one of --params, --params-file, or --params-stdin.")
    if raw_params_file:
        path = Path(raw_params_file)
        if not path.is_absolute():
            path = ORIGINAL_CWD / path
        if os.name == "posix":
            try:
                mode = stat.S_IMODE(path.stat().st_mode)
            except OSError as exc:
                raise ValueError(f"Cannot inspect --params-file permissions: {exc}") from exc
            if mode & 0o077:
                raise PermissionError("--params-file must not be readable or writable by group/other users (use mode 0600).")
        return json.loads(path.read_text(encoding="utf-8"))
    if raw_params:
        payload = json.loads(raw_params)
        if _contains_secret(payload):
            raise ValueError("Secret-bearing payloads must use --params-stdin or a protected --params-file.")
        return payload
    if params_stdin:
        content = sys.stdin.read()
        return json.loads(content) if content.strip() else {}
    return {}


def _contains_secret(value):
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            if any(part in normalized_key for part in ("authorization", "cookie", "session", "token")):
                return True
            if _contains_secret(item):
                return True
    elif isinstance(value, list):
        return any(_contains_secret(item) for item in value)
    return False


def _runtime_error(exc):
    message = (
        "Failed to initialize the vendored XHS runtime. "
        "Run 'bash scripts/bootstrap_env.sh' from the xhs-tool directory. "
        f"Original error: {exc}"
    )
    raise RuntimeError(message) from exc


def _configure_runtime():
    node_modules = SCRIPT_DIR / "node_modules"
    existing_node_path = os.environ.get("NODE_PATH")
    if node_modules.exists():
        os.environ["NODE_PATH"] = str(node_modules)
        if existing_node_path:
            os.environ["NODE_PATH"] += os.pathsep + existing_node_path
    os.chdir(RUNTIME_ROOT)
    runtime_path = str(RUNTIME_ROOT)
    if runtime_path not in sys.path:
        sys.path.insert(0, runtime_path)


def _configure_http_timeout():
    import requests

    session_class = requests.sessions.Session
    if getattr(session_class, "_xhs_timeout_configured", False):
        return
    original_request = session_class.request
    try:
        timeout = float(os.environ.get("XHS_HTTP_TIMEOUT", DEFAULT_HTTP_TIMEOUT))
    except ValueError as exc:
        raise ValueError("XHS_HTTP_TIMEOUT must be a number of seconds.") from exc
    if timeout <= 0 or timeout > 120:
        raise ValueError("XHS_HTTP_TIMEOUT must be greater than 0 and at most 120 seconds.")

    def request_with_timeout(self, *args, **kwargs):
        kwargs.setdefault("timeout", timeout)
        return original_request(self, *args, **kwargs)

    session_class.request = request_with_timeout
    session_class._xhs_timeout_configured = True


def _load_namespaces(namespace=None):
    _configure_runtime()
    try:
        _configure_http_timeout()
        from xhs_utils.cookie_util import trans_cookies
        namespaces = {}
        if namespace in (None, "pc"):
            from apis.xhs_pc_apis import XHS_Apis
            namespaces["pc"] = {
                "class": XHS_Apis,
                "trans_cookies": trans_cookies,
            }
    except Exception as exc:
        _runtime_error(exc)
    return namespaces


def _format_signature(func):
    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())
    if parameters and parameters[0].name == "self":
        parameters = parameters[1:]
    return "(" + ", ".join(str(parameter) for parameter in parameters) + ")"


def _list_methods(namespaces):
    result = {}
    for namespace, config in namespaces.items():
        cls = config["class"]
        methods = []
        for name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name not in ALLOWED_METHODS.get(namespace, set()):
                continue
            methods.append(
                {
                    "name": name,
                    "signature": _format_signature(func),
                }
            )
        result[namespace] = sorted(methods, key=lambda item: item["name"])
    return result


def _resolve_callable(namespaces, namespace, method):
    if namespace not in namespaces:
        raise KeyError(f"Unknown namespace: {namespace}")
    if method not in ALLOWED_METHODS.get(namespace, set()):
        raise PermissionError(f"Method is not allowed by the research-only API policy: {namespace}.{method}")
    cls = namespaces[namespace]["class"]
    func = getattr(cls, method, None)
    if func is None or method.startswith("_"):
        raise KeyError(f"Unknown method: {namespace}.{method}")
    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())
    if parameters and parameters[0].name == "self":
        target = getattr(cls(), method)
    else:
        target = func
    return target, signature


def _normalize_payload(namespaces, namespace, method, signature, payload):
    if not isinstance(payload, dict):
        raise TypeError("Payload must be a JSON object.")

    payload = dict(payload)
    _validate_method_payload(method, payload)
    trans_cookies = namespaces[namespace]["trans_cookies"]
    parameter_names = list(signature.parameters.keys())
    if parameter_names and parameter_names[0] == "self":
        parameter_names = parameter_names[1:]

    expects_cookies = "cookies" in parameter_names

    if expects_cookies and "cookies" not in payload and isinstance(payload.get("cookies_str"), str):
        payload["cookies"] = trans_cookies(payload["cookies_str"])
    if expects_cookies and isinstance(payload.get("cookies"), str):
        payload["cookies"] = trans_cookies(payload["cookies"])
    return payload


def _validate_method_payload(method, payload):
    if payload.get("proxies"):
        raise PermissionError("Proxy configuration is not allowed by the research API policy.")
    if "require_num" in payload:
        value = int(payload["require_num"])
        if value < 1 or value > 50:
            raise ValueError("require_num must be between 1 and 50.")
    if method in {"search_note", "search_user"} and "page" in payload:
        page = int(payload["page"])
        if page < 1 or page > 5:
            raise ValueError("page must be between 1 and 5.")


def _write_output(path_value, data):
    path = Path(path_value)
    if not path.is_absolute():
        path = ORIGINAL_CWD / path
    write_private_json(path, data)


def main():
    parser = argparse.ArgumentParser(description="Call vendored XHS APIs from the xhs-apis skill.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available namespaces and methods.")
    list_parser.add_argument("--namespace", choices=sorted(ALLOWED_METHODS), help="Only load and list one namespace.")
    list_parser.add_argument("--out", help="Write the method list to a JSON file.")

    call_parser = subparsers.add_parser("call", help="Call a namespace method.")
    call_parser.add_argument("namespace", choices=sorted(ALLOWED_METHODS))
    call_parser.add_argument("method")
    call_parser.add_argument("--params", help="Inline JSON payload.")
    call_parser.add_argument("--params-file", help="Path to a JSON payload file.")
    call_parser.add_argument("--params-stdin", action="store_true", help="Read a JSON payload from standard input. Required for secret-bearing payloads.")
    call_parser.add_argument("--out", help="Write the result to a JSON file.")

    args = parser.parse_args()
    try:
        namespaces = _load_namespaces(getattr(args, "namespace", None) if args.command == "list" else args.namespace)
    except Exception as exc:
        response = {
            "error": str(exc),
        }
        print(json.dumps(response, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    if args.command == "list":
        result = _list_methods(namespaces)
        if args.out:
            _write_output(args.out, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    try:
        payload = _read_json_arg(args.params, args.params_file, args.params_stdin)
        target, signature = _resolve_callable(namespaces, args.namespace, args.method)
        payload = _normalize_payload(namespaces, args.namespace, args.method, signature, payload)
        result = target(**payload)
        if isinstance(result, (list, tuple)) and len(result) >= 2 and result[0] is False:
            raise RuntimeError(str(result[1]))
        response = {
            "namespace": args.namespace,
            "method": args.method,
            "result": result,
        }
    except Exception as exc:
        response = {
            "namespace": args.namespace,
            "method": args.method,
            "error": str(exc),
        }
        print(json.dumps(response, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    if args.out:
        _write_output(args.out, response)
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
