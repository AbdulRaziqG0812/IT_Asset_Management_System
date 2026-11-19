from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from accounts.models import User
from .models import Assignment


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