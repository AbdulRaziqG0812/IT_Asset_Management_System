from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User

from .forms import (
    SoftwareLicenseAssignmentForm,
    SoftwareLicenseForm,
)
from .models import (
    SoftwareLicense,
    SoftwareLicenseAssignment,
)


def is_software_license_admin(user):
    """
    Only Super Admin and IT Admin can manage software licenses.
    """

    return (
        user.is_authenticated
        and user.is_active
        and user.role
        in {
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        }
    )


def require_software_license_admin(user):
    """
    Raise PermissionDenied when the current user is not
    authorized to manage software licenses.
    """

    if not is_software_license_admin(user):
        raise PermissionDenied(
            "You do not have permission to manage software licenses."
        )


@login_required
def software_license_list(request):
    """
    Display all software licenses.

    Access:
    - Super Admin
    - IT Admin
    """

    require_software_license_admin(request.user)

    licenses = (
        SoftwareLicense.objects
        .all()
        .order_by(
            "software_name",
            "version",
            "id",
        )
    )

    summary = {
        "total": licenses.count(),
        "active": licenses.filter(
            status=SoftwareLicense.Status.ACTIVE
        ).count(),
        "expiring_soon": licenses.filter(
            status=SoftwareLicense.Status.EXPIRING_SOON
        ).count(),
        "expired": licenses.filter(
            status=SoftwareLicense.Status.EXPIRED
        ).count(),
    }

    return render(
        request,
        "software_licenses/list.html",
        {
            "licenses": licenses,
            "summary": summary,
        },
    )


@login_required
def software_license_create(request):
    """
    Create a new software license.

    Only POST requests can create records.
    """

    require_software_license_admin(request.user)

    if request.method == "POST":
        form = SoftwareLicenseForm(request.POST)

        if form.is_valid():
            license_obj = form.save()

            messages.success(
                request,
                (
                    f"Software license for "
                    f"'{license_obj.software_name}' "
                    "was created successfully."
                ),
            )

            return redirect("software_license_list")

    else:
        form = SoftwareLicenseForm()

    return render(
        request,
        "software_licenses/form.html",
        {
            "form": form,
            "page_title": "Add Software License",
            "submit_label": "Create License",
        },
    )


@login_required
def software_license_edit(request, license_id):
    """
    Edit an existing software license.

    Only POST requests can modify the record.
    """

    require_software_license_admin(request.user)

    license_obj = get_object_or_404(
        SoftwareLicense,
        pk=license_id,
    )

    if request.method == "POST":
        form = SoftwareLicenseForm(
            request.POST,
            instance=license_obj,
        )

        if form.is_valid():
            license_obj = form.save()

            messages.success(
                request,
                (
                    f"Software license for "
                    f"'{license_obj.software_name}' "
                    "was updated successfully."
                ),
            )

            return redirect("software_license_list")

    else:
        form = SoftwareLicenseForm(
            instance=license_obj,
        )

    return render(
        request,
        "software_licenses/form.html",
        {
            "form": form,
            "license": license_obj,
            "page_title": "Edit Software License",
            "submit_label": "Save Changes",
        },
    )


@login_required
def software_license_delete(request, license_id):
    """
    Delete a software license.

    Deletion is POST-only.

    A license with existing assignment history cannot be deleted
    because SoftwareLicenseAssignment uses PROTECT.
    """

    require_software_license_admin(request.user)

    if request.method != "POST":
        raise PermissionDenied(
            "Software licenses can only be deleted using POST."
        )

    license_obj = get_object_or_404(
        SoftwareLicense,
        pk=license_id,
    )

    software_name = license_obj.software_name

    try:
        license_obj.delete()

    except Exception:
        messages.error(
            request,
            (
                f"'{software_name}' could not be deleted because "
                "it is associated with existing assignment records."
            ),
        )

        return redirect("software_license_list")

    messages.success(
        request,
        (
            f"Software license for "
            f"'{software_name}' was deleted successfully."
        ),
    )

    return redirect("software_license_list")


@login_required
def software_license_assignment_list(
    request,
    license_id,
):
    """
    Display assignment history for one software license.
    """

    require_software_license_admin(request.user)

    license_obj = get_object_or_404(
        SoftwareLicense,
        pk=license_id,
    )

    assignments = (
        SoftwareLicenseAssignment.objects
        .filter(
            license=license_obj,
        )
        .select_related(
            "employee",
            "employee__user",
            "employee__department",
        )
        .order_by(
            "-is_active",
            "-assigned_date",
            "-id",
        )
    )

    return render(
        request,
        "software_licenses/assignments.html",
        {
            "license": license_obj,
            "assignments": assignments,
        },
    )


@login_required
def software_license_assign(
    request,
    license_id,
):
    """
    Assign a software license to an active employee.

    Assignment is POST-only.
    """

    require_software_license_admin(request.user)

    license_obj = get_object_or_404(
        SoftwareLicense,
        pk=license_id,
    )

    if request.method == "POST":
        form = SoftwareLicenseAssignmentForm(
            request.POST,
            license_obj=license_obj,
        )

        if form.is_valid():

            with transaction.atomic():
                assignment = form.save(
                    commit=False,
                )

                assignment.license = license_obj
                assignment.is_active = True
                assignment.returned_date = None

                assignment.save()

            messages.success(
                request,
                (
                    f"Software license "
                    f"'{license_obj.software_name}' "
                    "was assigned successfully."
                ),
            )

            return redirect(
                "software_license_assignment_list",
                license_id=license_obj.pk,
            )

    else:
        form = SoftwareLicenseAssignmentForm(
            license_obj=license_obj,
        )

    return render(
        request,
        "software_licenses/assignment_form.html",
        {
            "form": form,
            "license": license_obj,
            "page_title": "Assign Software License",
            "submit_label": "Assign License",
        },
    )


@login_required
def software_license_return(
    request,
    assignment_id,
):
    """
    Return an active software license assignment.

    This operation is POST-only.
    """

    require_software_license_admin(request.user)

    if request.method != "POST":
        raise PermissionDenied(
            "Software license returns can only be processed using POST."
        )

    assignment = get_object_or_404(
        SoftwareLicenseAssignment.objects.select_related(
            "license",
            "employee",
            "employee__user",
        ),
        pk=assignment_id,
    )

    if not assignment.is_active:
        messages.info(
            request,
            "This software license assignment has already been returned.",
        )

        return redirect(
            "software_license_assignment_list",
            license_id=assignment.license_id,
        )

    with transaction.atomic():

        assignment.is_active = False
        assignment.save()

    employee_name = (
        assignment.employee.user.get_full_name().strip()
        or assignment.employee.user.username
    )

    messages.success(
        request,
        (
            f"Software license assigned to "
            f"'{employee_name}' "
            "was returned successfully."
        ),
    )

    return redirect(
        "software_license_assignment_list",
        license_id=assignment.license_id,
    )