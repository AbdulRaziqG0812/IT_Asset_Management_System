from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect, render

from accounts.models import EmployeeProfile, User
from assignments.models import Assignment

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