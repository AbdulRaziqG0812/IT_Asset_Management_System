
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import EmployeeProfile, User
from assignments.models import Assignment
from notifications.models import Notification

from .forms import MaintenanceRequestForm
from .models import MaintenanceRequest


def get_employee_profile(user):
    """
    Return the employee profile for the authenticated employee.

    Only Employee-role users can use employee maintenance functionality.
    """
    if user.role != User.Role.EMPLOYEE:
        raise PermissionDenied(
            "Only employees can access employee maintenance requests."
        )

    employee_profile = getattr(
        user,
        "employee_profile",
        None,
    )

    if employee_profile is None:
        raise PermissionDenied(
            "Employee profile is required to access maintenance requests."
        )

    return employee_profile


def can_manage_maintenance(user):
    """
    Return True only for users who are authorized to manage
    maintenance requests.
    """
    return user.role in (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
    )


@login_required
def create_maintenance_request(request):
    """
    Allow an active employee to create a maintenance/repair request
    only for an asset currently assigned to that employee.
    """
    employee_profile = get_employee_profile(request.user)

    if employee_profile.employment_status != (
        EmployeeProfile.EmploymentStatus.ACTIVE
    ):
        raise PermissionDenied(
            "Only active employees can create maintenance requests."
        )

    assigned_assets = (
        Assignment.objects
        .filter(
            employee=employee_profile,
            is_active=True,
            asset__status="ASSIGNED",
        )
        .select_related("asset")
        .order_by("asset__asset_id")
    )

    if request.method == "POST":
        form = MaintenanceRequestForm(
            request.POST,
            employee_profile=employee_profile,
        )

        if form.is_valid():
            with transaction.atomic():
                maintenance_request = form.save(
                    commit=False
                )

                # Security-controlled fields.
                maintenance_request.employee = employee_profile
                maintenance_request.status = (
                    MaintenanceRequest.Status.PENDING
                )
                maintenance_request.technician_notes = ""
                maintenance_request.resolution_notes = ""
                maintenance_request.started_at = None
                maintenance_request.completed_at = None

                maintenance_request.save()

            return redirect(
                "employee_maintenance_requests"
            )

    else:
        form = MaintenanceRequestForm(
            employee_profile=employee_profile,
        )

    return render(
        request,
        "maintenance/create_request.html",
        {
            "form": form,
            "assigned_assets": assigned_assets,
        },
    )


@login_required
def employee_maintenance_requests(request):
    """
    Display only the authenticated employee's own maintenance requests.
    """
    employee_profile = get_employee_profile(request.user)

    maintenance_requests = (
        MaintenanceRequest.objects
        .filter(
            employee=employee_profile
        )
        .select_related(
            "asset",
            "employee__user",
        )
        .order_by(
            "-requested_at",
            "-id",
        )
    )

    return render(
        request,
        "maintenance/employee_requests.html",
        {
            "maintenance_requests": maintenance_requests,
        },
    )


@login_required
def admin_maintenance_list(request):
    """
    Display maintenance requests for Super Admin and IT Admin.

    This view is read-only. Status processing is handled separately.
    """
    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if not can_manage_maintenance(user):
        raise PermissionDenied(
            "Only Super Admin and IT Admin can manage maintenance requests."
        )

    maintenance_requests = (
        MaintenanceRequest.objects
        .select_related(
            "asset",
            "employee",
            "employee__user",
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

    selected_status = request.GET.get(
        "status",
        "",
    ).strip().upper()

    selected_priority = request.GET.get(
        "priority",
        "",
    ).strip().upper()

    selected_request_type = request.GET.get(
        "type",
        "",
    ).strip().upper()

    if search_query:
        maintenance_requests = maintenance_requests.filter(
            Q(asset__asset_id__icontains=search_query)
            | Q(asset__asset_name__icontains=search_query)
            | Q(employee__employee_id__icontains=search_query)
            | Q(employee__user__username__icontains=search_query)
            | Q(employee__user__first_name__icontains=search_query)
            | Q(employee__user__last_name__icontains=search_query)
            | Q(issue_description__icontains=search_query)
        )

    valid_statuses = {
        value
        for value, _label in MaintenanceRequest.Status.choices
    }

    valid_priorities = {
        value
        for value, _label in MaintenanceRequest.Priority.choices
    }

    valid_request_types = {
        value
        for value, _label in MaintenanceRequest.RequestType.choices
    }

    if selected_status in valid_statuses:
        maintenance_requests = maintenance_requests.filter(
            status=selected_status
        )
    else:
        selected_status = ""

    if selected_priority in valid_priorities:
        maintenance_requests = maintenance_requests.filter(
            priority=selected_priority
        )
    else:
        selected_priority = ""

    if selected_request_type in valid_request_types:
        maintenance_requests = maintenance_requests.filter(
            request_type=selected_request_type
        )
    else:
        selected_request_type = ""

    total_requests = maintenance_requests.count()

    pending_requests = maintenance_requests.filter(
        status=MaintenanceRequest.Status.PENDING
    ).count()

    in_progress_requests = maintenance_requests.filter(
        status=MaintenanceRequest.Status.IN_PROGRESS
    ).count()

    completed_requests = maintenance_requests.filter(
        status=MaintenanceRequest.Status.COMPLETED
    ).count()

    return render(
        request,
        "maintenance/admin_maintenance_list.html",
        {
            "maintenance_requests": maintenance_requests,
            "search_query": search_query,
            "selected_status": selected_status,
            "selected_priority": selected_priority,
            "selected_request_type": selected_request_type,
            "statuses": MaintenanceRequest.Status.choices,
            "priorities": MaintenanceRequest.Priority.choices,
            "request_types": MaintenanceRequest.RequestType.choices,
            "total_requests": total_requests,
            "pending_requests": pending_requests,
            "in_progress_requests": in_progress_requests,
            "completed_requests": completed_requests,
        },
    )


@login_required
def admin_maintenance_process(request, maintenance_id):
    """
    Process a maintenance request for Super Admin and IT Admin.

    Allowed transitions are enforced both here and by the model:

        PENDING -> IN_PROGRESS
        PENDING -> REJECTED
        IN_PROGRESS -> COMPLETED
        IN_PROGRESS -> REJECTED
    """
    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if not can_manage_maintenance(user):
        raise PermissionDenied(
            "Only Super Admin and IT Admin can process maintenance requests."
        )

    if request.method != "POST":
        raise PermissionDenied(
            "Maintenance request processing must be submitted using POST."
        )

    maintenance_request = get_object_or_404(
        MaintenanceRequest.objects.select_related(
            "asset",
            "employee",
            "employee__user",
        ),
        pk=maintenance_id,
    )

    decision = request.POST.get(
        "decision",
        "",
    ).strip().upper()

    allowed_decisions = {
        MaintenanceRequest.Status.IN_PROGRESS,
        MaintenanceRequest.Status.COMPLETED,
        MaintenanceRequest.Status.REJECTED,
    }

    if decision not in allowed_decisions:
        return redirect("maintenance_list")

    current_status = maintenance_request.status

    allowed_transitions = {
        MaintenanceRequest.Status.PENDING: {
            MaintenanceRequest.Status.IN_PROGRESS,
            MaintenanceRequest.Status.REJECTED,
        },
        MaintenanceRequest.Status.IN_PROGRESS: {
            MaintenanceRequest.Status.COMPLETED,
            MaintenanceRequest.Status.REJECTED,
        },
    }

    if decision not in allowed_transitions.get(
        current_status,
        set(),
    ):
        return redirect("maintenance_list")

    technician_notes = request.POST.get(
        "technician_notes",
        "",
    ).strip()

    resolution_notes = request.POST.get(
        "resolution_notes",
        "",
    ).strip()

    if len(technician_notes) > 10000:
        return redirect("maintenance_list")

    if len(resolution_notes) > 10000:
        return redirect("maintenance_list")

    employee_user = maintenance_request.employee.user

    with transaction.atomic():

        maintenance_request.status = decision

        if technician_notes:
            maintenance_request.technician_notes = technician_notes

        if resolution_notes:
            maintenance_request.resolution_notes = resolution_notes

        maintenance_request.save()

        if employee_user.is_active:

            if decision == MaintenanceRequest.Status.IN_PROGRESS:

                Notification.objects.create(
                    recipient=employee_user,
                    notification_type=Notification.NotificationType.MAINTENANCE,
                    severity=Notification.Severity.INFO,
                    title="Maintenance Request In Progress",
                    message=(
                        f"Your maintenance request #{maintenance_request.id} "
                        f"for asset {maintenance_request.asset.asset_id} "
                        "has been marked as In Progress."
                    ),
                    url="/maintenance/",
                    reference_type="MaintenanceRequest",
                    reference_id=str(maintenance_request.id),
                )

            elif decision == MaintenanceRequest.Status.COMPLETED:

                Notification.objects.create(
                    recipient=employee_user,
                    notification_type=Notification.NotificationType.MAINTENANCE,
                    severity=Notification.Severity.SUCCESS,
                    title="Maintenance Request Completed",
                    message=(
                        f"Your maintenance request #{maintenance_request.id} "
                        f"for asset {maintenance_request.asset.asset_id} "
                        "has been completed."
                    ),
                    url="/maintenance/",
                    reference_type="MaintenanceRequest",
                    reference_id=str(maintenance_request.id),
                )

            elif decision == MaintenanceRequest.Status.REJECTED:

                Notification.objects.create(
                    recipient=employee_user,
                    notification_type=Notification.NotificationType.MAINTENANCE,
                    severity=Notification.Severity.DANGER,
                    title="Maintenance Request Rejected",
                    message=(
                        f"Your maintenance request #{maintenance_request.id} "
                        f"for asset {maintenance_request.asset.asset_id} "
                        "has been rejected."
                    ),
                    url="/maintenance/",
                    reference_type="MaintenanceRequest",
                    reference_id=str(maintenance_request.id),
                )

    return redirect("maintenance_list")