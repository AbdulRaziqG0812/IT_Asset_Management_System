from django.urls import path

from .views import (
    admin_asset_request_process,
    admin_asset_requests,
    create_asset_request,
    employee_asset_requests,
)


urlpatterns = [
    # Employee Asset Requests
    path(
        "",
        employee_asset_requests,
        name="employee_asset_requests",
    ),
    path(
        "create/",
        create_asset_request,
        name="create_asset_request",
    ),

    # Admin Asset Requests
    path(
        "admin/",
        admin_asset_requests,
        name="admin_asset_requests",
    ),
    path(
        "admin/<int:request_id>/process/",
        admin_asset_request_process,
        name="admin_asset_request_process",
    ),
]