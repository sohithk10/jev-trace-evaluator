import json
import threading
import urllib.request
import urllib.error

import pytest

from jev_eval.core import InputError
from jev_eval.web import audit, make_server


def test_audit():
    report = audit({"traces": [{"input": "hello", "output": "hello"}], "allowed_tools": []})
    assert report["summary"] == {"pass": 0, "fail": 0, "review": 1}
    assert "hello" not in json.dumps(report)


def test_invalid_batch():
    with pytest.raises(InputError):
        audit({"traces": [], "allowed_tools": []})


def test_http_boundaries():
    with make_server(0) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urllib.request.urlopen(base) as response:
                page = response.read().decode()
                assert "Trace Observatory" in page
                assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
            token = page.split('name="jev-token" content="')[1].split('"')[0]
            body = json.dumps({"traces": [{"input": "x", "output": "y"}], "allowed_tools": []}).encode()
            bad = urllib.request.Request(base + "/api/evaluate", data=body)
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(bad)
            assert error.value.code == 403
            good = urllib.request.Request(base + "/api/evaluate", data=body, headers={
                "Content-Type": "application/json", "Origin": base, "X-JEV-Token": token})
            with urllib.request.urlopen(good) as response:
                assert json.load(response)["summary"]["review"] == 1
        finally:
            server.shutdown()
            thread.join()
