"""Root URL configuration for SSK-Law backend."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("bills.urls")),
    path("api/", include("chat.urls")),
    path("api/", include("posts.urls")),
]
