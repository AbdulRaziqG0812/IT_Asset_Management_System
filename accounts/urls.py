from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    add_user,
    complete_employee_exit,
    delete_user,
    edit_employee,
    edit_user,
    employee_assigned_assets,
    employee_detail,
    employee_dashboard,
    employee_management,
    super_admin_dashboard,
    login_view,
    logout_view,
    start_employee_resignation,
    toggle_user_status,
    update_employee_asset_return_status,
    user_management,
)


urlpatterns = [

    # ------------------------------------------------------------------
    # Super Admin Dashboard
    # ------------------------------------------------------------------

    path(
        "super-admin-dashboard/",
        super_admin_dashboard,
        name="super_admin_dashboard",
    ),

    # ------------------------------------------------------------------
    # Employee
    # ------------------------------------------------------------------

    path(
        "employee-dashboard/",
        employee_dashboard,
        name="employee_dashboard",
    ),

    path(
        "employee/assigned-assets/",
        employee_assigned_assets,
        name="employee_assigned_assets",
    ),

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Super Admin - User Management
    # ------------------------------------------------------------------

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

    path(
        "delete/<int:user_id>/",
        delete_user,
        name="delete_user",
    ),

    # ------------------------------------------------------------------
    # HR - Employee Management
    # ------------------------------------------------------------------

    path(
        "hr/employees/",
        employee_management,
        name="hr_employee_management",
    ),

    path(
        "hr/employees/<int:employee_id>/",
        employee_detail,
        name="hr_employee_detail",
    ),

    path(
        "hr/employees/<int:employee_id>/edit/",
        edit_employee,
        name="hr_employee_edit",
    ),

    # ------------------------------------------------------------------
    # HR - Resignation Workflow
    # ------------------------------------------------------------------

    path(
        "hr/employees/<int:employee_id>/resignation/",
        start_employee_resignation,
        name="hr_employee_resignation",
    ),

    path(
        "hr/employees/<int:employee_id>/exit/",
        complete_employee_exit,
        name="hr_employee_exit",
    ),

    path(
        "hr/employees/<int:employee_id>/asset-return-status/",
        update_employee_asset_return_status,
        name="hr_employee_asset_return_status",
    ),

    # ------------------------------------------------------------------
    # Password Reset
    # ------------------------------------------------------------------

    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset.html",
            email_template_name="accounts/password_reset_email.txt",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url="/users/password-reset/done/",
        ),
        name="password_reset",
    ),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html",
        ),
        name="password_reset_done",
    ),

    path(
        "password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url="/users/password-reset/complete/",
        ),
        name="password_reset_confirm",
    ),

    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),

    # ------------------------------------------------------------------
    # Password Change
    # ------------------------------------------------------------------

    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change.html",
            success_url="/users/password-change/done/",
        ),
        name="password_change",
    ),

    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html",
        ),
        name="password_change_done",
    ),
]