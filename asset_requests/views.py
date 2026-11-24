from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import EmployeeProfile, User
from audit_logs.models import AuditLog
from notifications.models import Notification

from .forms import AssetRequestForm
from .models import AssetRequest


def get_employee_profile(user):
    """
    Return the employee profile belonging to the authenticated user.

    Only Employee-role users are allowed to use employee asset-request
    functionality.
    """
    if user.role != User.Role.EMPLOYEE:
        raise PermissionDenied(
            "Only employees can access employee asset requests."
        )

    employee_profile = getattr(
        user,
        "employee_profile",
        None,
    )

    if employee_profile is None:
        raise PermissionDenied(
            "Employee profile is required to access asset requests."
        )

    return employee_profile


def _can_manage_asset_requests(user):
    """
    Return True only for active Super Admin and IT Admin users.
    """
    return (
        user.is_active
        and user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        )
    )


@login_required
def employee_asset_requests(request):
    """
    Display only the authenticated employee's own asset requests.

    Employees can see their request history and current processing status,
    but cannot access requests belonging to another employee.

    Search and pagination are handled server-side so that the employee
    always receives only their own records from the database.
    """
    employee_profile = get_employee_profile(request.user)

    asset_requests = (
        AssetRequest.objects.filter(
            employee=employee_profile
        )
        .select_related(
            "department",
            "employee__user",
            "approved_by",
        )
        .order_by(
            "-requested_at",
            "-id",
        )
    )

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    if search_query:
        search_filters = (
            Q(asset_category__icontains=search_query)
            | Q(asset_name__icontains=search_query)
            | Q(reason__icontains=search_query)
            | Q(status__icontains=search_query)
            | Q(priority__icontains=search_query)
            | Q(department__name__icontains=search_query)
        )

        if search_query.isdigit():
            search_filters |= Q(id=int(search_query))

        asset_requests = asset_requests.filter(
            search_filters
        )

    paginator = Paginator(
        asset_requests,
        5,
    )

    page_number = request.GET.get(
        "page",
        1,
    )

    page_obj = paginator.get_page(
        page_number
    )

    return render(
        request,
        "asset_requests/employee_requests.html",
        {
            "asset_requests": page_obj.object_list,
            "page_obj": page_obj,
            "search_query": search_query,
        },
    )


@login_required
def create_asset_request(request):
    """
    Allow an active employee to create an asset request.

    Employee identity, department, status, approval fields and processing
    fields are controlled exclusively by the server.
    """
    employee_profile = get_employee_profile(request.user)

    if employee_profile.employment_status != (
        EmployeeProfile.EmploymentStatus.ACTIVE
    ):
        raise PermissionDenied(
            "Only active employees can create asset requests."
        )

    if employee_profile.department is None:
        raise PermissionDenied(
            "Your employee profile is not linked to a department."
        )

    if request.method == "POST":
        form = AssetRequestForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                asset_request = form.save(
                    commit=False
                )

                # ------------------------------------------------------
                # Security-controlled fields
                # ------------------------------------------------------

                # Never trust employee_id or department_id from the client.
                asset_request.employee = employee_profile
                asset_request.department = (
                    employee_profile.department
                )

                # Every newly submitted employee request starts as PENDING.
                asset_request.status = (
                    AssetRequest.Status.PENDING
                )

                # Approval information must always start empty.
                asset_request.approved_by = None
                asset_request.processed_at = None
                asset_request.manager_notes = ""

                asset_request.save()

            return redirect(
                "employee_asset_requests"
            )

    else:
        form = AssetRequestForm()

    return render(
        request,
        "asset_requests/create_request.html",
        {
            "form": form,
        },
    )


@login_required
def admin_asset_requests(request):
    """
    Display asset requests for Super Admin and IT Admin.

    Security:
    - Only active Super Admin and IT Admin users can access.
    - All requests are loaded with their related employee,
      department and processing user.
    - Search and filters are applied server-side.
    """
    user = request.user

    if not _can_manage_asset_requests(user):
        raise PermissionDenied(
            "Only Super Admin and IT Admin can manage asset requests."
        )

    asset_requests = (
        AssetRequest.objects
        .select_related(
            "employee",
            "employee__user",
            "department",
            "approved_by",
        )
        .order_by(
            "-requested_at",
            "-id",
        )
    )

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    status = request.GET.get(
        "status",
        "",
    ).strip().upper()

    priority = request.GET.get(
        "priority",
        "",
    ).strip().upper()

    if search_query:
        search_filters = (
            Q(asset_category__icontains=search_query)
            | Q(asset_name__icontains=search_query)
            | Q(reason__icontains=search_query)
            | Q(employee__employee_id__icontains=search_query)
            | Q(employee__user__username__icontains=search_query)
            | Q(employee__user__first_name__icontains=search_query)
            | Q(employee__user__last_name__icontains=search_query)
            | Q(department__name__icontains=search_query)
        )

        if search_query.isdigit():
            search_filters |= Q(id=int(search_query))

        asset_requests = asset_requests.filter(
            search_filters
        )

    if status in dict(AssetRequest.Status.choices):
        asset_requests = asset_requests.filter(
            status=status
        )

    if priority in dict(AssetRequest.Priority.choices):
        asset_requests = asset_requests.filter(
            priority=priority
        )

    paginator = Paginator(
        asset_requests,
        10,
    )

    page_number = request.GET.get(
        "page",
        1,
    )

    page_obj = paginator.get_page(
        page_number
    )

    return render(
        request,
        "asset_requests/admin_requests.html",
        {
            "asset_requests": page_obj.object_list,
            "page_obj": page_obj,
            "search_query": search_query,
            "selected_status": status,
            "selected_priority": priority,
            "statuses": AssetRequest.Status.choices,
            "priorities": AssetRequest.Priority.choices,
        },
    )


@login_required
def admin_asset_request_process(
    request,
    request_id,
):
    """
    Approve or reject an employee asset request.

    Security:
    - Only active Super Admin and IT Admin users can process.
    - Processing is POST-only.
    - Only Pending requests can be processed.
    - The authenticated admin is always stored as approved_by.
    - processed_at is generated server-side.
    - The browser cannot control the processing administrator.
    - The model remains responsible for validating the final state.
    """
    user = request.user

    if not _can_manage_asset_requests(user):
        raise PermissionDenied(
            "Only Super Admin and IT Admin can process asset requests."
        )

    if request.method != "POST":
        raise PermissionDenied(
            "Asset request processing must be submitted using POST."
        )

    asset_request = get_object_or_404(
        AssetRequest.objects.select_related(
            "employee",
            "employee__user",
            "department",
        ),
        pk=request_id,
    )

    if asset_request.status != AssetRequest.Status.PENDING:
        messages.error(
            request,
            (
                f"Asset request #{asset_request.id} has already "
                "been processed and cannot be changed."
            ),
        )

        return redirect(
            "admin_asset_requests"
        )

    decision = request.POST.get(
        "decision",
        "",
    ).strip().upper()

    if decision not in (
        AssetRequest.Status.APPROVED,
        AssetRequest.Status.REJECTED,
    ):
        messages.error(
            request,
            "Invalid asset request processing action.",
        )

        return redirect(
            "admin_asset_requests"
        )

    manager_notes = request.POST.get(
        "manager_notes",
        "",
    ).strip()

    if len(manager_notes) > 5000:
        messages.error(
            request,
            "Manager notes cannot exceed 5000 characters.",
        )

        return redirect(
            "admin_asset_requests"
        )

    employee_user = asset_request.employee.user

    with transaction.atomic():
        asset_request.status = decision

        # The authenticated administrator is always used.
        asset_request.approved_by = user

        # The timestamp is generated by the server.
        asset_request.processed_at = timezone.now()

        asset_request.manager_notes = manager_notes

        asset_request.save()

        if decision == AssetRequest.Status.APPROVED:
            audit_description = (
                f"Asset request #{asset_request.id} was approved. "
                f"Employee '{asset_request.employee.employee_id}' "
                f"requested {asset_request.quantity} "
                f"unit(s) of '{asset_request.asset_category}'."
            )

            notification_title = (
                "Asset Request Approved"
            )

            notification_message = (
                f"Your asset request #{asset_request.id} "
                f"for {asset_request.quantity} unit(s) of "
                f"{asset_request.asset_category} has been approved."
            )

            notification_severity = (
                Notification.Severity.SUCCESS
            )

            success_message = (
                f"Asset request #{asset_request.id} "
                "was approved successfully."
            )

        else:
            audit_description = (
                f"Asset request #{asset_request.id} was rejected. "
                f"Employee '{asset_request.employee.employee_id}' "
                f"requested {asset_request.quantity} "
                f"unit(s) of '{asset_request.asset_category}'."
            )

            notification_title = (
                "Asset Request Rejected"
            )

            notification_message = (
                f"Your asset request #{asset_request.id} "
                f"for {asset_request.quantity} unit(s) of "
                f"{asset_request.asset_category} has been rejected."
            )

            notification_severity = (
                Notification.Severity.WARNING
            )

            success_message = (
                f"Asset request #{asset_request.id} "
                "was rejected successfully."
            )

        create_audit_log(
            user=user,
            action=AuditLog.Action.UPDATE,
            module="Asset Requests",
            description=audit_description,
            object_type="AssetRequest",
            object_id=asset_request.id,
            ip_address=request.META.get(
                "REMOTE_ADDR"
            ),
        )

        if employee_user.is_active:
            Notification.objects.create(
                recipient=employee_user,
                notification_type=(
                    Notification.NotificationType.SYSTEM
                ),
                severity=notification_severity,
                title=notification_title,
                message=notification_message,
                url="",
                reference_type="AssetRequest",
                reference_id=str(
                    asset_request.id
                ),
            )

    messages.success(
        request,
        success_message,
    )

    return redirect(
        "admin_asset_requests"
    )