from django.urls import path

from .views import (
    admin_assignment_create,
    admin_assignment_list,
    admin_assignment_return,
    assignment_detail,
    assignment_history,
    department_manager_assignment_detail,
    department_manager_assignments,
)

urlpatterns = [
    # Super Admin / IT Admin - Assignment Management
    path(
        "admin/",
        admin_assignment_list,
        name="admin_assignment_list",
    ),
    path(
        "admin/create/",
        admin_assignment_create,
        name="admin_assignment_create",
    ),
    path(
        "admin/<int:assignment_id>/return/",
        admin_assignment_return,
        name="admin_assignment_return",
    ),

    # Role-aware Assignment History
    path(
        "history/",
        assignment_history,
        name="assignment_history",
    ),
    path(
        "history/<int:assignment_id>/",
        assignment_detail,
        name="assignment_detail",
    ),

    # Department Manager
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