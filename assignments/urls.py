from django.urls import path

from .views import (
    department_manager_assignments,
    department_manager_assignment_detail,
)


urlpatterns = [
    path(
        "department-manager/",
        department_manager_assignments,
        name="department_manager_assignments",
    ),
    path(
        "department-manager/<int:assignment_id>/",
        department_manager_assignment_detail,
        name="department_manager_assignment_detail",
    ),
]