from django.urls import path

from .views import (
    software_license_assign,
    software_license_assignment_list,
    software_license_create,
    software_license_delete,
    software_license_edit,
    software_license_list,
    software_license_return,
)


urlpatterns = [
    path(
        "",
        software_license_list,
        name="software_license_list",
    ),
    path(
        "create/",
        software_license_create,
        name="software_license_create",
    ),
    path(
        "<int:license_id>/edit/",
        software_license_edit,
        name="software_license_edit",
    ),
    path(
        "<int:license_id>/delete/",
        software_license_delete,
        name="software_license_delete",
    ),
    path(
        "<int:license_id>/assignments/",
        software_license_assignment_list,
        name="software_license_assignment_list",
    ),
    path(
        "<int:license_id>/assign/",
        software_license_assign,
        name="software_license_assign",
    ),
    path(
        "assignments/<int:assignment_id>/return/",
        software_license_return,
        name="software_license_return",
    ),
]