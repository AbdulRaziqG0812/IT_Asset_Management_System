from django.urls import path

from .views import (
    asset_create,
    asset_delete,
    asset_detail,
    asset_list,
    asset_update,
)


urlpatterns = [
    path(
        "",
        asset_list,
        name="asset_list",
    ),
    path(
        "add/",
        asset_create,
        name="asset_create",
    ),
    path(
        "<int:asset_id>/",
        asset_detail,
        name="asset_detail",
    ),
    path(
        "<int:asset_id>/edit/",
        asset_update,
        name="asset_update",
    ),
    path(
        "<int:asset_id>/delete/",
        asset_delete,
        name="asset_delete",
    ),
]