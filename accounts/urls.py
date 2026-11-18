
from django.contrib.auth import views as auth_views
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

    # Password Reset
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

    # Logged-in User Password Change
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