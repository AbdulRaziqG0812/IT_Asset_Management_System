from django.urls import path

from .views import (
    add_user,
    edit_user,
    employee_dashboard,
    login_view,
    logout_view,
    toggle_user_status,
    user_management,
)


urlpatterns = [

    path(
        "employee-dashboard/",
        employee_dashboard,
        name="employee_dashboard",
    ),
    path(
        "login/",
        login_view,
        name="login",
    ),
    path(
        "logout/",
        logout_view,
        name="logout",
    ),
    path(
        "",
        user_management,
        name="user_management",
    ),
    path(
        "add/",
        add_user,
        name="add_user",
    ),
    path(
        "edit/<int:user_id>/",
        edit_user,
        name="edit_user",
    ),
    path(
        "toggle-status/<int:user_id>/",
        toggle_user_status,
        name="toggle_user_status",
    ),
]