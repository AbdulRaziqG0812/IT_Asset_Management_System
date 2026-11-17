from django.contrib import admin

from accounts.models import User
from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log

from .models import (
    SoftwareLicense,
    SoftwareLicenseAssignment,
)


@admin.register(SoftwareLicense)
class SoftwareLicenseAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "software_name",
        "version",
        "license_type",
        "total_licenses",
        "assigned_licenses",
        "available_license_count",
        "purchase_date",
        "expiry_date",
        "status",
        "vendor_name",
    )

    list_filter = (
        "license_type",
        "status",
        "purchase_date",
        "expiry_date",
    )

    search_fields = (
        "software_name",
        "version",
        "license_key",
        "vendor_name",
    )

    ordering = ("-id",)

    readonly_fields = (
        "assigned_licenses",
        "available_license_count",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Software Information",
            {
                "fields": (
                    "software_name",
                    "version",
                    "license_type",
                    "license_key",
                )
            },
        ),
        (
            "License Allocation",
            {
                "fields": (
                    "total_licenses",
                    "assigned_licenses",
                    "available_license_count",
                )
            },
        ),
        (
            "Purchase & Expiry",
            {
                "fields": (
                    "purchase_date",
                    "expiry_date",
                    "vendor_name",
                    "purchase_price",
                )
            },
        ),
        (
            "Status & Notes",
            {
                "fields": (
                    "status",
                    "notes",
                )
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def available_license_count(self, obj):
        return obj.available_licenses

    available_license_count.short_description = "Available Licenses"

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
        is_update = change

        super().save_model(request, obj, form, change)

        create_audit_log(
            user=request.user,
            action=(
                AuditLog.Action.UPDATE
                if is_update
                else AuditLog.Action.CREATE
            ),
            module="Software License",
            description=(
                f"Software license '{obj.software_name}' "
                f"was {'updated' if is_update else 'created'}."
            ),
            object_type="SoftwareLicense",
            object_id=obj.id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

    def delete_model(self, request, obj):
        license_name = obj.software_name
        license_id = obj.id

        super().delete_model(request, obj)

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.DELETE,
            module="Software License",
            description=(
                f"Software license '{license_name}' was deleted."
            ),
            object_type="SoftwareLicense",
            object_id=license_id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )


@admin.register(SoftwareLicenseAssignment)
class SoftwareLicenseAssignmentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "license",
        "employee",
        "assigned_date",
        "returned_date",
        "is_active",
    )

    list_filter = (
        "is_active",
        "assigned_date",
        "returned_date",
    )

    search_fields = (
        "license__software_name",
        "license__license_key",
        "employee__employee_id",
        "employee__user__username",
        "employee__user__email",
    )

    ordering = ("-id",)

    readonly_fields = (
        "created_at",
        "updated_at",
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
        is_update = change

        super().save_model(request, obj, form, change)

        if not change:
            action = AuditLog.Action.ASSIGN
            description = (
                f"Software license '{obj.license.software_name}' "
                f"was assigned to employee "
                f"'{obj.employee.employee_id}'."
            )
        elif not obj.is_active:
            action = AuditLog.Action.RETURN
            description = (
                f"Software license '{obj.license.software_name}' "
                f"was returned from employee "
                f"'{obj.employee.employee_id}'."
            )
        else:
            action = AuditLog.Action.UPDATE
            description = (
                f"Software license assignment #{obj.id} "
                f"for employee '{obj.employee.employee_id}' "
                "was updated."
            )

        create_audit_log(
            user=request.user,
            action=action,
            module="Software License",
            description=description,
            object_type="SoftwareLicenseAssignment",
            object_id=obj.id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

    def delete_model(self, request, obj):
        assignment_id = obj.id
        license_name = obj.license.software_name
        employee_id = obj.employee.employee_id

        super().delete_model(request, obj)

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.DELETE,
            module="Software License",
            description=(
                f"Software license assignment #{assignment_id} "
                f"for license '{license_name}' and employee "
                f"'{employee_id}' was deleted."
            ),
            object_type="SoftwareLicenseAssignment",
            object_id=assignment_id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )