import json

from services import geocoding


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.content


def test_geocode_city_queries_only_city_and_state_and_uses_app_user_agent(monkeypatch):
    observed = {}

    def fake_urlopen(request, timeout):
        observed["url"] = request.full_url
        observed["user_agent"] = request.get_header("User-agent")
        observed["timeout"] = timeout
        return FakeResponse(json.dumps([{"lat": "-1.4558", "lon": "-48.4902"}]).encode())

    monkeypatch.setattr(geocoding, "urlopen", fake_urlopen)
    monkeypatch.setattr(geocoding.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(geocoding.time, "monotonic", lambda: 10.0)
    monkeypatch.setattr(geocoding, "_LAST_REQUEST_AT", 0.0)

    assert geocoding.geocode_city("Belém", "PA") == (-1.4558, -48.4902)
    assert "city=Bel%C3%A9m" in observed["url"]
    assert "state=Par%C3%A1" in observed["url"]
    assert "country=Brasil" in observed["url"]
    assert "name" not in observed["url"]
    assert observed["user_agent"].startswith("MissingPersonsPrototype/")
    assert observed["timeout"] == 10


def test_geocode_city_returns_none_for_no_result_or_outside_brazil(monkeypatch):
    responses = iter(([], [{"lat": "40.7128", "lon": "-74.0060"}]))

    def fake_urlopen(_request, timeout):
        return FakeResponse(json.dumps(next(responses)).encode())

    monkeypatch.setattr(geocoding, "urlopen", fake_urlopen)
    monkeypatch.setattr(geocoding.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(geocoding.time, "monotonic", lambda: 10.0)
    monkeypatch.setattr(geocoding, "_LAST_REQUEST_AT", 0.0)

    assert geocoding.geocode_city("Cidade inexistente", "PA") is None
    assert geocoding.geocode_city("Cidade", "PA") is None
