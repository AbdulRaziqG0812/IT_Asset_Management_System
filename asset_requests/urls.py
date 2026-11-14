from django.urls import path

from .views import (
    employee_asset_requests,
    create_asset_request,
)


urlpatterns = [
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
]