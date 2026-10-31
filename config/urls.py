from django.contrib import admin
from django.urls import include, path, re_path

from catalog.views import photo

urlpatterns = [
    path("admin/", admin.site.urls),
    re_path(r"^media/dolls/(?P<filename>[a-f0-9]{32}\.webp)$", photo, name="photo"),
    path("", include("catalog.urls")),
]
