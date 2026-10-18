"""Stack-agnostic HTTP smoke runner used by the refactor-arch skill (stdlib only).

Usage:
    python smoke_test.py BASE_URL cases.json

cases.json: [{"method": "GET", "path": "/x", "body": {...}?, "headers": {...}?}, ...]
Prints one line per case: METHOD PATH STATUS BODY_PREVIEW. Exit code 1 if any request
failed at the network level or returned a 5xx.
"""
import json
import sys
import urllib.error
import urllib.request


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


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    base_url, cases_path = sys.argv[1].rstrip("/"), sys.argv[2]
    with open(cases_path, encoding="utf-8") as handle:
        cases = json.load(handle)

    failures = 0
    for case in cases:
        status, body = run_case(base_url, case)
        if status == "ERR" or int(status) >= 500:
            failures += 1
        preview = " ".join(body.split())[:100]
        print(f"{case['method']:6} {case['path']:45} {status}  {preview}")
    print(f"--- {len(cases)} cases, {failures} failures (5xx/network)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
