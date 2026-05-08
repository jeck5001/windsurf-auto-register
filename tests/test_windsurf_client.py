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
            return FakeResponse(
                200,
                encode_proto_string(1, "devin-session-token$session-token-plain")
                + encode_proto_string(4, "account_123")
                + encode_proto_string(5, "org_456"),
            )
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
    assert session.calls[0][1]["data"] == b""


def test_exchange_for_session_context_extracts_account_and_org_ids():
    session = FakeSession()
    client = WindsurfClient(
        base_url="https://windsurf.com",
        session=session,
    )

    details = client.exchange_for_session_context("auth1_plain_token")

    assert details["session_token"] == "devin-session-token$session-token-plain"
    assert details["account_id"] == "account_123"
    assert details["primary_org_id"] == "org_456"


def test_get_one_time_token_sends_context_headers_and_empty_body():
    session = FakeSession()
    client = WindsurfClient(
        base_url="https://windsurf.com",
        session=session,
    )

    ott = client.get_one_time_token(
        "devin-session-token$session-token-plain",
        auth_token="auth1_plain_token",
        account_id="account_123",
        primary_org_id="org_456",
    )

    assert ott == "ott$one-time-token-plain"
    assert session.calls[0][0].endswith("/GetOneTimeAuthToken")
    assert session.calls[0][1]["headers"]["X-Devin-Session-Token"] == "devin-session-token$session-token-plain"
    assert session.calls[0][1]["headers"]["X-Devin-Auth1-Token"] == "auth1_plain_token"
    assert session.calls[0][1]["headers"]["X-Devin-Account-Id"] == "account_123"
    assert session.calls[0][1]["headers"]["X-Devin-Primary-Org-Id"] == "org_456"
    assert "Authorization" not in session.calls[0][1]["headers"]
    assert session.calls[0][1]["data"] == b""
