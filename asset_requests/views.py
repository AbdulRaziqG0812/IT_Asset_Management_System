from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect, render

from accounts.models import EmployeeProfile, User

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

    employee_profile = getattr(user, "employee_profile", None)

    if employee_profile is None:
        raise PermissionDenied(
            "Employee profile is required to access asset requests."
        )

    return employee_profile


@login_required
def employee_asset_requests(request):
    """
    Display only the authenticated employee's own asset requests.

    Employees can see their request history and current processing status,
    but cannot access requests belonging to another employee.
    """
    employee_profile = get_employee_profile(request.user)

    requests = (
        AssetRequest.objects.filter(
            employee=employee_profile
        )
        .select_related(
            "department",
            "employee__user",
            "approved_by",
        )
        .order_by("-requested_at", "-id")
    )

    return render(
        request,
        "asset_requests/employee_requests.html",
        {
            "asset_requests": requests,
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

    if employee_profile.employment_status != EmployeeProfile.EmploymentStatus.ACTIVE:
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
                asset_request = form.save(commit=False)

                # ------------------------------------------------------
                # Security-controlled fields
                # ------------------------------------------------------

                # Never trust employee_id or department_id from the client.
                asset_request.employee = employee_profile
                asset_request.department = employee_profile.department

                # Every newly submitted employee request starts as PENDING.
                asset_request.status = AssetRequest.Status.PENDING

                # Approval information must always start empty.
                asset_request.approved_by = None
                asset_request.processed_at = None
                asset_request.manager_notes = ""

                asset_request.save()

            return redirect("employee_asset_requests")

    else:
        form = AssetRequestForm()

    return render(
        request,
        "asset_requests/create_request.html",
        {
            "form": form,
        },
    )