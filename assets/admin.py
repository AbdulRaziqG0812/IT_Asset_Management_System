from django.contrib import admin

from accounts.models import User
from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log

from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):

    list_display = (
        "asset_id",
        "asset_name",
        "category",
        "brand_model",
        "serial_number",
        "department",
        "condition",
        "status",
    )

    list_filter = (
        "category",
        "department",
        "condition",
        "status",
    )

    search_fields = (
        "asset_id",
        "asset_name",
        "serial_number",
        "brand_model",
        "vendor_name",
    )

    ordering = (
        "-id",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if request.user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        ):
            return queryset

        return queryset.none()

    def has_view_permission(self, request, obj=None):
        return request.user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        )

    def has_add_permission(self, request):
        return request.user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        )

    def has_change_permission(self, request, obj=None):
        return request.user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        )

    def has_delete_permission(self, request, obj=None):
        return request.user.role == User.Role.SUPER_ADMIN

    def save_model(self, request, obj, form, change):
        old_status = None

        if change:
            try:
                old_asset = Asset.objects.get(pk=obj.pk)
                old_status = old_asset.status
            except Asset.DoesNotExist:
                old_status = None

        super().save_model(request, obj, form, change)

        if not change:
            action = AuditLog.Action.CREATE
            description = (
                f"Asset '{obj.asset_id}' - '{obj.asset_name}' "
                "was created."
            )
        elif old_status and old_status != obj.status:
            action = AuditLog.Action.UPDATE
            description = (
                f"Asset '{obj.asset_id}' status changed from "
                f"'{old_status}' to '{obj.status}'."
            )
        else:
            action = AuditLog.Action.UPDATE
            description = (
                f"Asset '{obj.asset_id}' - '{obj.asset_name}' "
                "was updated."
            )

        create_audit_log(
            user=request.user,
            action=action,
            module="Asset Management",
            description=description,
            object_type="Asset",
            object_id=obj.id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

    def delete_model(self, request, obj):
        asset_id = obj.asset_id
        asset_name = obj.asset_name
        asset_pk = obj.id

        super().delete_model(request, obj)

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.DELETE,
            module="Asset Management",
            description=(
                f"Asset '{asset_id}' - '{asset_name}' was deleted."
            ),
            object_type="Asset",
            object_id=asset_pk,
            ip_address=request.META.get("REMOTE_ADDR"),
        )