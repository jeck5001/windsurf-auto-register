from windsurf_auth_replay import WindsurfClient


class FakeResponse:
    def __init__(self, status_code: int, content: bytes):
        self.status_code = status_code
        self.content = content
        self.text = content.decode("utf-8", errors="ignore")

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        return None


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(200, b"devin-session-token$session-token-plain")


def test_exchange_for_session_sends_auth1_header():
    session = FakeSession()
    client = WindsurfClient(
        base_url="https://windsurf.com",
        session=session,
    )

    session_token = client.exchange_for_session("auth1_plain_token")

    assert session_token == "devin-session-token$session-token-plain"
    assert session.calls[0][0].endswith("/WindsurfPostAuth")
    assert session.calls[0][1]["headers"]["X-Devin-Auth1-Token"] == "auth1_plain_token"