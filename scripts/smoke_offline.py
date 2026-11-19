"""Офлайн smoke-тест reqmachine без pytest/responses/сети.

Проверяет проброс ошибок HttpClient через подставную сессию:
    python3 scripts/smoke_offline.py

Нужен только python с requests и orjson.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from requests.exceptions import (
    ConnectionError as ReqConnectionError,
    HTTPError,
    InvalidSchema,
    Timeout,
)

from reqmachine import (
    HttpClient,
    HttpConnectionError,
    HttpDecodeError,
    HttpClientError,
    HttpStatusError,
    HttpTimeoutError,
)

URL = "https://example.com/api"


class FakeResponse:
    def __init__(self, content=b"", status=200, ctype="application/json"):
        self.content = content
        self.status_code = status
        self.headers = {"Content-Type": ctype}
        self.url = URL
        self.request = type("Req", (), {"method": "GET"})()

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError(f"{self.status_code}", response=self)


class _StreamResponse(FakeResponse):
    def __init__(self, resp: FakeResponse):
        super().__init__(resp.content, resp.status_code)
        self.headers = resp.headers

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def iter_content(self, chunk_size=1):
        yield self.content


class FakeSession:
    """Подставка вместо requests.Session: behavior — исключение или ответ."""

    def __init__(self, behavior):
        self.behavior = behavior

    def _act(self, behavior):
        if isinstance(behavior, Exception):
            raise behavior
        return behavior

    def request(self, method, url, **kw):
        return self._act(self.behavior)

    def get(self, url, stream=False, timeout=None):
        b = self._act(self.behavior)
        return _StreamResponse(b) if isinstance(b, FakeResponse) else b

    def post(self, url, files=None, data=None, timeout=None):
        return self._act(self.behavior)

    def head(self, url, timeout=None, allow_redirects=False):
        return self._act(self.behavior)

    def close(self):
        pass


def expect(exc_type, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc_type as e:
        print(f"OK   {exc_type.__name__}: {e}")
        return e
    except Exception as e:  # noqa: BLE001
        print(f"FAIL expected {exc_type.__name__}, got {type(e).__name__}: {e}")
        sys.exit(1)
    print(f"FAIL expected {exc_type.__name__}, no exception")
    sys.exit(1)


def main():
    client = HttpClient(verify=False)

    client.session = FakeSession(Timeout("slow"))
    expect(HttpTimeoutError, client.get, URL)
    client.session = FakeSession(ReqConnectionError("refused"))
    expect(HttpConnectionError, client.get, URL)
    client.session = FakeSession(InvalidSchema("bad"))
    expect(HttpClientError, client.get, URL)

    client.session = FakeSession(FakeResponse(status=500))
    e = expect(HttpStatusError, client.get, URL)
    assert e.status == 500 and e.url == URL, "status/url not attached"

    client.session = FakeSession(FakeResponse(content=b"", status=204))
    assert client.get(URL) is None, "empty body must stay None"
    print("OK   empty body -> None")

    client.session = FakeSession(FakeResponse(content=b'{"a": 1}'))
    assert client.get(URL) == {"a": 1}
    print("OK   json parsed")

    client.session = FakeSession(FakeResponse(content=b"<html>oops", ctype="text/html"))
    expect(HttpDecodeError, client.get, URL)
    client.session = FakeSession(FakeResponse(content=b"{not json", ctype="application/json"))
    expect(HttpDecodeError, client.get, URL)

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "f.bin"
        f.write_bytes(b"data")

        client.session = FakeSession(FakeResponse(status=503))
        e = expect(HttpStatusError, client.upload_file, URL, f)
        assert e.status == 503
        client.session = FakeSession(ReqConnectionError("nope"))
        expect(HttpConnectionError, client.upload_file, URL, f)
        client.session = FakeSession(FakeResponse(status=200))
        assert client.upload_file(URL, f) is True
        print("OK   upload success")

        client.session = FakeSession(FakeResponse(status=404))
        out = Path(tmp) / "out.bin"
        e = expect(HttpStatusError, client.download_file, URL, out)
        assert e.status == 404 and not out.exists()
        client.session = FakeSession(ReqConnectionError("nope"))
        expect(HttpConnectionError, client.download_file, URL, out)
        client.session = FakeSession(FakeResponse(content=b"payload"))
        out = Path(tmp) / "sub" / "out.bin"
        assert client.download_file(URL, out) is True
        assert out.read_bytes() == b"payload"
        print("OK   download success")

    client.session = FakeSession(ReqConnectionError("down"))
    assert client.is_url_available(URL) is False
    client.session = FakeSession(FakeResponse(status=200))
    assert client.is_url_available(URL) is True
    print("OK   is_url_available bool contract")

    print("ALL SMOKE CHECKS PASSED")


if __name__ == "__main__":
    main()
