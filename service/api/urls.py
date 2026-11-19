from django.urls import path

from . import views

urlpatterns = [
    path("api/json/", views.json_ok),
    path("api/empty/", views.empty),
    path("api/html/", views.html),
    path("api/invalid-json/", views.invalid_json),
    path("api/error/", views.server_error),
    path("api/echo/", views.echo),
    path("api/ping/", views.ping),
    path("api/head-only/", views.head_only),
    path("api/redirect/", views.redirect_to_ping),
    path("api/payload/", views.fixed_payload),
    path("api/upload/", views.upload),
    path("api/download/<str:name>/", views.download),
]
