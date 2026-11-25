from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import EmployeeProfile, User
from assets.models import Asset
from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log
from notifications.models import Notification

from .forms import AssignmentForm, AssignmentReturnForm
from .models import Assignment


def _is_assignment_manager(user):
    return (
        user.is_authenticated
        and user.is_active
        and user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        )
    )


def _get_employee_profile(user):
    return (
        EmployeeProfile.objects
        .select_related("user", "department")
        .filter(user=user)
        .first()
    )


def _get_assignment_history_queryset():
    return (
        Assignment.objects
        .select_related(
            "asset",
            "employee__user",
            "employee__department",
        )
        .order_by(
            "-assigned_date",
            "-id",
        )
    )


def _notify_employee(
    *,
    employee,
    title,
    message,
    assignment,
):
    """
    Create an in-system notification for the employee.

    The Notification model uses `recipient`, not `user`.
    """
    if employee is None or employee.user_id is None:
        return

    Notification.objects.create(
        recipient=employee.user,
        notification_type=Notification.NotificationType.SYSTEM,
        severity=Notification.Severity.INFO,
        title=title,
        message=message,
        url="",
        reference_type="Assignment",
        reference_id=str(assignment.id),
    )


@login_required
def admin_assignment_list(request):
    """
    Super Admin and IT Admin can view all asset assignments.

    This includes both active and returned assignments so the
    same screen can support assignment history.
    """
    if not _is_assignment_manager(request.user):
        raise PermissionDenied(
            "Only Super Admin and IT Admin can manage asset assignments."
        )

    assignments = _get_assignment_history_queryset()

    search_query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if search_query:
        assignments = assignments.filter(
            Q(asset__asset_id__icontains=search_query)
            | Q(asset__asset_name__icontains=search_query)
            | Q(asset__serial_number__icontains=search_query)
            | Q(employee__employee_id__icontains=search_query)
            | Q(employee__user__username__icontains=search_query)
            | Q(employee__user__first_name__icontains=search_query)
            | Q(employee__user__last_name__icontains=search_query)
            | Q(employee__user__email__icontains=search_query)
        )

    if status == "active":
        assignments = assignments.filter(is_active=True)
    elif status == "returned":
        assignments = assignments.filter(is_active=False)

    return render(
        request,
        "assignments/admin_assignment_list.html",
        {
            "assignments": assignments,
            "search_query": search_query,
            "selected_status": status,
        },
    )


@login_required
def admin_assignment_create(request):
    """
    Super Admin and IT Admin can assign an available asset
    to an active employee.
    """
    if not _is_assignment_manager(request.user):
        raise PermissionDenied(
            "Only Super Admin and IT Admin can assign assets."
        )

    if request.method == "POST":
        form = AssignmentForm(request.POST)

        if form.is_valid():
            selected_asset_id = form.cleaned_data["asset"].pk
            selected_employee_id = form.cleaned_data["employee"].pk

            try:
                with transaction.atomic():
                    asset = (
                        Asset.objects
                        .select_for_update()
                        .get(pk=selected_asset_id)
                    )

                    employee = get_object_or_404(
                        EmployeeProfile.objects.select_related(
                            "user",
                            "department",
                        ),
                        pk=selected_employee_id,
                    )

                    if not employee.user.is_active:
                        form.add_error(
                            "employee",
                            "An inactive employee cannot receive an asset assignment.",
                        )
                        raise ValueError("Inactive employee.")

                    if asset.status != Asset.Status.AVAILABLE:
                        form.add_error(
                            "asset",
                            "This asset is no longer available.",
                        )
                        raise ValueError("Asset no longer available.")

                    if asset.assignments.filter(
                        is_active=True,
                    ).exists():
                        form.add_error(
                            "asset",
                            "This asset already has an active assignment.",
                        )
                        raise ValueError("Active assignment exists.")

                    assignment = form.save(commit=False)

                    assignment.asset = asset
                    assignment.employee = employee
                    assignment.is_active = True
                    assignment.return_date = None
                    assignment.return_notes = ""

                    assignment.save()

                    create_audit_log(
                        user=request.user,
                        action=AuditLog.Action.ASSIGN,
                        module="Asset Assignment",
                        description=(
                            f"Asset '{asset.asset_id}' was assigned "
                            f"to employee '{employee.employee_id}'."
                        ),
                        object_type="Assignment",
                        object_id=str(assignment.id),
                        ip_address=(
                            request.META.get("HTTP_X_FORWARDED_FOR", "")
                            .split(",")[0]
                            .strip()
                            or request.META.get("REMOTE_ADDR")
                        ),
                    )

                    _notify_employee(
                        employee=employee,
                        assignment=assignment,
                        title="Asset Assigned",
                        message=(
                            f"Asset '{asset.asset_id} - "
                            f"{asset.asset_name}' has been assigned "
                            f"to you."
                        ),
                    )

            except ValueError:
                pass
            else:
                return redirect("admin_assignment_list")
    else:
        form = AssignmentForm()

    return render(
        request,
        "assignments/admin_assignment_form.html",
        {
            "form": form,
            "page_title": "Assign Asset",
            "submit_label": "Assign Asset",
        },
    )


@login_required
def admin_assignment_return(request, assignment_id):
    """
    Super Admin and IT Admin can return an actively assigned asset.
    """
    if not _is_assignment_manager(request.user):
        raise PermissionDenied(
            "Only Super Admin and IT Admin can return assets."
        )

    assignment = get_object_or_404(
        Assignment.objects.select_related(
            "asset",
            "employee__user",
            "employee__department",
        ),
        pk=assignment_id,
    )

    if not assignment.is_active:
        raise PermissionDenied(
            "This assignment has already been returned."
        )

    if request.method == "POST":
        form = AssignmentReturnForm(
            request.POST,
            instance=assignment,
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    locked_assignment = (
                        Assignment.objects
                        .select_for_update()
                        .select_related(
                            "asset",
                            "employee__user",
                        )
                        .get(pk=assignment_id)
                    )

                    if not locked_assignment.is_active:
                        form.add_error(
                            None,
                            "This assignment has already been returned.",
                        )
                        raise ValueError(
                            "Assignment already returned."
                        )

                    asset = (
                        Asset.objects
                        .select_for_update()
                        .get(pk=locked_assignment.asset_id)
                    )

                    locked_assignment.return_date = (
                        form.cleaned_data["return_date"]
                    )
                    locked_assignment.return_notes = (
                        form.cleaned_data["return_notes"]
                    )
                    locked_assignment.is_active = False

                    locked_assignment.save()

                    create_audit_log(
                        user=request.user,
                        action=AuditLog.Action.RETURN,
                        module="Asset Assignment",
                        description=(
                            f"Asset '{asset.asset_id}' was returned "
                            f"from employee "
                            f"'{locked_assignment.employee.employee_id}'."
                        ),
                        object_type="Assignment",
                        object_id=str(locked_assignment.id),
                        ip_address=(
                            request.META.get("HTTP_X_FORWARDED_FOR", "")
                            .split(",")[0]
                            .strip()
                            or request.META.get("REMOTE_ADDR")
                        ),
                    )

                    _notify_employee(
                        employee=locked_assignment.employee,
                        assignment=locked_assignment,
                        title="Asset Returned",
                        message=(
                            f"Asset '{asset.asset_id} - "
                            f"{asset.asset_name}' has been marked "
                            f"as returned."
                        ),
                    )

            except ValueError:
                pass
            else:
                return redirect(
                    "admin_assignment_list"
                )
    else:
        form = AssignmentReturnForm(
            instance=assignment,
            initial={
                "return_date": timezone.now().date(),
            },
        )

    return render(
        request,
        "assignments/admin_assignment_return.html",
        {
            "form": form,
            "assignment": assignment,
        },
    )


@login_required
def assignment_history(request):
    """
    Role-aware assignment history.

    Super Admin / IT Admin:
        Complete organization history.

    HR Manager:
        Complete assignment history because HR manages employee
        records and assigned asset information.

    Department Manager:
        Only employees belonging to their department.

    Employee:
        Only their own assignment history.
    """
    user = request.user

    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    assignments = _get_assignment_history_queryset()

    if user.role in (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
        User.Role.HR_MANAGER,
    ):
        pass

    elif user.role == User.Role.DEPARTMENT_MANAGER:
        if user.department_id is None:
            raise PermissionDenied(
                "Your Department Manager account is not linked to a department."
            )

        assignments = assignments.filter(
            employee__department_id=user.department_id,
        )

    elif user.role == User.Role.EMPLOYEE:
        employee_profile = _get_employee_profile(user)

        if employee_profile is None:
            raise PermissionDenied(
                "Your employee profile could not be found."
            )

        assignments = assignments.filter(
            employee=employee_profile,
        )

    else:
        raise PermissionDenied(
            "You do not have permission to view assignment history."
        )

    search_query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if search_query:
        assignments = assignments.filter(
            Q(asset__asset_id__icontains=search_query)
            | Q(asset__asset_name__icontains=search_query)
            | Q(asset__serial_number__icontains=search_query)
            | Q(employee__employee_id__icontains=search_query)
            | Q(employee__user__username__icontains=search_query)
            | Q(employee__user__first_name__icontains=search_query)
            | Q(employee__user__last_name__icontains=search_query)
        )

    if status == "active":
        assignments = assignments.filter(
            is_active=True,
        )
    elif status == "returned":
        assignments = assignments.filter(
            is_active=False,
        )

    return render(
        request,
        "assignments/assignment_history.html",
        {
            "assignments": assignments,
            "search_query": search_query,
            "selected_status": status,
        },
    )


@login_required
def assignment_detail(request, assignment_id):
    """
    Role-aware assignment detail.

    The queryset itself enforces the user's visibility scope,
    preventing ID-based access to another user's restricted
    assignment record.
    """
    user = request.user

    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    queryset = Assignment.objects.select_related(
        "asset",
        "asset__department",
        "employee__user",
        "employee__department",
    )

    if user.role in (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
        User.Role.HR_MANAGER,
    ):
        pass

    elif user.role == User.Role.DEPARTMENT_MANAGER:
        if user.department_id is None:
            raise PermissionDenied(
                "Your Department Manager account is not linked to a department."
            )

        queryset = queryset.filter(
            employee__department_id=user.department_id,
        )

    elif user.role == User.Role.EMPLOYEE:
        employee_profile = _get_employee_profile(user)

        if employee_profile is None:
            raise PermissionDenied(
                "Your employee profile could not be found."
            )

        queryset = queryset.filter(
            employee=employee_profile,
        )

    else:
        raise PermissionDenied(
            "You do not have permission to view assignment details."
        )

    assignment = get_object_or_404(
        queryset,
        pk=assignment_id,
    )

    return render(
        request,
        "assignments/assignment_detail.html",
        {
            "assignment": assignment,
        },
    )


@login_required
def department_manager_assignments(request):
    """
    Department Manager can view only active assignments belonging
    to employees of the manager's own department.
    """
    department = get_department_manager_department(request)

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
            "-assigned_date",
            "asset__asset_id",
        )
    )

    return render(
        request,
        "assignments/department_manager_assignments.html",
        {
            "department": department,
            "assignments": assignments,
        },
    )


@login_required
def department_manager_assignment_detail(
    request,
    assignment_id,
):
    """
    Department Manager can inspect an assignment only when the
    employee belongs to the manager's own department.
    """
    department = get_department_manager_department(request)

    assignment = get_object_or_404(
        Assignment.objects.select_related(
            "asset",
            "employee__user",
            "employee__department",
        ),
        pk=assignment_id,
        employee__department=department,
    )

    return render(
        request,
        "assignments/department_manager_assignment_detail.html",
        {
            "department": department,
            "assignment": assignment,
        },
    )


def get_department_manager_department(request):
    if not (
        request.user.is_authenticated
        and request.user.is_active
        and request.user.role == User.Role.DEPARTMENT_MANAGER
    ):
        raise PermissionDenied(
            "Only an active Department Manager can access this resource."
        )

    if request.user.department_id is None:
        raise PermissionDenied(
            "Your Department Manager account is not linked to a department."
        )

    return request.user.department