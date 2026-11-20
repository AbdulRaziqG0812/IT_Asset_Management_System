from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from accounts.models import User
from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log

from .forms import AssetForm
from .models import Asset


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
            assignments__employee=user,
            assignments__is_active=True,
        ).distinct()

    return queryset.none()


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

    if not _can_view_assets(user):
        raise PermissionDenied(
            "You do not have permission to view assets."
        )

    asset = get_object_or_404(
        _get_asset_queryset_for_user(user),
        pk=asset_id,
    )

    return render(
        request,
        "assets/asset_detail.html",
        {
            "asset": asset,
            "can_manage": _can_manage_assets(user),
            "can_delete": user.role == User.Role.SUPER_ADMIN,
        },
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