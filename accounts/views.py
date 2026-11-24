from datetime import date

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.permissions import is_super_admin
from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log
from notifications.models import Notification

from .models import EmployeeProfile, User

from assets.models import Asset
from asset_requests.models import AssetRequest
from software_licenses.models import SoftwareLicense


# ============================================================================
# COMMON HELPERS
# ============================================================================


def is_hr_or_super_admin(user):
    return (
        user.is_authenticated
        and user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.HR_MANAGER,
        )
    )


def get_client_ip(request):
    return request.META.get("REMOTE_ADDR")


def get_employee_active_assignments(employee):
    """
    Returns currently active asset assignments for an employee.

    Import is kept inside the helper to avoid unnecessary model-loading
    dependencies when this functionality is not being used.
    """
    from assignments.models import Assignment

    return (
        Assignment.objects
        .select_related("asset")
        .filter(
            employee=employee,
            is_active=True,
        )
        .order_by("assigned_date", "id")
    )


def notify_it_and_super_admins(
    *,
    notification_type,
    severity,
    title,
    message,
    reference_type,
    reference_id,
    url="",
):
    """
    Notify all active IT Administrators and Super Admins.

    Notifications are created individually so each recipient has
    independent read/unread state.
    """

    recipients = User.objects.filter(
        is_active=True,
        role__in=(
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        ),
    ).order_by("id")

    notifications = []

    for recipient in recipients:
        notifications.append(
            Notification(
                recipient=recipient,
                notification_type=notification_type,
                severity=severity,
                title=title,
                message=message,
                url=url,
                reference_type=reference_type,
                reference_id=str(reference_id),
            )
        )

    if notifications:
        Notification.objects.bulk_create(notifications)


# ============================================================================
# EMPLOYEE DASHBOARD
# ============================================================================


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
def super_admin_dashboard(request):
    """
    Dedicated landing dashboard for Super Admin.

    Dashboard statistics are calculated directly from the
    current database records.
    """

    today = timezone.localdate()

    total_users = User.objects.count()

    total_assets = Asset.objects.count()

    available_assets = Asset.objects.filter(
        status=Asset.Status.AVAILABLE
    ).count()

    assigned_assets = Asset.objects.filter(
        status=Asset.Status.ASSIGNED
    ).count()

    maintenance_assets = Asset.objects.filter(
        status=Asset.Status.UNDER_MAINTENANCE
    ).count()

    damaged_assets = Asset.objects.filter(
        status=Asset.Status.DAMAGED
    ).count()

    pending_requests = AssetRequest.objects.filter(
        status=AssetRequest.Status.PENDING
    ).count()

    expiring_licenses = SoftwareLicense.objects.filter(
        status=SoftwareLicense.Status.EXPIRING_SOON
    ).count()

    return render(
        request,
        "accounts/super_admin_dashboard.html",
        {
            "user": request.user,

            "total_users": total_users,
            "total_assets": total_assets,
            "available_assets": available_assets,
            "assigned_assets": assigned_assets,
            "maintenance_assets": maintenance_assets,
            "damaged_assets": damaged_assets,
            "pending_requests": pending_requests,
            "expiring_licenses": expiring_licenses,
        },
    )


# ============================================================================
# EMPLOYEE - MY ASSIGNED ASSETS
# ============================================================================


@login_required
def employee_assigned_assets(request):
    """
    Display the assets currently assigned to the authenticated employee.

    Employees can only access their own active assignments.
    No other employee's assignment records are exposed.
    """

    if request.user.role != User.Role.EMPLOYEE:
        return redirect("login")

    employee = getattr(
        request.user,
        "employee_profile",
        None,
    )

    if employee is None:
        raise PermissionDenied(
            "Your employee profile is not available."
        )

    assignments = get_employee_active_assignments(
        employee
    )

    return render(
        request,
        "accounts/employee_assigned_assets.html",
        {
            "employee": employee,
            "assignments": assignments,
        },
    )


# ============================================================================
# SUPER ADMIN - USER MANAGEMENT
# ============================================================================


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
                {"error": "Username is required."},
            )

        if not email:
            return render(
                request,
                "accounts/user_form.html",
                {"error": "Email is required."},
            )

        if role not in User.Role.values:
            return render(
                request,
                "accounts/user_form.html",
                {"error": "Invalid user role selected."},
            )

        if not password:
            return render(
                request,
                "accounts/user_form.html",
                {"error": "Password is required."},
            )

        if password != confirm_password:
            return render(
                request,
                "accounts/user_form.html",
                {"error": "Passwords do not match."},
            )

        if User.objects.filter(username=username).exists():
            return render(
                request,
                "accounts/user_form.html",
                {"error": "Username already exists."},
            )

        if User.objects.filter(email=email).exists():
            return render(
                request,
                "accounts/user_form.html",
                {"error": "Email already exists."},
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

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.CREATE,
            module="User Management",
            object_type="User",
            object_id=user.id,
            description=(
                f"Super Admin created user '{user.username}' "
                f"with role '{user.get_role_display()}'."
            ),
            ip_address=get_client_ip(request),
        )

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

        if (
            User.objects
            .filter(username=username)
            .exclude(id=user.id)
            .exists()
        ):
            return render(
                request,
                "accounts/user_edit.html",
                {
                    "user": user,
                    "error": "Username already exists.",
                },
            )

        if (
            User.objects
            .filter(email=email)
            .exclude(id=user.id)
            .exists()
        ):
            return render(
                request,
                "accounts/user_edit.html",
                {
                    "user": user,
                    "error": "Email already exists.",
                },
            )

        if user.id == request.user.id and not is_active:
            return render(
                request,
                "accounts/user_edit.html",
                {
                    "user": user,
                    "error": "You cannot deactivate your own account.",
                },
            )

        old_role = user.role
        old_is_active = user.is_active

        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.role = role
        user.is_active = is_active
        user.save()

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.UPDATE,
            module="User Management",
            object_type="User",
            object_id=user.id,
            description=(
                f"User '{user.username}' was updated. "
                f"Role: '{old_role}' -> '{user.role}'. "
                f"Active: '{old_is_active}' -> '{user.is_active}'."
            ),
            ip_address=get_client_ip(request),
        )

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

    if user.id == request.user.id and user.is_active:
        raise PermissionDenied(
            "You cannot deactivate your own account."
        )

    old_status = user.is_active

    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])

    create_audit_log(
        user=request.user,
        action=AuditLog.Action.UPDATE,
        module="User Management",
        object_type="User",
        object_id=user.id,
        description=(
            f"User '{user.username}' active status changed "
            f"from '{old_status}' to '{user.is_active}'."
        ),
        ip_address=get_client_ip(request),
    )

    return redirect("user_management")


# ============================================================================
# HR - EMPLOYEE MANAGEMENT
# ============================================================================


@login_required
@user_passes_test(is_hr_or_super_admin)
def employee_management(request):
    employees = (
        EmployeeProfile.objects
        .select_related(
            "user",
            "department",
        )
        .order_by("employee_id")
    )

    return render(
        request,
        "accounts/hr_employee_management.html",
        {
            "employees": employees,
        },
    )


@login_required
@user_passes_test(is_hr_or_super_admin)
def employee_detail(request, employee_id):
    employee = get_object_or_404(
        EmployeeProfile.objects.select_related(
            "user",
            "department",
        ),
        id=employee_id,
    )

    active_assignments = get_employee_active_assignments(
        employee
    )

    return render(
        request,
        "accounts/hr_employee_detail.html",
        {
            "employee": employee,
            "active_assignments": active_assignments,
        },
    )


@login_required
@user_passes_test(is_hr_or_super_admin)
def edit_employee(request, employee_id):
    employee = get_object_or_404(
        EmployeeProfile.objects.select_related(
            "user",
            "department",
        ),
        id=employee_id,
    )

    if request.method == "POST":
        department_id = request.POST.get(
            "department",
            "",
        ).strip()

        phone = request.POST.get(
            "phone",
            "",
        ).strip()

        job_title = request.POST.get(
            "job_title",
            "",
        ).strip()

        date_of_joining = request.POST.get(
            "date_of_joining",
            "",
        ).strip()

        address = request.POST.get(
            "address",
            "",
        ).strip()

        if department_id:
            from departments.models import Department

            department = get_object_or_404(
                Department,
                id=department_id,
                is_active=True,
            )
        else:
            department = None

        old_values = {
            "department": (
                employee.department.name
                if employee.department
                else ""
            ),
            "phone": employee.phone,
            "job_title": employee.job_title,
            "date_of_joining": employee.date_of_joining,
            "address": employee.address,
        }

        employee.department = department
        employee.phone = phone
        employee.job_title = job_title

        if date_of_joining:
            try:
                employee.date_of_joining = date.fromisoformat(
                    date_of_joining
                )
            except ValueError:
                return render(
                    request,
                    "accounts/hr_employee_edit.html",
                    {
                        "employee": employee,
                        "error": (
                            "Invalid joining date. "
                            "Please use YYYY-MM-DD format."
                        ),
                    },
                )
        else:
            employee.date_of_joining = None

        employee.address = address

        with transaction.atomic():
            employee.save()

            create_audit_log(
                user=request.user,
                action=AuditLog.Action.UPDATE,
                module="HR Employee Management",
                object_type="EmployeeProfile",
                object_id=employee.id,
                description=(
                    f"Employee '{employee.employee_id}' "
                    f"information was updated. "
                    f"Previous values: {old_values}"
                ),
                ip_address=get_client_ip(request),
            )

        return redirect(
            "hr_employee_detail",
            employee_id=employee.id,
        )

    from departments.models import Department

    departments = (
        Department.objects
        .filter(is_active=True)
        .order_by("name")
    )

    return render(
        request,
        "accounts/hr_employee_edit.html",
        {
            "employee": employee,
            "departments": departments,
        },
    )


# ============================================================================
# HR - RESIGNATION WORKFLOW
# ============================================================================


@login_required
@user_passes_test(is_hr_or_super_admin)
def start_employee_resignation(request, employee_id):
    """
    Start an employee resignation process.

    HR/Super Admin can initiate resignation.
    The actual asset return remains an IT-controlled operation.
    """

    if request.method != "POST":
        raise PermissionDenied(
            "Employee resignation can only be started using POST."
        )

    employee = get_object_or_404(
        EmployeeProfile.objects.select_related(
            "user",
            "department",
        ),
        id=employee_id,
    )

    if employee.employment_status == (
        EmployeeProfile.EmploymentStatus.EXITED
    ):
        raise PermissionDenied(
            "An exited employee cannot be placed into resignation again."
        )

    if employee.employment_status == (
        EmployeeProfile.EmploymentStatus.RESIGNATION_PENDING
    ):
        raise PermissionDenied(
            "This employee is already in resignation pending status."
        )

    resignation_date_value = request.POST.get(
        "resignation_date",
        "",
    ).strip()

    resignation_reason = request.POST.get(
        "exit_reason",
        "",
    ).strip()

    resignation_notes = request.POST.get(
        "exit_notes",
        "",
    ).strip()

    if not resignation_date_value:
        raise PermissionDenied(
            "Resignation date is required."
        )

    try:
        resignation_date = date.fromisoformat(
            resignation_date_value
        )
    except ValueError:
        raise PermissionDenied(
            "Invalid resignation date. Use YYYY-MM-DD format."
        )

    if resignation_date > timezone.localdate():
        raise PermissionDenied(
            "Resignation date cannot be in the future."
        )

    if not resignation_reason:
        raise PermissionDenied(
            "Resignation reason is required."
        )

    active_assignments = get_employee_active_assignments(
        employee
    )

    if active_assignments.exists():
        asset_return_status = (
            EmployeeProfile.AssetReturnStatus.PENDING
        )
    else:
        asset_return_status = (
            EmployeeProfile.AssetReturnStatus.NOT_REQUIRED
        )

    with transaction.atomic():
        employee.employment_status = (
            EmployeeProfile.EmploymentStatus.RESIGNATION_PENDING
        )
        employee.resignation_date = resignation_date
        employee.exit_reason = resignation_reason
        employee.exit_notes = resignation_notes
        employee.asset_return_status = asset_return_status

        employee.save(
            update_fields=[
                "employment_status",
                "resignation_date",
                "exit_reason",
                "exit_notes",
                "asset_return_status",
                "updated_at",
            ]
        )

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.UPDATE,
            module="HR Employee Management",
            object_type="EmployeeProfile",
            object_id=employee.id,
            description=(
                f"Employee '{employee.employee_id}' "
                f"entered resignation pending status. "
                f"Resignation date: {resignation_date}. "
                f"Asset return status: "
                f"'{asset_return_status}'."
            ),
            ip_address=get_client_ip(request),
        )

        notify_it_and_super_admins(
            notification_type=Notification.NotificationType.EMPLOYEE_EVENT,
            severity=Notification.Severity.WARNING,
            title="Employee Resignation Initiated",
            message=(
                f"Employee '{employee.user.get_full_name() or employee.user.username}' "
                f"({employee.employee_id}) has entered resignation "
                f"pending status. "
                f"Resignation date: {resignation_date}. "
                f"Asset return status: "
                f"{employee.get_asset_return_status_display()}."
            ),
            reference_type="EmployeeProfile",
            reference_id=employee.id,
            url=f"/users/hr/employees/{employee.id}/",
        )

    return redirect(
        "hr_employee_detail",
        employee_id=employee.id,
    )


# ============================================================================
# HR - COMPLETE EMPLOYEE EXIT
# ============================================================================


@login_required
@user_passes_test(is_hr_or_super_admin)
def complete_employee_exit(request, employee_id):
    """
    Complete an employee exit.

    Exit cannot be completed while active asset assignments exist.
    IT must return/close those assignments first.
    """

    if request.method != "POST":
        raise PermissionDenied(
            "Employee exit can only be completed using POST."
        )

    employee = get_object_or_404(
        EmployeeProfile.objects.select_related(
            "user",
            "department",
        ),
        id=employee_id,
    )

    if employee.employment_status != (
        EmployeeProfile.EmploymentStatus.RESIGNATION_PENDING
    ):
        raise PermissionDenied(
            "Only employees in resignation pending status "
            "can be marked as exited."
        )

    if not employee.resignation_date:
        raise PermissionDenied(
            "Resignation date is required before completing exit."
        )

    exit_date_value = request.POST.get(
        "exit_date",
        "",
    ).strip()

    if not exit_date_value:
        raise PermissionDenied(
            "Exit date is required."
        )

    try:
        exit_date = date.fromisoformat(
            exit_date_value
        )
    except ValueError:
        raise PermissionDenied(
            "Invalid exit date. Use YYYY-MM-DD format."
        )

    if exit_date < employee.resignation_date:
        raise PermissionDenied(
            "Exit date cannot be earlier than the resignation date."
        )

    active_assignments = get_employee_active_assignments(
        employee
    )

    if active_assignments.exists():
        employee.asset_return_status = (
            EmployeeProfile.AssetReturnStatus.PENDING
        )
        employee.save(
            update_fields=[
                "asset_return_status",
                "updated_at",
            ]
        )

        raise PermissionDenied(
            "Employee exit cannot be completed while active asset "
            "assignments exist. IT must return all assigned assets first."
        )

    with transaction.atomic():
        employee.employment_status = (
            EmployeeProfile.EmploymentStatus.EXITED
        )
        employee.exit_date = exit_date
        employee.asset_return_status = (
            EmployeeProfile.AssetReturnStatus.COMPLETED
            if employee.asset_return_status
            != EmployeeProfile.AssetReturnStatus.NOT_REQUIRED
            else EmployeeProfile.AssetReturnStatus.NOT_REQUIRED
        )

        employee.save(
            update_fields=[
                "employment_status",
                "exit_date",
                "asset_return_status",
                "updated_at",
            ]
        )

        # The application account is disabled only after the
        # employee has actually reached EXITED status.
        employee.user.is_active = False
        employee.user.save(
            update_fields=["is_active"]
        )

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.UPDATE,
            module="HR Employee Management",
            object_type="EmployeeProfile",
            object_id=employee.id,
            description=(
                f"Employee '{employee.employee_id}' "
                f"completed exit. "
                f"Exit date: {exit_date}. "
                f"User account was deactivated after exit."
            ),
            ip_address=get_client_ip(request),
        )

        notify_it_and_super_admins(
            notification_type=Notification.NotificationType.EMPLOYEE_EVENT,
            severity=Notification.Severity.INFO,
            title="Employee Exit Completed",
            message=(
                f"Employee '{employee.user.get_full_name() or employee.user.username}' "
                f"({employee.employee_id}) has completed the exit process "
                f"with exit date {exit_date}. "
                f"All active asset assignments have been cleared."
            ),
            reference_type="EmployeeProfile",
            reference_id=employee.id,
            url=f"/users/hr/employees/{employee.id}/",
        )

    return redirect(
        "hr_employee_detail",
        employee_id=employee.id,
    )


# ============================================================================
# HR - UPDATE ASSET RETURN STATUS
# ============================================================================


@login_required
@user_passes_test(is_hr_or_super_admin)
def update_employee_asset_return_status(
    request,
    employee_id,
):
    """
    HR can update the employee-level return tracking status.

    This does NOT return an actual asset assignment.
    Actual assignment return remains an IT-controlled operation.
    """

    if request.method != "POST":
        raise PermissionDenied(
            "Asset return status can only be changed using POST."
        )

    employee = get_object_or_404(
        EmployeeProfile,
        id=employee_id,
    )

    if employee.employment_status not in (
        EmployeeProfile.EmploymentStatus.RESIGNATION_PENDING,
        EmployeeProfile.EmploymentStatus.EXITED,
    ):
        raise PermissionDenied(
            "Asset return tracking is only applicable to "
            "resignation or exited employees."
        )

    requested_status = request.POST.get(
        "asset_return_status",
        "",
    ).strip()

    allowed_statuses = {
        choice[0]
        for choice in EmployeeProfile.AssetReturnStatus.choices
    }

    if requested_status not in allowed_statuses:
        raise PermissionDenied(
            "Invalid asset return status."
        )

    active_assignments = get_employee_active_assignments(
        employee
    )

    if (
        requested_status
        == EmployeeProfile.AssetReturnStatus.COMPLETED
        and active_assignments.exists()
    ):
        raise PermissionDenied(
            "Asset return status cannot be marked Completed while "
            "active asset assignments still exist."
        )

    old_status = employee.asset_return_status

    employee.asset_return_status = requested_status
    employee.save(
        update_fields=[
            "asset_return_status",
            "updated_at",
        ]
    )

    create_audit_log(
        user=request.user,
        action=AuditLog.Action.UPDATE,
        module="HR Employee Management",
        object_type="EmployeeProfile",
        object_id=employee.id,
        description=(
            f"Employee '{employee.employee_id}' asset return status "
            f"changed from '{old_status}' to '{requested_status}'."
        ),
        ip_address=get_client_ip(request),
    )

    return redirect(
        "hr_employee_detail",
        employee_id=employee.id,
    )


# ============================================================================
# AUTHENTICATION
# ============================================================================


def get_role_redirect(user):
    """
    Return the correct landing page for each authenticated role.

    Keeping all role-based login routing in one place prevents
    different parts of the login flow from becoming inconsistent.
    """

    if user.role == User.Role.SUPER_ADMIN:
        return "super_admin_dashboard"

    if user.role == User.Role.IT_ADMIN:
        return "dashboard:home"

    if user.role == User.Role.HR_MANAGER:
        return "hr_employee_management"

    if user.role == User.Role.DEPARTMENT_MANAGER:
        return "department_manager_dashboard"

    if user.role == User.Role.EMPLOYEE:
        return "employee_dashboard"

    return None


def login_view(request):
    """
    Authenticate users and redirect every supported role to its
    correct application landing page.
    """

    if request.user.is_authenticated:
        if not request.user.is_active:
            logout(request)

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

        redirect_name = get_role_redirect(request.user)

        if redirect_name:
            return redirect(redirect_name)

        return render(
            request,
            "accounts/login.html",
            {
                "error": (
                    "Your account has an invalid or unsupported role. "
                    "Please contact the administrator."
                ),
            },
        )

    if request.method == "POST":
        username = request.POST.get(
            "username",
            "",
        ).strip()

        password = request.POST.get(
            "password",
            "",
        )

        if not username or not password:
            return render(
                request,
                "accounts/login.html",
                {
                    "error": (
                        "Username and password are required."
                    ),
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

        redirect_name = get_role_redirect(user)

        if redirect_name is None:
            return render(
                request,
                "accounts/login.html",
                {
                    "error": (
                        "Your account has an invalid or unsupported role. "
                        "Please contact the administrator."
                    ),
                },
            )

        login(request, user)

        return redirect(redirect_name)

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