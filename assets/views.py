from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from accounts.models import EmployeeProfile, User
from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log
from notifications.models import Notification

from .forms import AssetForm, AssetIncidentForm
from .models import Asset, AssetIncident


def _can_manage_assets(user):
    return user.role in (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
    )


def _can_view_assets(user):
    return user.role in (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
        User.Role.HR_MANAGER,
        User.Role.DEPARTMENT_MANAGER,
        User.Role.EMPLOYEE,
    )


def _get_asset_queryset_for_user(user):
    queryset = (
        Asset.objects
        .select_related("department")
        .order_by("-id")
    )

    if user.role in (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
        User.Role.HR_MANAGER,
    ):
        return queryset

    if user.role == User.Role.DEPARTMENT_MANAGER:
        if user.department_id is None:
            return queryset.none()

        return queryset.filter(
            department_id=user.department_id
        )

    if user.role == User.Role.EMPLOYEE:
        return queryset.filter(
            assignments__employee__user=user,
            assignments__is_active=True,
        ).distinct()

    return queryset.none()


def _has_active_assignment(asset):
    return asset.assignments.filter(
        is_active=True
    ).exists()


@login_required
def asset_list(request):
    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if not _can_view_assets(user):
        raise PermissionDenied(
            "You do not have permission to view assets."
        )

    assets = _get_asset_queryset_for_user(user)

    search_query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    status = request.GET.get("status", "").strip()
    condition = request.GET.get("condition", "").strip()
    department = request.GET.get("department", "").strip()

    if search_query:
        assets = assets.filter(
            Q(asset_id__icontains=search_query)
            | Q(asset_name__icontains=search_query)
            | Q(serial_number__icontains=search_query)
            | Q(brand_model__icontains=search_query)
            | Q(vendor_name__icontains=search_query)
        )

    if category:
        assets = assets.filter(category=category)

    if status:
        assets = assets.filter(status=status)

    if condition:
        assets = assets.filter(condition=condition)

    if department:
        assets = assets.filter(department_id=department)

    context = {
        "assets": assets,
        "search_query": search_query,
        "selected_category": category,
        "selected_status": status,
        "selected_condition": condition,
        "selected_department": department,
        "categories": Asset.Category.choices,
        "statuses": Asset.Status.choices,
        "conditions": Asset.Condition.choices,
        "can_manage": _can_manage_assets(user),
        "can_delete": user.role == User.Role.SUPER_ADMIN,
    }

    return render(
        request,
        "assets/asset_list.html",
        context,
    )


@login_required
def asset_detail(request, asset_id):
    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if user.role == User.Role.EMPLOYEE:
        return redirect(
            "employee_asset_detail",
            asset_id=asset_id,
        )

    if not _can_view_assets(user):
        raise PermissionDenied(
            "You do not have permission to view assets."
        )

    asset = get_object_or_404(
        _get_asset_queryset_for_user(user),
        pk=asset_id,
    )

    assignment_history = (
        asset.assignments
        .select_related(
            "employee",
            "employee__user",
            "employee__department",
        )
        .order_by(
            "-assigned_date",
            "-id",
        )
    )

    has_active_assignment = _has_active_assignment(asset)

    can_retire = (
        _can_manage_assets(user)
        and asset.status not in (
            Asset.Status.RETIRED,
            Asset.Status.DISPOSED,
        )
        and not has_active_assignment
    )

    can_dispose = (
        _can_manage_assets(user)
        and asset.status == Asset.Status.RETIRED
        and not has_active_assignment
    )

    return render(
        request,
        "assets/asset_detail.html",
        {
            "asset": asset,
            "assignment_history": assignment_history,
            "has_active_assignment": has_active_assignment,
            "can_manage": _can_manage_assets(user),
            "can_delete": user.role == User.Role.SUPER_ADMIN,
            "can_retire": can_retire,
            "can_dispose": can_dispose,
        },
    )


@login_required
def employee_asset_detail(request, asset_id):
    """
    Display an assigned asset to the authenticated employee.

    Employees can only access an asset when that asset has an
    active assignment belonging to their own EmployeeProfile.

    This view intentionally does not expose the complete assignment
    history because that could reveal information about other
    employees.
    """
    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if user.role != User.Role.EMPLOYEE:
        raise PermissionDenied(
            "Only employees can access this page."
        )

    employee = getattr(
        user,
        "employee_profile",
        None,
    )

    if employee is None:
        raise PermissionDenied(
            "Your employee profile is not available."
        )

    assignment = get_object_or_404(
        employee.asset_assignments
        .select_related(
            "asset",
            "asset__department",
            "employee",
            "employee__user",
        )
        .filter(
            is_active=True,
            asset_id=asset_id,
        ),
        asset_id=asset_id,
    )

    return render(
        request,
        "assets/employee_asset_detail.html",
        {
            "asset": assignment.asset,
            "assignment": assignment,
            "employee": employee,
        },
    )


@login_required
def employee_asset_incident_create(request):
    """
    Allow an employee to report a damaged or lost asset.

    Security:
    - Only active EMPLOYEE users can access this view.
    - The employee must have an EmployeeProfile.
    - The form only exposes assets actively assigned to this employee.
    - The incident is always created as PENDING.
    - Processing fields remain server-controlled.
    """

    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if user.role != User.Role.EMPLOYEE:
        raise PermissionDenied(
            "Only employees can report damaged or lost assets."
        )

    employee = getattr(
        user,
        "employee_profile",
        None,
    )

    if employee is None:
        raise PermissionDenied(
            "Your employee profile is not available."
        )

    if request.method == "POST":
        form = AssetIncidentForm(
            request.POST,
            employee=employee,
        )

        if form.is_valid():
            incident = form.save(commit=False)

            incident.employee = employee
            incident.status = AssetIncident.Status.PENDING
            incident.processed_at = None
            incident.processed_by = None
            incident.admin_notes = ""

            incident.save()

            recipients = User.objects.filter(
                role__in=(
                    User.Role.SUPER_ADMIN,
                    User.Role.IT_ADMIN,
                ),
                is_active=True,
            )

            incident_type = incident.get_incident_type_display()
            asset_name = incident.asset.asset_name
            asset_id = incident.asset.asset_id

            employee_name = (
                user.get_full_name()
                or user.username
            )

            for recipient in recipients:
                Notification.objects.create(
                    recipient=recipient,
                    notification_type=(
                        Notification.NotificationType.SYSTEM
                    ),
                    severity=Notification.Severity.WARNING,
                    title=(
                        f"New {incident_type} Asset Report"
                    ),
                    message=(
                        f"{employee_name} reported "
                        f"{incident_type.lower()} for "
                        f"{asset_name} ({asset_id}). "
                        f"Incident #{incident.id} is "
                        "awaiting review."
                    ),
                    url="",
                    reference_type="AssetIncident",
                    reference_id=str(incident.id),
                )

            messages.success(
                request,
                (
                    f"Your {incident_type.lower()} asset report "
                    "has been submitted successfully and is "
                    "waiting for administrator review."
                ),
            )

            return redirect(
                "employee_asset_incident_list"
            )

    else:
        form = AssetIncidentForm(
            employee=employee,
        )

    return render(
        request,
        "assets/employee_asset_incident_create.html",
        {
            "form": form,
            "employee": employee,
        },
    )


@login_required
def employee_asset_incident_list(request):
    """
    Display asset incidents submitted by the authenticated employee.

    Security:
    - Only active EMPLOYEE users can access this page.
    - Only the authenticated employee's own incidents are returned.
    - No other employee's incident data is exposed.
    """

    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if user.role != User.Role.EMPLOYEE:
        raise PermissionDenied(
            "Only employees can access asset incident reports."
        )

    employee = getattr(
        user,
        "employee_profile",
        None,
    )

    if employee is None:
        raise PermissionDenied(
            "Your employee profile is not available."
        )

    incidents = (
        AssetIncident.objects
        .select_related(
            "asset",
            "asset__department",
        )
        .filter(
            employee=employee,
        )
        .order_by(
            "-reported_at",
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
    ).strip()

    incident_type = request.GET.get(
        "type",
        "",
    ).strip()

    if search_query:
        incidents = incidents.filter(
            Q(asset__asset_id__icontains=search_query)
            | Q(asset__asset_name__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    if status:
        incidents = incidents.filter(
            status=status,
        )

    if incident_type:
        incidents = incidents.filter(
            incident_type=incident_type,
        )

    return render(
        request,
        "assets/employee_asset_incident_list.html",
        {
            "incidents": incidents,
            "employee": employee,
            "search_query": search_query,
            "selected_status": status,
            "selected_type": incident_type,
            "statuses": AssetIncident.Status.choices,
            "incident_types": AssetIncident.IncidentType.choices,
        },
    )


@login_required
def admin_asset_incident_list(request):
    """
    Display asset incident reports for Super Admin and IT Admin.

    Security:
    - Only active Super Admin and IT Admin users can access.
    - All incidents are loaded with the related asset and employee.
    - Search and filters are applied server-side.
    """

    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if not _can_manage_assets(user):
        raise PermissionDenied(
            "Only Super Admin and IT Admin can review asset incidents."
        )

    incidents = (
        AssetIncident.objects
        .select_related(
            "asset",
            "asset__department",
            "employee",
            "employee__user",
            "processed_by",
        )
        .order_by(
            "-reported_at",
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
    ).strip()

    incident_type = request.GET.get(
        "type",
        "",
    ).strip()

    if search_query:
        incidents = incidents.filter(
            Q(asset__asset_id__icontains=search_query)
            | Q(asset__asset_name__icontains=search_query)
            | Q(employee__employee_id__icontains=search_query)
            | Q(employee__user__username__icontains=search_query)
            | Q(employee__user__first_name__icontains=search_query)
            | Q(employee__user__last_name__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    if status:
        incidents = incidents.filter(
            status=status,
        )

    if incident_type:
        incidents = incidents.filter(
            incident_type=incident_type,
        )

    return render(
        request,
        "assets/admin_asset_incident_list.html",
        {
            "incidents": incidents,
            "search_query": search_query,
            "selected_status": status,
            "selected_type": incident_type,
            "statuses": AssetIncident.Status.choices,
            "incident_types": AssetIncident.IncidentType.choices,
        },
    )


@login_required
def admin_asset_incident_process(request, incident_id):
    """
    Approve or reject an employee asset incident.

    Security:
    - Only active Super Admin and IT Admin users can process.
    - Processing is POST-only.
    - Only Pending incidents can be processed.
    - The authenticated admin is always stored as processed_by.
    - The browser cannot control processed_by or processed_at.
    - Approving changes the asset status according to incident type.
    - Rejecting does not change the asset status.
    """

    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if not _can_manage_assets(user):
        raise PermissionDenied(
            "Only Super Admin and IT Admin can process asset incidents."
        )

    if request.method != "POST":
        raise PermissionDenied(
            "Asset incident processing must be submitted using POST."
        )

    incident = get_object_or_404(
        AssetIncident.objects.select_related(
            "asset",
            "employee",
            "employee__user",
        ),
        pk=incident_id,
    )

    if incident.status != AssetIncident.Status.PENDING:
        messages.error(
            request,
            (
                f"Incident #{incident.id} has already been "
                "processed and cannot be changed."
            ),
        )
        return redirect(
            "admin_asset_incident_list"
        )

    decision = request.POST.get(
        "decision",
        "",
    ).strip().upper()

    if decision not in (
        AssetIncident.Status.APPROVED,
        AssetIncident.Status.REJECTED,
    ):
        messages.error(
            request,
            "Invalid incident processing action.",
        )
        return redirect(
            "admin_asset_incident_list"
        )

    admin_notes = request.POST.get(
        "admin_notes",
        "",
    ).strip()

    if len(admin_notes) > 5000:
        messages.error(
            request,
            "Admin notes cannot exceed 5000 characters.",
        )
        return redirect(
            "admin_asset_incident_list"
        )

    asset = incident.asset

    if decision == AssetIncident.Status.APPROVED:

        if incident.incident_type == AssetIncident.IncidentType.DAMAGED:
            new_asset_status = Asset.Status.DAMAGED
        else:
            new_asset_status = Asset.Status.LOST

        old_asset_status = asset.status

        incident.status = AssetIncident.Status.APPROVED
        incident.processed_by = user
        incident.processed_at = None
        incident.admin_notes = admin_notes

        incident.save()

        create_audit_log(
            user=user,
            action=AuditLog.Action.UPDATE,
            module="Asset Management",
            description=(
                f"Asset incident #{incident.id} was approved. "
                f"Asset '{asset.asset_id}' - "
                f"'{asset.asset_name}' status changed from "
                f"'{old_asset_status}' to '{new_asset_status}'."
            ),
            object_type="AssetIncident",
            object_id=incident.id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        employee_user = incident.employee.user

        if employee_user.is_active:
            Notification.objects.create(
                recipient=employee_user,
                notification_type=(
                    Notification.NotificationType.SYSTEM
                ),
                severity=Notification.Severity.WARNING,
                title="Asset Incident Approved",
                message=(
                    f"Your {incident.get_incident_type_display().lower()} "
                    f"report for {asset.asset_name} "
                    f"({asset.asset_id}) has been approved."
                ),
                url="",
                reference_type="AssetIncident",
                reference_id=str(incident.id),
            )

        messages.success(
            request,
            (
                f"Incident #{incident.id} was approved successfully. "
                f"Asset {asset.asset_id} is now marked as "
                f"{asset.get_status_display()}."
            ),
        )

    else:
        incident.status = AssetIncident.Status.REJECTED
        incident.processed_by = user
        incident.processed_at = None
        incident.admin_notes = admin_notes

        incident.save()

        create_audit_log(
            user=user,
            action=AuditLog.Action.UPDATE,
            module="Asset Management",
            description=(
                f"Asset incident #{incident.id} was rejected. "
                f"Asset '{asset.asset_id}' - "
                f"'{asset.asset_name}' status was not changed."
            ),
            object_type="AssetIncident",
            object_id=incident.id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        employee_user = incident.employee.user

        if employee_user.is_active:
            Notification.objects.create(
                recipient=employee_user,
                notification_type=(
                    Notification.NotificationType.SYSTEM
                ),
                severity=Notification.Severity.WARNING,
                title="Asset Incident Rejected",
                message=(
                    f"Your {incident.get_incident_type_display().lower()} "
                    f"report for {asset.asset_name} "
                    f"({asset.asset_id}) has been rejected."
                ),
                url="",
                reference_type="AssetIncident",
                reference_id=str(incident.id),
            )

        messages.success(
            request,
            f"Incident #{incident.id} was rejected successfully.",
        )

    return redirect(
        "admin_asset_incident_list"
    )


@login_required
def asset_create(request):
    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if not _can_manage_assets(user):
        raise PermissionDenied(
            "Only Super Admin and IT Admin can create assets."
        )

    if request.method == "POST":
        form = AssetForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            asset = form.save()

            create_audit_log(
                user=user,
                action=AuditLog.Action.CREATE,
                module="Asset Management",
                description=(
                    f"Asset '{asset.asset_id}' - "
                    f"'{asset.asset_name}' was created "
                    "from the frontend."
                ),
                object_type="Asset",
                object_id=asset.id,
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            messages.success(
                request,
                f"Asset {asset.asset_id} was created successfully.",
            )

            return redirect(
                "asset_detail",
                asset_id=asset.id,
            )
    else:
        form = AssetForm()

    return render(
        request,
        "assets/asset_form.html",
        {
            "form": form,
            "page_title": "Add Asset",
            "submit_text": "Create Asset",
        },
    )


@login_required
def asset_update(request, asset_id):
    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if not _can_manage_assets(user):
        raise PermissionDenied(
            "Only Super Admin and IT Admin can update assets."
        )

    asset = get_object_or_404(
        Asset.objects.select_related("department"),
        pk=asset_id,
    )

    old_status = asset.status

    if request.method == "POST":
        form = AssetForm(
            request.POST,
            request.FILES,
            instance=asset,
        )

        if form.is_valid():
            new_status = form.cleaned_data.get("status")

            lifecycle_statuses = (
                Asset.Status.RETIRED,
                Asset.Status.DISPOSED,
            )

            if (
                old_status != new_status
                and new_status in lifecycle_statuses
            ):
                form.add_error(
                    "status",
                    (
                        "Retired and Disposed status must be handled "
                        "through the dedicated asset lifecycle actions."
                    ),
                )
            else:
                asset = form.save()

                if old_status != asset.status:
                    description = (
                        f"Asset '{asset.asset_id}' status changed "
                        f"from '{old_status}' to "
                        f"'{asset.status}' from the frontend."
                    )
                else:
                    description = (
                        f"Asset '{asset.asset_id}' - "
                        f"'{asset.asset_name}' was updated "
                        "from the frontend."
                    )

                create_audit_log(
                    user=user,
                    action=AuditLog.Action.UPDATE,
                    module="Asset Management",
                    description=description,
                    object_type="Asset",
                    object_id=asset.id,
                    ip_address=request.META.get("REMOTE_ADDR"),
                )

                messages.success(
                    request,
                    f"Asset {asset.asset_id} was updated successfully.",
                )

                return redirect(
                    "asset_detail",
                    asset_id=asset.id,
                )
    else:
        form = AssetForm(instance=asset)

    return render(
        request,
        "assets/asset_form.html",
        {
            "form": form,
            "asset": asset,
            "page_title": "Edit Asset",
            "submit_text": "Save Changes",
        },
    )


@login_required
def asset_retire(request, asset_id):
    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if not _can_manage_assets(user):
        raise PermissionDenied(
            "Only Super Admin and IT Admin can retire assets."
        )

    if request.method != "POST":
        raise PermissionDenied(
            "Asset retirement must be submitted using POST."
        )

    asset = get_object_or_404(
        Asset.objects.select_related("department"),
        pk=asset_id,
    )

    if asset.status == Asset.Status.DISPOSED:
        messages.error(
            request,
            f"Asset {asset.asset_id} has already been disposed.",
        )
        return redirect(
            "asset_detail",
            asset_id=asset.id,
        )

    if asset.status == Asset.Status.RETIRED:
        messages.info(
            request,
            f"Asset {asset.asset_id} is already retired.",
        )
        return redirect(
            "asset_detail",
            asset_id=asset.id,
        )

    if _has_active_assignment(asset):
        messages.error(
            request,
            (
                f"Asset {asset.asset_id} cannot be retired while it "
                "is actively assigned to an employee. Return the "
                "asset first."
            ),
        )
        return redirect(
            "asset_detail",
            asset_id=asset.id,
        )

    old_status = asset.status

    asset.status = Asset.Status.RETIRED
    asset.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    create_audit_log(
        user=user,
        action=AuditLog.Action.UPDATE,
        module="Asset Management",
        description=(
            f"Asset '{asset.asset_id}' - "
            f"'{asset.asset_name}' was retired from the frontend. "
            f"Previous status was '{old_status}'."
        ),
        object_type="Asset",
        object_id=asset.id,
        ip_address=request.META.get("REMOTE_ADDR"),
    )

    messages.success(
        request,
        f"Asset {asset.asset_id} was retired successfully.",
    )

    return redirect(
        "asset_detail",
        asset_id=asset.id,
    )


@login_required
def asset_dispose(request, asset_id):
    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if not _can_manage_assets(user):
        raise PermissionDenied(
            "Only Super Admin and IT Admin can dispose assets."
        )

    if request.method != "POST":
        raise PermissionDenied(
            "Asset disposal must be submitted using POST."
        )

    asset = get_object_or_404(
        Asset.objects.select_related("department"),
        pk=asset_id,
    )

    if asset.status == Asset.Status.DISPOSED:
        messages.info(
            request,
            f"Asset {asset.asset_id} is already disposed.",
        )
        return redirect(
            "asset_detail",
            asset_id=asset.id,
        )

    if asset.status != Asset.Status.RETIRED:
        messages.error(
            request,
            (
                f"Asset {asset.asset_id} must be retired before "
                "it can be disposed."
            ),
        )
        return redirect(
            "asset_detail",
            asset_id=asset.id,
        )

    if _has_active_assignment(asset):
        messages.error(
            request,
            (
                f"Asset {asset.asset_id} cannot be disposed while "
                "it is actively assigned to an employee."
            ),
        )
        return redirect(
            "asset_detail",
            asset_id=asset.id,
        )

    asset.status = Asset.Status.DISPOSED
    asset.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    create_audit_log(
        user=user,
        action=AuditLog.Action.UPDATE,
        module="Asset Management",
        description=(
            f"Asset '{asset.asset_id}' - "
            f"'{asset.asset_name}' was disposed from the frontend."
        ),
        object_type="Asset",
        object_id=asset.id,
        ip_address=request.META.get("REMOTE_ADDR"),
    )

    messages.success(
        request,
        f"Asset {asset.asset_id} was disposed successfully.",
    )

    return redirect(
        "asset_detail",
        asset_id=asset.id,
    )


@login_required
def asset_delete(request, asset_id):
    user = request.user

    if not user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if user.role != User.Role.SUPER_ADMIN:
        raise PermissionDenied(
            "Only Super Admin can delete assets."
        )

    asset = get_object_or_404(
        Asset.objects.select_related("department"),
        pk=asset_id,
    )

    if request.method == "POST":
        asset_id_value = asset.asset_id
        asset_name = asset.asset_name
        asset_pk = asset.id

        if asset.assignments.exists():
            messages.error(
                request,
                (
                    f"Asset {asset_id_value} cannot be deleted because "
                    "assignment history exists for this asset."
                ),
            )

            return redirect(
                "asset_detail",
                asset_id=asset_pk,
            )

        asset.delete()

        create_audit_log(
            user=user,
            action=AuditLog.Action.DELETE,
            module="Asset Management",
            description=(
                f"Asset '{asset_id_value}' - "
                f"'{asset_name}' was deleted from the frontend."
            ),
            object_type="Asset",
            object_id=asset_pk,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        messages.success(
            request,
            f"Asset {asset_id_value} was deleted successfully.",
        )

        return redirect("asset_list")

    return render(
        request,
        "assets/asset_confirm_delete.html",
        {
            "asset": asset,
        },
    )