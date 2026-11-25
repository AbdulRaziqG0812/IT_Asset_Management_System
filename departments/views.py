from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.models import EmployeeProfile, User
from asset_requests.models import AssetRequest
from assignments.models import Assignment
from assets.models import Asset
from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log
from notifications.models import Notification
from notifications.services import (
    create_notification,
    get_notification_staff,
)

from .models import Department


# ============================================================================
# COMMON HELPERS
# ============================================================================


def department_manager_required(user):
    """
    Returns True only for an authenticated, active Department Manager
    whose account is linked to a department.
    """

    return (
        user.is_authenticated
        and user.role == User.Role.DEPARTMENT_MANAGER
        and user.is_active
        and user.department_id is not None
    )


def get_manager_department(request):
    """
    Returns the department belonging to the logged-in Department Manager.

    The department is always resolved from the authenticated user rather
    than from request parameters to prevent cross-department access.
    """

    if not department_manager_required(request.user):
        raise PermissionDenied(
            "Only an active Department Manager can access this resource."
        )

    department = request.user.department

    if department is None:
        raise PermissionDenied(
            "Your Department Manager account is not linked to a department."
        )

    return department


def notify_asset_request_staff(asset_request):
    """
    Notify active Super Admins and IT Administrators about a newly
    submitted asset request.

    Each recipient receives an independent notification so read/unread
    state remains user-specific.
    """

    request_url = reverse(
        "department_manager_asset_requests"
    )

    for recipient in get_notification_staff():
        create_notification(
            recipient=recipient,
            notification_type=Notification.NotificationType.ASSET_REQUEST,
            severity=Notification.Severity.WARNING,
            title="New Asset Request",
            message=(
                f"Department Manager '{request_user_display(asset_request)}' "
                f"submitted an asset request for employee "
                f"'{asset_request.employee.employee_id}' "
                f"({asset_request.asset_category})."
            ),
            url=request_url,
            reference_type="AssetRequest",
            reference_id=asset_request.pk,
        )


def request_user_display(asset_request):
    """
    Returns a safe display name for the user who submitted the request.

    AssetRequest does not currently store the submitting manager directly,
    so the employee's department manager relationship is used as the
    operational source.
    """

    department = asset_request.department

    manager = (
        User.objects
        .filter(
            role=User.Role.DEPARTMENT_MANAGER,
            department=department,
            is_active=True,
        )
        .order_by("id")
        .first()
    )

    if manager:
        return manager.get_full_name() or manager.username

    return "Department Manager"


def notify_asset_request_employee(asset_request, decision):
    """
    Notify the employee when their asset request is approved or rejected.
    """

    employee_user = asset_request.employee.user

    if decision == AssetRequest.Status.APPROVED:
        title = "Asset Request Approved"
        message = (
            f"Your asset request for "
            f"{asset_request.asset_category} has been approved "
            f"by your Department Manager."
        )
        severity = Notification.Severity.SUCCESS

    elif decision == AssetRequest.Status.REJECTED:
        title = "Asset Request Rejected"
        message = (
            f"Your asset request for "
            f"{asset_request.asset_category} has been rejected "
            f"by your Department Manager."
        )
        severity = Notification.Severity.DANGER

    else:
        return

    create_notification(
        recipient=employee_user,
        notification_type=Notification.NotificationType.ASSET_REQUEST,
        severity=severity,
        title=title,
        message=message,
        url=reverse("employee_asset_requests"),
        reference_type="AssetRequest",
        reference_id=asset_request.pk,
    )


# ============================================================================
# DEPARTMENT MANAGER DASHBOARD
# ============================================================================


@login_required
def department_manager_dashboard(request):
    """
    Department Manager dashboard data.

    All records are strictly scoped to the logged-in manager's department.
    """

    department = get_manager_department(request)

    employees = (
        EmployeeProfile.objects
        .filter(
            department=department,
            employment_status=EmployeeProfile.EmploymentStatus.ACTIVE,
        )
        .select_related("user")
        .order_by("employee_id")
    )

    assets = (
        Asset.objects
        .filter(department=department)
        .order_by("asset_id")
    )

    pending_requests = (
        AssetRequest.objects
        .filter(
            department=department,
            status=AssetRequest.Status.PENDING,
        )
        .select_related(
            "employee__user",
            "department",
        )
        .order_by("-requested_at")
    )

    active_assignments = (
        Assignment.objects
        .filter(
            employee__department=department,
            is_active=True,
        )
        .select_related(
            "asset",
            "employee__user",
            "employee__department",
        )
        .order_by("-assigned_date")
    )

    return render(
        request,
        "departments/department_manager_dashboard.html",
        {
            "department": department,
            "employees": employees,
            "assets": assets,
            "pending_requests": pending_requests,
            "active_assignments": active_assignments,
            "employee_count": employees.count(),
            "asset_count": assets.count(),
            "pending_request_count": pending_requests.count(),
            "active_assignment_count": active_assignments.count(),
        },
    )


# ============================================================================
# DEPARTMENT MANAGER - EMPLOYEES
# ============================================================================


@login_required
def department_manager_employees(request):
    """
    Department Manager can only view employees belonging to
    the manager's own department.
    """

    department = get_manager_department(request)

    employees = (
        EmployeeProfile.objects
        .filter(department=department)
        .select_related("user", "department")
        .order_by("employee_id")
    )

    return render(
        request,
        "departments/department_manager_employees.html",
        {
            "department": department,
            "employees": employees,
        },
    )


@login_required
def department_manager_employee_detail(
    request,
    employee_id,
):
    """
    Department Manager can only inspect an employee from the
    manager's own department.
    """

    department = get_manager_department(request)

    employee = get_object_or_404(
        EmployeeProfile.objects.select_related(
            "user",
            "department",
        ),
        pk=employee_id,
        department=department,
    )

    assignments = (
        Assignment.objects
        .filter(employee=employee)
        .select_related("asset")
        .order_by("-assigned_date")
    )

    requests = (
        AssetRequest.objects
        .filter(employee=employee)
        .select_related("department", "approved_by")
        .order_by("-requested_at")
    )

    return render(
        request,
        "departments/department_manager_employee_detail.html",
        {
            "department": department,
            "employee": employee,
            "assignments": assignments,
            "asset_requests": requests,
        },
    )


# ============================================================================
# DEPARTMENT MANAGER - ASSETS
# ============================================================================


@login_required
def department_manager_assets(request):
    """
    Department Manager can only view assets allocated to the
    manager's own department.
    """

    department = get_manager_department(request)

    assets = (
        Asset.objects
        .filter(department=department)
        .select_related("department")
        .order_by("asset_id")
    )

    return render(
        request,
        "departments/department_manager_assets.html",
        {
            "department": department,
            "assets": assets,
        },
    )


@login_required
def department_manager_asset_detail(request, asset_id):
    """
    Department Manager can only view the details of an asset
    belonging to the manager's own department.

    The department restriction is enforced server-side so a manager
    cannot access another department's asset by changing the asset_id
    in the URL.
    """

    department = get_manager_department(request)

    asset = get_object_or_404(
        Asset.objects.select_related("department"),
        pk=asset_id,
        department=department,
    )

    return render(
        request,
        "departments/department_manager_asset_detail.html",
        {
            "department": department,
            "asset": asset,
        },
    )


@login_required
def department_manager_asset_allocation(request):
    """
    Shows active asset allocations where the employee belongs to
    the Department Manager's own department.

    The employee department is used as the security boundary.
    """

    department = get_manager_department(request)

    assignments = (
        Assignment.objects
        .filter(
            employee__department=department,
            is_active=True,
        )
        .select_related(
            "asset",
            "employee__user",
            "employee__department",
        )
        .order_by(
            "employee__employee_id",
            "asset__asset_id",
        )
    )

    return render(
        request,
        "departments/department_manager_asset_allocation.html",
        {
            "department": department,
            "assignments": assignments,
        },
    )


# ============================================================================
# DEPARTMENT MANAGER - CREATE ASSET REQUEST
# ============================================================================


@login_required
def department_manager_create_asset_request(
    request,
):
    """
    Department Manager can submit an asset request on behalf of
    an employee belonging to the manager's own department.

    Employee and department ownership are resolved server-side.
    """

    department = get_manager_department(request)

    employees = (
        EmployeeProfile.objects
        .filter(
            department=department,
            employment_status=EmployeeProfile.EmploymentStatus.ACTIVE,
        )
        .select_related("user")
        .order_by("employee_id")
    )

    if request.method == "POST":
        employee_id = request.POST.get(
            "employee_id",
            "",
        ).strip()

        asset_category = request.POST.get(
            "asset_category",
            "",
        ).strip()

        asset_name = request.POST.get(
            "asset_name",
            "",
        ).strip()

        reason = request.POST.get(
            "reason",
            "",
        ).strip()

        priority = request.POST.get(
            "priority",
            AssetRequest.Priority.MEDIUM,
        ).strip()

        quantity_raw = request.POST.get(
            "quantity",
            "1",
        ).strip()

        employee = get_object_or_404(
            EmployeeProfile,
            pk=employee_id,
            department=department,
            employment_status=EmployeeProfile.EmploymentStatus.ACTIVE,
        )

        errors = {}

        if not asset_category:
            errors["asset_category"] = (
                "Asset category is required."
            )

        if not reason:
            errors["reason"] = (
                "Request reason is required."
            )

        try:
            quantity = int(quantity_raw)
        except (TypeError, ValueError):
            quantity = 0

        if quantity < 1:
            errors["quantity"] = (
                "Quantity must be at least 1."
            )

        valid_priorities = {
            choice[0]
            for choice in AssetRequest.Priority.choices
        }

        if priority not in valid_priorities:
            errors["priority"] = (
                "Invalid request priority."
            )

        if errors:
            return render(
                request,
                "departments/department_manager_create_request.html",
                {
                    "department": department,
                    "employees": employees,
                    "errors": errors,
                    "form_data": request.POST,
                },
                status=400,
            )

        with transaction.atomic():
            asset_request = AssetRequest(
                employee=employee,
                department=department,
                asset_category=asset_category,
                asset_name=asset_name,
                quantity=quantity,
                reason=reason,
                priority=priority,
                status=AssetRequest.Status.PENDING,
                approved_by=None,
                processed_at=None,
            )

            asset_request.save()

            create_audit_log(
                user=request.user,
                action=AuditLog.Action.CREATE,
                module="Asset Requests",
                object_type="AssetRequest",
                object_id=asset_request.id,
                description=(
                    f"Department Manager '{request.user.username}' "
                    f"created asset request #{asset_request.id} "
                    f"for employee '{employee.employee_id}' "
                    f"in department '{department.name}'."
                ),
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            notify_asset_request_staff(
                asset_request
            )

        return redirect(
            "department_manager_asset_requests"
        )

    return render(
        request,
        "departments/department_manager_create_request.html",
        {
            "department": department,
            "employees": employees,
            "errors": {},
            "form_data": {},
        },
    )


# ============================================================================
# DEPARTMENT MANAGER - ASSET REQUESTS
# ============================================================================


@login_required
def department_manager_asset_requests(request):
    """
    Department Manager can only see asset requests belonging
    to the manager's own department.
    """

    department = get_manager_department(request)

    requests = (
        AssetRequest.objects
        .filter(department=department)
        .select_related(
            "employee__user",
            "department",
            "approved_by",
        )
        .order_by("-requested_at")
    )

    return render(
        request,
        "departments/department_manager_asset_requests.html",
        {
            "department": department,
            "asset_requests": requests,
        },
    )


# ============================================================================
# DEPARTMENT MANAGER - APPROVE / REJECT ASSET REQUEST
# ============================================================================


@login_required
def department_manager_process_asset_request(
    request,
    request_id,
):
    """
    Department Manager can approve/reject only a pending request
    belonging to the manager's own department.

    Approval/rejection also creates an audit record and notifies
    the employee about the decision.
    """

    department = get_manager_department(request)

    if request.method != "POST":
        raise PermissionDenied(
            "Asset request processing must use POST."
        )

    asset_request = get_object_or_404(
        AssetRequest.objects.select_related(
            "employee__user",
            "department",
        ),
        pk=request_id,
        department=department,
    )

    if asset_request.status != AssetRequest.Status.PENDING:
        raise PermissionDenied(
            "Only pending asset requests can be processed."
        )

    decision = request.POST.get(
        "decision",
        "",
    ).strip().upper()

    manager_notes = request.POST.get(
        "manager_notes",
        "",
    ).strip()

    if decision not in {
        AssetRequest.Status.APPROVED,
        AssetRequest.Status.REJECTED,
    }:
        raise PermissionDenied(
            "Invalid asset request decision."
        )

    with transaction.atomic():
        asset_request.status = decision
        asset_request.manager_notes = manager_notes
        asset_request.approved_by = request.user
        asset_request.processed_at = timezone.now()

        asset_request.save(
            update_fields=[
                "status",
                "manager_notes",
                "approved_by",
                "processed_at",
                "updated_at",
            ]
        )

        if decision == AssetRequest.Status.APPROVED:
            audit_action = AuditLog.Action.APPROVE
            decision_text = "approved"
        else:
            audit_action = AuditLog.Action.REJECT
            decision_text = "rejected"

        create_audit_log(
            user=request.user,
            action=audit_action,
            module="Asset Requests",
            object_type="AssetRequest",
            object_id=asset_request.id,
            description=(
                f"Department Manager '{request.user.username}' "
                f"{decision_text} asset request "
                f"#{asset_request.id} for employee "
                f"'{asset_request.employee.employee_id}'."
            ),
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        notify_asset_request_employee(
            asset_request,
            decision,
        )

    return redirect(
        "department_manager_asset_requests"
    )

# ============================================================================
# SUPER ADMIN - DEPARTMENT MANAGEMENT
# ============================================================================


def super_admin_required(user):
    """
    Returns True only for an authenticated, active Super Admin.
    """

    return (
        user.is_authenticated
        and user.role == User.Role.SUPER_ADMIN
        and user.is_active
    )


def get_super_admin_department(request, department_id):
    """
    Returns a department for Super Admin operations.

    Access is restricted to active Super Admin users.
    """

    if not super_admin_required(request.user):
        raise PermissionDenied(
            "Only an active Super Admin can manage departments."
        )

    return get_object_or_404(
        Department,
        pk=department_id,
    )


@login_required
def super_admin_department_list(request):
    """
    Display all departments for the Super Admin.

    Departments are ordered by name for consistent administration.
    """

    if not super_admin_required(request.user):
        raise PermissionDenied(
            "Only an active Super Admin can access department management."
        )

    departments = (
        Department.objects
        .all()
        .order_by("name")
    )

    return render(
        request,
        "departments/super_admin_department_list.html",
        {
            "departments": departments,
        },
    )


@login_required
def super_admin_department_create(request):
    """
    Create a new department.

    Only an active Super Admin can create departments.
    """

    if not super_admin_required(request.user):
        raise PermissionDenied(
            "Only an active Super Admin can create departments."
        )

    from .forms import DepartmentForm

    if request.method == "POST":
        form = DepartmentForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                department = form.save()

                create_audit_log(
                    user=request.user,
                    action=AuditLog.Action.CREATE,
                    module="Departments",
                    object_type="Department",
                    object_id=department.id,
                    description=(
                        f"Super Admin '{request.user.username}' "
                        f"created department '{department.name}' "
                        f"with code '{department.code}'."
                    ),
                    ip_address=request.META.get("REMOTE_ADDR"),
                )

            return redirect(
                "super_admin_department_list"
            )

    else:
        form = DepartmentForm()

    return render(
        request,
        "departments/super_admin_department_form.html",
        {
            "form": form,
            "page_title": "Add Department",
            "submit_label": "Create Department",
        },
    )


@login_required
def super_admin_department_edit(
    request,
    department_id,
):
    """
    Edit an existing department.

    Only an active Super Admin can modify departments.
    """

    department = get_super_admin_department(
        request,
        department_id,
    )

    from .forms import DepartmentForm

    if request.method == "POST":
        form = DepartmentForm(
            request.POST,
            instance=department,
        )

        if form.is_valid():
            with transaction.atomic():
                department = form.save()

                create_audit_log(
                    user=request.user,
                    action=AuditLog.Action.UPDATE,
                    module="Departments",
                    object_type="Department",
                    object_id=department.id,
                    description=(
                        f"Super Admin '{request.user.username}' "
                        f"updated department '{department.name}' "
                        f"with code '{department.code}'."
                    ),
                    ip_address=request.META.get("REMOTE_ADDR"),
                )

            return redirect(
                "super_admin_department_list"
            )

    else:
        form = DepartmentForm(
            instance=department,
        )

    return render(
        request,
        "departments/super_admin_department_form.html",
        {
            "form": form,
            "department": department,
            "page_title": "Edit Department",
            "submit_label": "Save Changes",
        },
    )


@login_required
def super_admin_department_delete(
    request,
    department_id,
):
    """
    Delete an existing department.

    Deletion is intentionally restricted to POST requests to prevent
    accidental deletion through a normal GET request.

    The department must also not have dependent records that prevent
    deletion at the database level.
    """

    department = get_super_admin_department(
        request,
        department_id,
    )

    if request.method != "POST":
        raise PermissionDenied(
            "Department deletion must use POST."
        )

    department_name = department.name
    department_code = department.code
    department_id_value = department.id

    with transaction.atomic():
        department.delete()

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.DELETE,
            module="Departments",
            object_type="Department",
            object_id=department_id_value,
            description=(
                f"Super Admin '{request.user.username}' "
                f"deleted department '{department_name}' "
                f"with code '{department_code}'."
            ),
            ip_address=request.META.get("REMOTE_ADDR"),
        )

    return redirect(
        "super_admin_department_list"
    )