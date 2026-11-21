import json
from dataclasses import dataclass
from pathlib import Path

import pytest
import responses
from requests.exceptions import ConnectionError as ReqConnectionError
from requests.exceptions import InvalidSchema, Timeout

from reqmachine import (
    HttpClient,
    HttpClientError,
    HttpConnectionError,
    HttpDecodeError,
    HttpStatusError,
    HttpTimeoutError,
)

URL = "http://127.0.0.1:8000/"


@dataclass
class GetJson:
    __test__ = False
    ok: bool | int


@dataclass
class PostJson:
    __test__ = False
    id: int


# ─────────────────────────── Фикстуры ───────────────────────────


@pytest.fixture
def client():
    c = HttpClient(verify=False, retries=0)  # без ретраев — быстрее и детерминированно
    yield c
    c.close()


# ─────────────────────────── _request / get ───────────────────────────


@responses.activate
def test_get_json_returns_parsed(client):
    responses.add(responses.GET, URL, json={"ok": True}, status=200)
    val = client.get(URL, GetJson)
    assert val == GetJson(ok=True)


@responses.activate
def test_get_empty_body_returns_none(client):
    responses.add(responses.GET, URL, body=b"", status=204)
    assert client.get(URL, GetJson) is None


@responses.activate
def test_get_html_returns_bytes(client):
    responses.add(
        responses.GET,
        URL,
        body="<html>oops</html>",
        status=200,
        content_type="text/html",
    )
    result = client.get(URL, GetJson)

    assert isinstance(result, bytes)
    assert result == b"<html>oops</html>"


@responses.activate
def test_get_invalid_json_raises_decode_error(client):
    responses.add(
        responses.GET,
        URL,
        body="{not json",
        status=200,
        content_type="application/json",
    )
    with pytest.raises(HttpDecodeError):
        client.get(URL, GetJson)


@responses.activate
def test_get_http_error_raises_status_error(client):
    responses.add(responses.GET, URL, json={"error": "boom"}, status=500)
    with pytest.raises(HttpStatusError) as ei:
        client.get(URL, GetJson)
    assert ei.value.status == 500
    assert ei.value.url == URL


@responses.activate
def test_get_connection_error_raises_connection_error(client):
    responses.add(
        responses.GET,
        URL,
        body=ReqConnectionError("refused"),
    )
    with pytest.raises(HttpConnectionError):
        client.get(URL, GetJson)


@responses.activate
def test_get_timeout_raises_timeout_error(client):
    responses.add(responses.GET, URL, body=Timeout("slow"))
    with pytest.raises(HttpTimeoutError):
        client.get(URL, GetJson)


@responses.activate
def test_get_other_request_error_raises_client_error(client):
    responses.add(responses.GET, URL, body=InvalidSchema("bad url"))
    with pytest.raises(HttpClientError):
        client.get(URL, GetJson)


def test_request_rejects_stream(client):
    with pytest.raises(ValueError):
        client._request("GET", URL, GetJson, stream=True)


# ─────────────────────────── post / put / patch / delete ───────────────────────────


@responses.activate
def test_post_json(client):
    responses.add(responses.POST, URL, json={"id": 1}, status=201)
    r = client.post(URL, PostJson, json={"name": "a"})
    assert r == PostJson(id=1)

    body = responses.calls[0].request.body
    assert isinstance(body, (bytes, bytearray, str)), "Ожидалось тело в виде bytes/str"
    sent = json.loads(body)
    assert sent == {"name": "a"}


@responses.activate
def test_post_data(client):
    responses.add(responses.POST, URL, json={}, status=200)
    client.post(URL, PostJson, data={"x": "1"})
    assert responses.calls[0].request.body == "x=1"


def test_post_json_and_data_conflict(client):
    with pytest.raises(ValueError):
        client.post(URL, PostJson, json={"a": 1}, data={"b": 2})


@responses.activate
def test_put_patch_delete(client):
    responses.add(responses.PUT, URL, json={"ok": 1})
    responses.add(responses.PATCH, URL, json={"ok": 2})
    responses.add(responses.DELETE, URL, json={"ok": 3})
    assert client.put(URL, GetJson, json={}) == GetJson(ok=1)
    assert client.patch(URL, GetJson, json={}) == GetJson(ok=2)
    assert client.delete(URL, GetJson) == GetJson(ok=3)


# ─────────────────────────── is_url_available ───────────────────────────


@responses.activate
def test_is_url_available_true(client):
    responses.add(responses.HEAD, URL, status=200)
    assert client.is_url_available(URL) is True


@responses.activate
def test_is_url_available_redirect_ok(client):
    responses.add(responses.HEAD, URL, status=302, headers={"Location": URL + "/next"})
    responses.add(responses.HEAD, URL + "/next", status=200)
    assert client.is_url_available(URL) is True


@responses.activate
def test_is_url_available_405_falls_back_to_get(client):
    responses.add(responses.HEAD, URL, status=405)
    responses.add(responses.GET, URL, status=200, body=b"ok")
    assert client.is_url_available(URL) is True


@responses.activate
def test_is_url_available_false_on_500(client):
    responses.add(responses.HEAD, URL, status=500)
    assert client.is_url_available(URL) is False


@responses.activate
def test_is_url_available_false_on_connection_error(client):
    responses.add(responses.HEAD, URL, body=ReqConnectionError("nope"))
    assert client.is_url_available(URL) is False


# ─────────────────────────── upload_file ───────────────────────────


def _make_file(tmp_path: Path, content: bytes = b"hello") -> Path:
    f = tmp_path / "f.bin"
    f.write_bytes(content)
    return f


META_FIELD = "JSONData"  #  HttpClient.upload_file


@responses.activate
def test_upload_file_ok(client, tmp_path):
    responses.add(responses.POST, URL, json={"ok": 1}, status=200)
    f = _make_file(tmp_path)
    assert client.upload_file(URL, f, key=META_FIELD, meta={"data": "hello"}) is True

    req = responses.calls[0].request
    # Проверяем, что тело — это bytes, и ty это учтёт
    assert isinstance(req.body, bytes), "Ожидалось тело в виде bytes"
    assert b'filename="f.bin"' in req.body  # multipart
    assert b'"data"' in req.body


@responses.activate
def test_upload_file_http_error_raises(client, tmp_path):
    responses.add(responses.POST, URL, json={"error": "x"}, status=500)
    with pytest.raises(HttpStatusError) as ei:
        client.upload_file(URL, _make_file(tmp_path))
    assert ei.value.status == 500


@responses.activate
def test_upload_file_connection_error_raises(client, tmp_path):
    responses.add(responses.POST, URL, body=ReqConnectionError("nope"))
    with pytest.raises(HttpConnectionError):
        client.upload_file(URL, _make_file(tmp_path))


# ─────────────────────────── download_file ───────────────────────────


@responses.activate
def test_download_file_ok(client, tmp_path):
    payload = b"x" * 1024
    responses.add(responses.GET, URL, body=payload, status=200)
    out = tmp_path / "sub" / "f.bin"  # проверяем создание родителя
    assert client.download_file(URL, out) is True
    assert out.read_bytes() == payload


@responses.activate
def test_download_file_http_error_raises(client, tmp_path):
    responses.add(responses.GET, URL, body=b"nope", status=404)
    out = tmp_path / "f.bin"
    with pytest.raises(HttpStatusError) as ei:
        client.download_file(URL, out)
    assert ei.value.status == 404
    assert not out.exists()


@responses.activate
def test_download_file_connection_error_raises(client, tmp_path):
    responses.add(responses.GET, URL, body=ReqConnectionError("nope"))
    with pytest.raises(HttpConnectionError):
        client.download_file(URL, tmp_path / "f.bin")


@responses.activate
def test_download_file_iterates_chunks(client, tmp_path, monkeypatch):
    """Проверяем, что файл пишется по чанкам, а не целиком."""
    payload = b"a" * 10
    responses.add(responses.GET, URL, body=payload, status=200)

    writes = []
    real_open = Path.open

    def spy_open(self, *a, **kw):
        f = real_open(self, *a, **kw)
        if "wb" in a or kw.get("mode") == "wb":
            orig_write = f.write
            f.write = lambda b: (writes.append(len(b)), orig_write(b))[1]
        return f

    monkeypatch.setattr(Path, "open", spy_open)
    monkeypatch.setattr(client, "chunk_size", 3)

    assert client.download_file(URL, tmp_path / "f.bin") is True
    assert sum(writes) == len(payload)
    assert all(w <= 3 for w in writes)


# ─────────────────────────── context manager ───────────────────────────


def test_context_manager_closes_session(monkeypatch):
    closed = {"v": False}
    with HttpClient(verify=False) as c:
        monkeypatch.setattr(c.session, "close", lambda: closed.update(v=True))
    assert closed["v"] is True
