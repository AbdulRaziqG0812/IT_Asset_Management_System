
from django.urls import path

from .views import (
    admin_maintenance_list,
    admin_maintenance_process,
    create_maintenance_request,
    employee_maintenance_requests,
)


urlpatterns = [
    path(
        "",
        employee_maintenance_requests,
        name="employee_maintenance_requests",
    ),
    path(
        "create/",
        create_maintenance_request,
        name="create_maintenance_request",
    ),
    path(
        "admin/",
        admin_maintenance_list,
        name="maintenance_list",
    ),
    path(
        "admin/<int:maintenance_id>/process/",
        admin_maintenance_process,
        name="admin_maintenance_process",
    ),
]
