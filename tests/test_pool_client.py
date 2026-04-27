from windsurf_auth_replay import WindsurfPoolClient


class FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith("/auth/accounts"):
            return FakeResponse(502, {"error": "bad gateway"})
        if url.endswith("/dashboard/api/accounts"):
            return FakeResponse(
                200,
                {"accounts": [{"email": "legacy@example.com", "status": "active"}]},
            )
        raise AssertionError(url)


def test_list_accounts_falls_back_to_dashboard_when_auth_endpoint_fails():
    session = FakeSession()
    client = WindsurfPoolClient(
        base_url="http://pool.example",
        session=session,
        dashboard_password="secret",
    )

    accounts = client.list_accounts()

    assert accounts == [{"email": "legacy@example.com", "status": "active"}]
    assert session.calls[0][0].endswith("/auth/accounts")
    assert session.calls[1][0].endswith("/dashboard/api/accounts")
