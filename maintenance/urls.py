from django.urls import path

from .views import (
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
]