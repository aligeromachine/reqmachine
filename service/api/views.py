"""
Эндпоинты, повторяющие все сценарии из тестов reqmachine:

| Сценарий клиента                    | Эндпоинт                     |
|-------------------------------------|------------------------------|
| 200 + JSON                          | GET  /api/json/              |
| пустое тело (204 -> None)           | GET  /api/empty/             |
| не-JSON ответ (HTML)                | GET  /api/html/              |
| битый JSON                          | GET  /api/invalid-json/      |
| HTTP 500 с JSON-ошибкой             | GET  /api/error/             |
| echo JSON / form / PUT / PATCH / DELETE | /api/echo/               |
| is_url_available: HEAD 200          | GET,HEAD /api/ping/          |
| is_url_available: редирект          | ANY /api/redirect/           |
| is_url_available: 405 на HEAD       | GET /api/head-only/          |
| upload_file (multipart + JSONData)  | POST /api/upload/            |
| download_file (streaming)           | GET  /api/download/<name>/   |
| фиксированный бинарный payload      | GET  /api/payload/           |
"""

import orjson
from django.core.files.storage import default_storage
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseNotAllowed,
    JsonResponse,
    QueryDict,
)
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

# ─────────────────────────── Простые ответы ───────────────────────────


@require_http_methods(["GET", "HEAD"])
def json_ok(request):
    """200 + валидный JSON (test_get_json_returns_parsed)."""
    return JsonResponse({"ok": True, "users": ["alice", "bob"]})


@require_http_methods(["GET", "HEAD"])
def empty(request):
    """204 без тела — клиент должен вернуть None (test_get_empty_body_returns_none)."""
    return HttpResponse(status=204)


@require_http_methods(["GET", "HEAD"])
def html(request):
    """200 с HTML вместо JSON — клиент бросает HttpDecodeError."""
    return HttpResponse("<html>oops</html>", content_type="text/html")


@require_http_methods(["GET", "HEAD"])
def invalid_json(request):
    """200 с content-type JSON, но битым телом — клиент бросает HttpDecodeError."""
    return HttpResponse("{not json", content_type="application/json")


@require_http_methods(["GET", "HEAD"])
def server_error(request):
    """500 с JSON-ошибкой — клиент бросает HttpStatusError (test_get_http_error_*)."""
    return JsonResponse({"error": "boom"}, status=500)


@require_http_methods(["GET", "HEAD"])
def ping(request):
    """200 на HEAD и GET (test_is_url_available_true)."""
    return HttpResponse("pong")


def head_only(request):
    """405 на HEAD, 200 на GET (test_is_url_available_405_falls_back_to_get)."""
    if request.method == "HEAD":
        return HttpResponseNotAllowed(["GET"])
    return HttpResponse("ok")


def redirect_to_ping(request):
    """302 -> /api/ping/ (test_is_url_available_redirect_ok)."""
    return redirect("/api/ping/")


@require_http_methods(["GET", "HEAD"])
def fixed_payload(request):
    """Бинарный payload фиксированного размера для проверки скачивания по чанкам."""
    payload = b"x" * 1024
    return HttpResponse(
        payload,
        content_type="application/octet-stream",
        headers={"Content-Length": str(len(payload))},
    )


# ─────────────────────────── Echo (POST/PUT/PATCH/DELETE) ───────────────────────────


def _extract_body(request):
    """Разбирает тело запроса: JSON -> объект, form -> dict, иначе строка."""
    if not request.body:
        return None
    ctype = request.content_type
    if "json" in ctype:
        return orjson.loads(request.body)  # orjson.JSONDecodeError -> 400 в echo
    if "form" in ctype:
        # у POST multipart/urlencoded request.POST заполнен,
        # у PUT/PATCH тело придётся разобрать самим
        if request.POST:
            return dict(request.POST.items())
        return QueryDict(request.body).dict()
    return request.body.decode("utf-8", "replace")


@require_http_methods(["GET", "POST", "PUT", "PATCH", "DELETE"])
def echo(request):
    """Возвращает метод и тело запроса; POST -> 201, остальное -> 200.

    test_post_json: 201 + {"id": 1}; test_post_data; test_put_patch_delete.
    """
    try:
        data = _extract_body(request)
    except orjson.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    status = 201 if request.method == "POST" else 200
    if request.method == "GET":
        return JsonResponse(
            {"method": "GET", "args": request.GET.dict()}, status=status
        )
    return JsonResponse({"method": request.method, "data": data}, status=status)


# ─────────────────────────── Файлы ───────────────────────────

MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MiB
META_FIELD = "JSONData"  # то же имя поля, что шлёт HttpClient.upload_file


@require_http_methods(["POST"])
def upload(request):
    """Multipart-загрузка: поле `file` + JSON-метаданные в поле JSONData.

    Сохраняет файл в MEDIA_ROOT/uploads/, возвращает 201 с метаданными.
    Ошибки: 400 (нет файла/поля, битые метаданные), 413 (файл слишком большой).
    """
    file = request.FILES.get("file")
    if file is None:
        return JsonResponse({"error": "missing file field 'file'"}, status=400)

    raw_meta = request.POST.get(META_FIELD)
    if raw_meta is None:
        return JsonResponse({"error": f"missing form field '{META_FIELD}'"}, status=400)

    try:
        meta = orjson.loads(raw_meta)
    except orjson.JSONDecodeError:
        return JsonResponse({"error": f"invalid JSON in '{META_FIELD}'"}, status=400)

    if file.size > MAX_UPLOAD_SIZE:
        return JsonResponse({"error": "file too large"}, status=413)

    stored = default_storage.save(f"uploads/{file.name}", file)
    return JsonResponse(
        {
            "ok": 1,
            "filename": file.name,
            "stored_as": stored,
            "size": file.size,
            "meta": meta,
        },
        status=201,
    )


@require_http_methods(["GET", "HEAD"])
def download(request, name: str):
    """Streaming-отдача ранее загруженного файла (client.download_file).

    404, если файла нет — клиент бросает HttpStatusError со status=404.
    """
    stored = f"uploads/{name}"
    if not default_storage.exists(stored):
        raise Http404(f"no such file: {name}")
    return FileResponse(default_storage.open(stored, "rb"), as_attachment=True)
