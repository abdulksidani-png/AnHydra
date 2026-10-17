import httpx

from tardiscreen import explain as e


DRIVERS = [("low_complexity", 0.9), ("gly_ser_his", -0.4)]


def test_prompt_distinguishes_contributions_from_measurements():
    prompt = e.build_prompt(0.81, "protective", None, DRIVERS)
    assert "NOT raw measurements" in prompt
    assert "not the ESM-2 score" in prompt
    assert "gly_ser_his: -0.400" in prompt


def test_success_uses_configured_model_and_ignores_thoughts(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    def post(url, **kwargs):
        assert url == e.API_URL.format(model=e.GEMINI_MODEL)
        assert kwargs["headers"]["x-goog-api-key"] == "test-key"
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [
            {"thought": True, "text": "internal"}, {"text": "Family signal; test experimentally."}
        ]}}]}, request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "post", post)
    assert e.explain(0.81, "protective", None, DRIVERS) == "Family signal; test experimentally."


def test_error_falls_back_without_logging_secret(monkeypatch, capsys):
    monkeypatch.setenv("GEMINI_API_KEY", "private-test-key")
    def post(*args, **kwargs):
        raise httpx.ReadTimeout("private-test-key")
    monkeypatch.setattr(httpx, "post", post)
    assert e.explain(0.81, "protective", None, DRIVERS) == e._offline_readout(0.81, "protective", DRIVERS)
    output = capsys.readouterr().out
    assert "ReadTimeout" in output
    assert "private-test-key" not in output


def test_blocked_response_falls_back(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "post", lambda url, **kw: httpx.Response(
        200, json={"candidates": []}, request=httpx.Request("POST", url)))
    assert e.explain(0.81, "protective", None, DRIVERS) == e._offline_readout(0.81, "protective", DRIVERS)
