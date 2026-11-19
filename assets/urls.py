from django.urls import path

from .views import (
    department_manager_assets,
    department_manager_asset_detail,
)


urlpatterns = [
    path(
        "department-manager/",
        department_manager_assets,
        name="department_manager_assets",
    ),
    path(
        "department-manager/<int:asset_id>/",
        department_manager_asset_detail,
        name="department_manager_asset_detail",
    ),
]