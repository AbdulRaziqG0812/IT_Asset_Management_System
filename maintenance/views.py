from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from assignments.models import Assignment
from .forms import MaintenanceRequestForm
from .models import MaintenanceRequest


@login_required
def create_maintenance_request(request):

    if request.user.role != User.Role.EMPLOYEE:
        raise PermissionDenied(
            "Only employees can create maintenance requests."
        )

    employee_profile = getattr(
        request.user,
        "employee_profile",
        None,
    )

    if employee_profile is None:
        raise PermissionDenied(
            "Employee profile is required to create a maintenance request."
        )

    assigned_assets = Assignment.objects.filter(
        employee=employee_profile,
        is_active=True,
    ).select_related("asset")

    if request.method == "POST":
        form = MaintenanceRequestForm(
            request.POST,
            employee_profile=employee_profile,
        )

        if form.is_valid():
            maintenance_request = form.save(
                commit=False
            )

            maintenance_request.employee = employee_profile
            maintenance_request.status = (
                MaintenanceRequest.Status.PENDING
            )

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

    if request.user.role != User.Role.EMPLOYEE:
        raise PermissionDenied(
            "Only employees can access maintenance requests."
        )

    employee_profile = getattr(
        request.user,
        "employee_profile",
        None,
    )

    if employee_profile is None:
        raise PermissionDenied(
            "Employee profile is required."
        )

    maintenance_requests = (
        MaintenanceRequest.objects
        .filter(employee=employee_profile)
        .select_related("asset", "employee__user")
        .order_by("-requested_at")
    )

    return render(
        request,
        "maintenance/employee_requests.html",
        {
            "maintenance_requests": maintenance_requests,
        },
    )