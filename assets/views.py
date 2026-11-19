from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from accounts.models import User
from .models import Asset


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


@login_required
def department_manager_assets(request):
    """
    Department Manager can view only assets assigned to their
    own department.
    """

    department = get_department_manager_department(request)

    assets = (
        Asset.objects
        .filter(department=department)
        .select_related("department")
        .order_by("asset_id")
    )

    return render(
        request,
        "assets/department_manager_assets.html",
        {
            "department": department,
            "assets": assets,
        },
    )


@login_required
def department_manager_asset_detail(
    request,
    asset_id,
):
    """
    Asset access is strictly scoped to the manager's department.
    """

    department = get_department_manager_department(request)

    asset = get_object_or_404(
        Asset.objects.select_related("department"),
        pk=asset_id,
        department=department,
    )

    return render(
        request,
        "assets/department_manager_asset_detail.html",
        {
            "department": department,
            "asset": asset,
        },
    )