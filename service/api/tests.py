import tempfile
from pathlib import Path

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings


class SimpleEndpointTests(TestCase):
    """Эндпоинты-сценарии: JSON, пустое тело, HTML, битый JSON, 500."""

    def test_json_ok(self):
        r = self.client.get("/api/json/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"ok": True, "users": ["alice", "bob"]})

    def test_empty_returns_204(self):
        r = self.client.get("/api/empty/")
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.content, b"")

    def test_html_is_not_json(self):
        r = self.client.get("/api/html/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["Content-Type"])
        self.assertEqual(r.content, b"<html>oops</html>")

    def test_invalid_json_body(self):
        r = self.client.get("/api/invalid-json/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("application/json", r.headers["Content-Type"])
        self.assertEqual(r.content, b"{not json")

    def test_server_error_json(self):
        r = self.client.get("/api/error/")
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json(), {"error": "boom"})

    def test_payload_size(self):
        r = self.client.get("/api/payload/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"x" * 1024)


class EchoTests(TestCase):
    """Echo: GET-параметры, JSON и form для POST/PUT/PATCH/DELETE."""

    def test_get_args(self):
        r = self.client.get("/api/echo/", {"q": "1"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"method": "GET", "args": {"q": "1"}})

    def test_post_json_returns_201(self):
        r = self.client.post(
            "/api/echo/", data='{"name": "a"}', content_type="application/json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json(), {"method": "POST", "data": {"name": "a"}})

    def test_post_form(self):
        r = self.client.post("/api/echo/", data={"x": "1"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json(), {"method": "POST", "data": {"x": "1"}})

    def test_post_invalid_json_returns_400(self):
        r = self.client.post("/api/echo/", data="{bad", content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), {"error": "invalid json"})

    def test_put_json(self):
        r = self.client.put("/api/echo/", data='{"ok": 1}', content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"method": "PUT", "data": {"ok": 1}})

    def test_patch_json(self):
        r = self.client.patch("/api/echo/", data='{"ok": 2}', content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"method": "PATCH", "data": {"ok": 2}})

    def test_delete_no_body(self):
        r = self.client.delete("/api/echo/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"method": "DELETE", "data": None})

    def test_post_json_and_form_is_form(self):
        # Django-клиент шлёт dict как form; JSON-поле не смешивается
        r = self.client.post("/api/echo/", data={"a": "1"})
        self.assertEqual(r.json()["data"], {"a": "1"})


class AvailabilityTests(TestCase):
    """Сценарии is_url_available: 200, редирект, 405 на HEAD, 500, HEAD работает."""

    def test_ping_head_and_get(self):
        self.assertEqual(self.client.get("/api/ping/").status_code, 200)
        self.assertEqual(self.client.head("/api/ping/").status_code, 200)

    def test_redirect_to_ping(self):
        r = self.client.get("/api/redirect/")
        self.assertEqual(r.status_code, 302)
        r = self.client.get("/api/redirect/", follow=True)
        self.assertEqual(r.status_code, 200)

    def test_head_only_405_on_head_200_on_get(self):
        self.assertEqual(self.client.head("/api/head-only/").status_code, 405)
        self.assertEqual(self.client.get("/api/head-only/").status_code, 200)

    def test_error_is_500_on_head_too(self):
        self.assertEqual(self.client.head("/api/error/").status_code, 500)


class UploadDownloadTests(TestCase):
    """upload_file / download_file: multipart с JSONData и streaming-отдача."""

    def setUp(self):
        # изолированный MEDIA_ROOT, чтобы тесты не засоряли service/media/
        tmp = tempfile.mkdtemp()
        override = override_settings(MEDIA_ROOT=Path(tmp))
        override.enable()
        self.addCleanup(override.disable)

    def _upload(self, name="f.bin", content=b"hello", meta='{"filename": "f.bin", "tags": ["t1"]}'):
        return self.client.post(
            "/api/upload/",
            {"file": SimpleUploadedFile(name, content), "JSONData": meta},
        )

    def test_upload_ok(self):
        r = self._upload()
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertEqual(body["ok"], 1)
        self.assertEqual(body["filename"], "f.bin")
        self.assertEqual(body["size"], 5)
        self.assertEqual(body["tags"], ["t1"])
        self.assertTrue(default_storage.exists(f"uploads/{body['stored_as'].split('/')[-1]}"))

    def test_upload_missing_file(self):
        r = self.client.post("/api/upload/", {"JSONData": "{}"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("file", r.json()["error"])

    def test_upload_missing_meta(self):
        r = self.client.post("/api/upload/", {"file": SimpleUploadedFile("f.bin", b"x")})
        self.assertEqual(r.status_code, 400)
        self.assertIn("JSONData", r.json()["error"])

    def test_upload_invalid_meta_json(self):
        r = self.client.post(
            "/api/upload/",
            {"file": SimpleUploadedFile("f.bin", b"x"), "JSONData": "{bad"},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("JSONData", r.json()["error"])

    def test_download_roundtrip(self):
        payload = b"payload" * 100
        r = self._upload(name="big.bin", content=payload)
        self.assertEqual(r.status_code, 201)

        d = self.client.get("/api/download/big.bin/")
        self.assertEqual(d.status_code, 200)
        self.assertEqual(b"".join(d.streaming_content), payload)

    def test_download_unknown_file_is_404(self):
        r = self.client.get("/api/download/nope.bin/")
        self.assertEqual(r.status_code, 404)

    def test_payload_endpoint_download(self):
        r = self.client.get("/api/payload/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"x" * 1024)
