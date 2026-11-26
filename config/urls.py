"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),

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

    path(
        "reports/",
        include("reports.urls"),
    ),

    path(
        "notifications/",
        include("notifications.urls"),
    ),

    path(
        "departments/",
        include("departments.urls"),
    ),

    path(
        "assets/",
        include("assets.urls"),
    ),

    path(
        "assignments/",
        include("assignments.urls"),
    ),

    path(
        "dashboard/",
        include("dashboard.urls"),
    ),

    path(
        "software-licenses/",
        include("software_licenses.urls"),
    ),

    path(
        "vendors/",
        include("vendors.urls"),
    ),
]


# Serve uploaded media files during development only.
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )