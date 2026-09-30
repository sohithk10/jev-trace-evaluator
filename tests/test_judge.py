import json

import pytest

pytest.importorskip("langchain_typesafe")
import httpx2

from jev_eval.core import RUBRICS, normalize, policy_from
from jev_eval.judge import JevJudge


def test_real_sdk_mock_transport(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("TYPESAFE_BASE_URL", "https://untrusted.invalid")
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        assert str(request.url) == "https://api.typesafe.ai/v1/systemone"
        return httpx2.Response(200, json={
            "model": "jev-test",
            "answers": {name: {"type": "noul", "noul": 0.98} for name in RUBRICS},
        })

    judge = JevJudge()
    judge.classifier.client.close()
    judge.classifier.client = httpx2.Client(transport=httpx2.MockTransport(handler))
    try:
        result = judge(normalize({"input": "2+2?", "output": "4"}), policy_from())
        assert result == dict.fromkeys(RUBRICS, 0.98)
        assert set(seen[0]["questions"]) == set(RUBRICS)
    finally:
        judge.classifier.client.close()
