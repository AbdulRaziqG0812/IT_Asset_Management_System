from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .models import User
from .permissions import is_super_admin


@login_required
def employee_dashboard(request):
    if request.user.role != User.Role.EMPLOYEE:
        return redirect("login")

    profile = getattr(
        request.user,
        "employee_profile",
        None,
    )

    return render(
        request,
        "accounts/employee_dashboard.html",
        {
            "profile": profile,
        },
    )


@login_required
@user_passes_test(is_super_admin)
def user_management(request):
    users = User.objects.all().order_by("username")

    return render(
        request,
        "accounts/user_management.html",
        {
            "users": users,
        },
    )


@login_required
@user_passes_test(is_super_admin)
def add_user(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        role = request.POST.get("role", "").strip()
        is_active = request.POST.get("is_active") == "1"
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not username:
            return render(
                request,
                "accounts/user_form.html",
                {
                    "error": "Username is required.",
                },
            )

        if not email:
            return render(
                request,
                "accounts/user_form.html",
                {
                    "error": "Email is required.",
                },
            )

        if role not in User.Role.values:
            return render(
                request,
                "accounts/user_form.html",
                {
                    "error": "Invalid user role selected.",
                },
            )

        if not password:
            return render(
                request,
                "accounts/user_form.html",
                {
                    "error": "Password is required.",
                },
            )

        if password != confirm_password:
            return render(
                request,
                "accounts/user_form.html",
                {
                    "error": "Passwords do not match.",
                },
            )

        if User.objects.filter(username=username).exists():
            return render(
                request,
                "accounts/user_form.html",
                {
                    "error": "Username already exists.",
                },
            )

        if User.objects.filter(email=email).exists():
            return render(
                request,
                "accounts/user_form.html",
                {
                    "error": "Email already exists.",
                },
            )

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=is_active,
        )

        user.set_password(password)
        user.save()

        return redirect("user_management")

    return render(
        request,
        "accounts/user_form.html",
    )


@login_required
@user_passes_test(is_super_admin)
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        role = request.POST.get("role", "").strip()
        is_active = request.POST.get("is_active") == "1"

        if not username:
            return render(
                request,
                "accounts/user_edit.html",
                {
                    "user": user,
                    "error": "Username is required.",
                },
            )

        if not email:
            return render(
                request,
                "accounts/user_edit.html",
                {
                    "user": user,
                    "error": "Email is required.",
                },
            )

        if role not in User.Role.values:
            return render(
                request,
                "accounts/user_edit.html",
                {
                    "user": user,
                    "error": "Invalid user role selected.",
                },
            )

        if User.objects.filter(
            username=username
        ).exclude(id=user.id).exists():
            return render(
                request,
                "accounts/user_edit.html",
                {
                    "user": user,
                    "error": "Username already exists.",
                },
            )

        if User.objects.filter(
            email=email
        ).exclude(id=user.id).exists():
            return render(
                request,
                "accounts/user_edit.html",
                {
                    "user": user,
                    "error": "Email already exists.",
                },
            )

        # Prevent Super Admin from disabling their own account.
        if user.id == request.user.id and not is_active:
            return render(
                request,
                "accounts/user_edit.html",
                {
                    "user": user,
                    "error": "You cannot deactivate your own account.",
                },
            )

        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.role = role
        user.is_active = is_active

        user.save()

        return redirect("user_management")

    return render(
        request,
        "accounts/user_edit.html",
        {
            "user": user,
        },
    )


@login_required
@user_passes_test(is_super_admin)
def toggle_user_status(request, user_id):
    if request.method != "POST":
        raise PermissionDenied(
            "User account status can only be changed using POST."
        )

    user = get_object_or_404(User, id=user_id)

    # Super Admin must not be able to deactivate their own account.
    if user.id == request.user.id and user.is_active:
        raise PermissionDenied(
            "You cannot deactivate your own account."
        )

    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])

    return redirect("user_management")


def login_view(request):
    if request.user.is_authenticated:
        if request.user.role == User.Role.SUPER_ADMIN:
            return redirect("user_management")

        if request.user.role == User.Role.EMPLOYEE:
            return redirect("employee_dashboard")

        return render(
            request,
            "accounts/login.html",
            {
                "error": "You are already logged in.",
            },
        )

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:
            return render(
                request,
                "accounts/login.html",
                {
                    "error": "Username and password are required.",
                },
            )

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is None:
            return render(
                request,
                "accounts/login.html",
                {
                    "error": "Invalid username or password.",
                },
            )

        if not user.is_active:
            return render(
                request,
                "accounts/login.html",
                {
                    "error": (
                        "Your account is inactive. "
                        "Please contact the administrator."
                    ),
                },
            )

        login(request, user)

        if user.role == User.Role.SUPER_ADMIN:
            return redirect("user_management")

        if user.role == User.Role.EMPLOYEE:
            return redirect("employee_dashboard")

        return render(
            request,
            "accounts/login.html",
            {
                "error": (
                    f"Login successful. "
                    f"{user.get_role_display()} dashboard "
                    f"will be available here."
                ),
            },
        )

    return render(
        request,
        "accounts/login.html",
    )


def logout_view(request):
    if request.method != "POST":
        raise PermissionDenied(
            "Logout can only be performed using POST."
        )

    logout(request)

    return redirect("login")