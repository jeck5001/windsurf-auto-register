from windsurf_auth_replay import WindsurfClient, encode_proto_string


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
    def __init__(self, responder=None):
        self.calls = []
        self.responder = responder

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.responder is not None:
            return self.responder(url, kwargs)
        if url.endswith("/WindsurfPostAuth"):
            return FakeResponse(200, b"devin-session-token$session-token-plain")
        if url.endswith("/GetOneTimeAuthToken"):
            return FakeResponse(200, b"ott$one-time-token-plain")
        raise AssertionError(url)


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


def test_get_one_time_token_sends_session_headers():
    session = FakeSession()
    client = WindsurfClient(
        base_url="https://windsurf.com",
        session=session,
    )

    ott = client.get_one_time_token(
        "devin-session-token$session-token-plain",
        auth_token="auth1_plain_token",
    )

    assert ott == "ott$one-time-token-plain"
    assert session.calls[0][0].endswith("/GetOneTimeAuthToken")
    assert session.calls[0][1]["headers"]["X-Devin-Session-Token"] == "devin-session-token$session-token-plain"
    assert session.calls[0][1]["headers"]["X-Devin-Auth1-Token"] == "auth1_plain_token"
    assert session.calls[0][1]["headers"]["Authorization"] == "Bearer auth1_plain_token"
    assert session.calls[0][1]["data"] == encode_proto_string(1, "auth1_plain_token")


def test_get_one_time_token_retries_alternate_variants():
    def responder(url, kwargs):
        if not url.endswith("/GetOneTimeAuthToken"):
            raise AssertionError(url)
        if (
            kwargs["headers"]["X-Devin-Session-Token"] == "devin-session-token$session-token-plain"
            and kwargs["headers"]["X-Devin-Auth1-Token"] == "auth1_plain_token"
            and kwargs["headers"]["Authorization"] == "Bearer devin-session-token$session-token-plain"
            and kwargs["data"] == encode_proto_string(1, "devin-session-token$session-token-plain")
        ):
            return FakeResponse(200, b"ott$one-time-token-plain")
        return FakeResponse(401, b"missing auth token")

    session = FakeSession(responder=responder)
    client = WindsurfClient(
        base_url="https://windsurf.com",
        session=session,
    )

    ott = client.get_one_time_token(
        "devin-session-token$session-token-plain",
        auth_token="auth1_plain_token",
    )

    assert ott == "ott$one-time-token-plain"
    assert len(session.calls) >= 2
