from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User

from .forms import SoftwareLicenseAssignmentForm, SoftwareLicenseForm
from .models import SoftwareLicense, SoftwareLicenseAssignment


def is_software_license_admin(user):
    return (
        user.is_authenticated
        and user.is_active
        and user.role in {
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        }
    )


def require_software_license_admin(user):
    if not is_software_license_admin(user):
        raise PermissionDenied(
            "You do not have permission to manage software licenses."
        )


@login_required
def software_license_list(request):
    require_software_license_admin(request.user)

    # =========================================================
    # SEARCH
    # =========================================================

    search_query = request.GET.get("search", "").strip()

    all_licenses = SoftwareLicense.objects.all()

    licenses_queryset = all_licenses

    if search_query:
        licenses_queryset = licenses_queryset.filter(
            Q(software_name__icontains=search_query)
            | Q(version__icontains=search_query)
            | Q(license_key__icontains=search_query)
            | Q(vendor_name__icontains=search_query)
            | Q(license_type__icontains=search_query)
            | Q(status__icontains=search_query)
        )

    # =========================================================
    # SUMMARY
    # Summary always represents all licenses.
    # Search does not change these totals.
    # =========================================================

    summary = {
        "total": all_licenses.count(),
        "active": all_licenses.filter(
            status=SoftwareLicense.Status.ACTIVE
        ).count(),
        "expiring_soon": all_licenses.filter(
            status=SoftwareLicense.Status.EXPIRING_SOON
        ).count(),
        "expired": all_licenses.filter(
            status=SoftwareLicense.Status.EXPIRED
        ).count(),
    }

    # =========================================================
    # ORDERING
    # =========================================================

    licenses_queryset = licenses_queryset.order_by(
        "software_name",
        "version",
        "id",
    )

    # =========================================================
    # PAGINATION
    # =========================================================

    paginator = Paginator(licenses_queryset, 10)

    page_number = request.GET.get("page", 1)

    page_obj = paginator.get_page(page_number)

    # =========================================================
    # PAGE RANGE
    # =========================================================

    page_range = paginator.get_elided_page_range(
        number=page_obj.number,
        on_each_side=2,
        on_ends=1,
    )

    return render(
        request,
        "software_licenses/list.html",
        {
            "licenses": page_obj,
            "page_obj": page_obj,
            "paginator": paginator,
            "page_range": page_range,
            "summary": summary,
            "search_query": search_query,
        },
    )


@login_required
def software_license_create(request):
    require_software_license_admin(request.user)

    if request.method == "POST":
        form = SoftwareLicenseForm(request.POST)

        if form.is_valid():
            license_obj = form.save()

            messages.success(
                request,
                f"Software license for '{license_obj.software_name}' "
                f"was created successfully.",
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
                f"Software license for '{license_obj.software_name}' "
                f"was updated successfully.",
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
            f"'{software_name}' could not be deleted because it is "
            f"associated with existing assignment records.",
        )

        return redirect("software_license_list")

    messages.success(
        request,
        f"Software license for '{software_name}' "
        f"was deleted successfully.",
    )

    return redirect("software_license_list")


@login_required
def software_license_assignment_list(request, license_id):
    require_software_license_admin(request.user)

    license_obj = get_object_or_404(
        SoftwareLicense,
        pk=license_id,
    )

    # =========================================================
    # SEARCH
    # =========================================================

    search_query = request.GET.get("search", "").strip()

    assignments_queryset = (
        SoftwareLicenseAssignment.objects
        .filter(license=license_obj)
        .select_related(
            "employee",
            "employee__user",
            "employee__department",
        )
    )

    if search_query:

        search_filter = (
            Q(employee__user__first_name__icontains=search_query)
            | Q(employee__user__last_name__icontains=search_query)
            | Q(employee__user__username__icontains=search_query)
            | Q(employee__employee_id__icontains=search_query)
            | Q(employee__department__name__icontains=search_query)
            | Q(notes__icontains=search_query)
        )

        # Allow searching by assignment status.
        status_query = search_query.lower()

        if status_query == "active":
            search_filter |= Q(is_active=True)

        elif status_query == "returned":
            search_filter |= Q(is_active=False)

        assignments_queryset = assignments_queryset.filter(
            search_filter
        )

    # =========================================================
    # ORDERING
    # =========================================================

    assignments_queryset = assignments_queryset.order_by(
        "-is_active",
        "-assigned_date",
        "-id",
    )

    # =========================================================
    # PAGINATION
    # =========================================================

    paginator = Paginator(
        assignments_queryset,
        10,
    )

    page_number = request.GET.get("page", 1)

    page_obj = paginator.get_page(page_number)

    # =========================================================
    # PAGE RANGE
    # =========================================================

    page_range = paginator.get_elided_page_range(
        number=page_obj.number,
        on_each_side=2,
        on_ends=1,
    )

    return render(
        request,
        "software_licenses/assignments.html",
        {
            "license": license_obj,
            "assignments": page_obj,
            "page_obj": page_obj,
            "paginator": paginator,
            "page_range": page_range,
            "search_query": search_query,
        },
    )


@login_required
def software_license_assign(request, license_id):
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
                    commit=False
                )

                assignment.license = license_obj
                assignment.is_active = True
                assignment.returned_date = None

                assignment.save()

            messages.success(
                request,
                f"Software license '{license_obj.software_name}' "
                f"was assigned successfully.",
            )

            return redirect(
                "software_license_assignment_list",
                license_id=license_obj.pk,
            )

    else:

        form = SoftwareLicenseAssignmentForm(
            license_obj=license_obj
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
def software_license_return(request, assignment_id):
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
        f"Software license assigned to '{employee_name}' "
        f"was returned successfully.",
    )

    return redirect(
        "software_license_assignment_list",
        license_id=assignment.license_id,
    )