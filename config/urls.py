"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "users/",
        include("accounts.urls"),
    ),

    path(
        "asset-requests/",
        include("asset_requests.urls"),
    ),

    path(
        "maintenance/",
        include("maintenance.urls"),
    ),
]