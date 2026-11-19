from django.contrib import admin

from accounts.models import User
from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log

from .models import (
    SoftwareLicense,
    SoftwareLicenseAssignment,
)


ADMIN_ROLES = (
    User.Role.SUPER_ADMIN,
    User.Role.IT_ADMIN,
)


def is_software_license_admin(user):
    return (
        user.is_authenticated
        and user.role in ADMIN_ROLES
    )


def is_super_admin(user):
    return (
        user.is_authenticated
        and user.role == User.Role.SUPER_ADMIN
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

    list_select_related = ()

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

    @admin.display(description="Available Licenses")
    def available_license_count(self, obj):
        return obj.available_licenses

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if not is_software_license_admin(request.user):
            return queryset.none()

        return queryset

    def has_module_permission(self, request):
        return is_software_license_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_software_license_admin(request.user)

    def has_add_permission(self, request):
        return is_software_license_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_software_license_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_super_admin(request.user)

    def save_model(self, request, obj, form, change):
        action = (
            AuditLog.Action.UPDATE
            if change
            else AuditLog.Action.CREATE
        )

        action_description = (
            "updated"
            if change
            else "created"
        )

        super().save_model(
            request,
            obj,
            form,
            change,
        )

        create_audit_log(
            user=request.user,
            action=action,
            module="Software License",
            description=(
                f"Software license '{obj.software_name}' "
                f"(ID: {obj.id}) was "
                f"{action_description}."
            ),
            object_type="SoftwareLicense",
            object_id=obj.id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

    def delete_model(self, request, obj):
        license_name = obj.software_name
        license_id = obj.id
        license_key = obj.license_key

        super().delete_model(
            request,
            obj,
        )

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.DELETE,
            module="Software License",
            description=(
                f"Software license '{license_name}' "
                f"(ID: {license_id}, key: {license_key}) "
                "was deleted."
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

    list_select_related = (
        "license",
        "employee",
        "employee__user",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Assignment",
            {
                "fields": (
                    "license",
                    "employee",
                    "assigned_date",
                    "returned_date",
                    "is_active",
                )
            },
        ),
        (
            "Notes",
            {
                "fields": (
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

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if not is_software_license_admin(request.user):
            return queryset.none()

        return queryset

    def has_module_permission(self, request):
        return is_software_license_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_software_license_admin(request.user)

    def has_add_permission(self, request):
        return is_software_license_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_software_license_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_super_admin(request.user)

    def save_model(self, request, obj, form, change):
        previous_is_active = None

        if change and obj.pk:
            previous_assignment = (
                SoftwareLicenseAssignment.objects
                .filter(pk=obj.pk)
                .values("is_active")
                .first()
            )

            if previous_assignment:
                previous_is_active = (
                    previous_assignment["is_active"]
                )

        super().save_model(
            request,
            obj,
            form,
            change,
        )

        if not change:
            action = AuditLog.Action.ASSIGN

            description = (
                f"Software license "
                f"'{obj.license.software_name}' "
                f"(ID: {obj.license.id}) was assigned "
                f"to employee "
                f"'{obj.employee.employee_id}'."
            )

        elif (
            previous_is_active is True
            and obj.is_active is False
        ):
            action = AuditLog.Action.RETURN

            description = (
                f"Software license "
                f"'{obj.license.software_name}' "
                f"(ID: {obj.license.id}) was returned "
                f"from employee "
                f"'{obj.employee.employee_id}'."
            )

        else:
            action = AuditLog.Action.UPDATE

            description = (
                f"Software license assignment "
                f"#{obj.id} for employee "
                f"'{obj.employee.employee_id}' "
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
        license_id = obj.license.id
        employee_id = obj.employee.employee_id

        super().delete_model(
            request,
            obj,
        )

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.DELETE,
            module="Software License",
            description=(
                f"Software license assignment "
                f"#{assignment_id} for license "
                f"'{license_name}' (ID: {license_id}) "
                f"and employee '{employee_id}' "
                "was deleted."
            ),
            object_type="SoftwareLicenseAssignment",
            object_id=assignment_id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )