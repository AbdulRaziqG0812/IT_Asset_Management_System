from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect

from accounts.models import User
from .models import AssetRequest
from .forms import AssetRequestForm


@login_required
def employee_asset_requests(request):
    """
    Employee can only view their own asset requests.
    """

    if request.user.role != User.Role.EMPLOYEE:
        raise PermissionDenied(
            f"Invalid role: {request.user.role}"
        )

    employee_profile = getattr(request.user, "employee_profile", None)

    if employee_profile is None:
        raise PermissionDenied(
            "Employee profile is required to access asset requests."
        )

    requests = AssetRequest.objects.filter(
        employee=employee_profile
    ).select_related(
        "department",
        "employee__user",
        "approved_by",
    ).order_by("-requested_at")

    return render(
        request,
        "asset_requests/employee_requests.html",
        {
            "asset_requests": requests,
        },
    )

@login_required
def create_asset_request(request):
    if request.user.role != User.Role.EMPLOYEE:
        raise PermissionDenied("Only employees can create asset requests.")

    employee_profile = getattr(request.user, "employee_profile", None)

    if employee_profile is None:
        raise PermissionDenied(
            "Employee profile is required to create an asset request."
        )

    if employee_profile.department is None:
        raise PermissionDenied(
            "Your employee profile is not linked to a department."
        )

    if request.method == "POST":
        form = AssetRequestForm(request.POST)

        if form.is_valid():
            asset_request = form.save(commit=False)

            # These values are controlled by the server.
            asset_request.employee = employee_profile
            asset_request.department = employee_profile.department
            asset_request.status = AssetRequest.Status.PENDING

            # Approval-related fields remain untouched.
            asset_request.approved_by = None
            asset_request.processed_at = None

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