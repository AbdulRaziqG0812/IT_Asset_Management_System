from django.contrib import admin

from accounts.models import User
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