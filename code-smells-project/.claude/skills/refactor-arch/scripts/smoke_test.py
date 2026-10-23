"""Stack-agnostic HTTP smoke runner used by the refactor-arch skill (stdlib only).

Usage:
    python smoke_test.py BASE_URL cases.json

cases.json: [{"method": "GET", "path": "/x", "body": {...}?, "headers": {...}?,
              "capture": {"var": "json_field"}?, "expect": 403?}, ...]

- "capture" stores a top-level field of the JSON response (e.g. a login token) in a variable;
  "{{var}}" is replaced in later paths, headers and bodies.
- "expect" asserts the status code (used for security negative cases).

Prints one line per case: METHOD PATH STATUS BODY_PREVIEW. Exit code 1 if any request failed at the
network level, returned a 5xx, or did not match its "expect".
"""
import json
import re
import sys
import urllib.error
import urllib.request

PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def substitute(value, variables):
    if isinstance(value, str):
        return PLACEHOLDER.sub(lambda match: str(variables.get(match.group(1), match.group(0))), value)
    if isinstance(value, dict):
        return {key: substitute(item, variables) for key, item in value.items()}
    if isinstance(value, list):
        return [substitute(item, variables) for item in value]
    return value


def run_case(base_url, case):
    data = json.dumps(case["body"]).encode() if "body" in case else None
    headers = {"Content-Type": "application/json", **case.get("headers", {})}
    request = urllib.request.Request(base_url + case["path"], data=data, method=case["method"], headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")
    except Exception as error:  # network failure: report, do not crash the run
        return "ERR", str(error)


def capture(body, spec, variables):
    try:
        payload = json.loads(body)
    except ValueError:
        return
    for name, field in spec.items():
        if isinstance(payload, dict) and field in payload:
            variables[name] = payload[field]


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    base_url, cases_path = sys.argv[1].rstrip("/"), sys.argv[2]
    with open(cases_path, encoding="utf-8") as handle:
        cases = json.load(handle)

    failures = 0
    variables = {}
    for raw_case in cases:
        case = substitute(raw_case, variables)
        status, body = run_case(base_url, case)
        failed = status == "ERR" or int(status) >= 500
        expected = case.get("expect")
        if expected is not None and status != expected:
            failed = True
        failures += failed
        if "capture" in case:
            capture(body, case["capture"], variables)

        preview = " ".join(body.split())[:100]
        marker = f" (expected {expected})" if expected is not None and status != expected else ""
        print(f"{case['method']:6} {raw_case['path']:45} {status}{marker}  {preview}")
    print(f"--- {len(cases)} cases, {failures} failures (5xx/network/unexpected status)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
