from django.contrib import admin

from accounts.models import User
from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log

from .models import Vendor, Purchase


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "contact_person",
        "email",
        "phone",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "contact_person",
        "email",
        "phone",
    )

    ordering = ("-id",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Vendor Information",
            {
                "fields": (
                    "name",
                    "contact_person",
                    "email",
                    "phone",
                    "address",
                )
            },
        ),
        (
            "Status & Notes",
            {
                "fields": (
                    "is_active",
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
            module="Vendor",
            description=(
                f"Vendor '{obj.name}' was "
                f"{'updated' if is_update else 'created'}."
            ),
            object_type="Vendor",
            object_id=obj.id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

    def delete_model(self, request, obj):
        vendor_name = obj.name
        vendor_id = obj.id

        super().delete_model(request, obj)

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.DELETE,
            module="Vendor",
            description=f"Vendor '{vendor_name}' was deleted.",
            object_type="Vendor",
            object_id=vendor_id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "vendor",
        "purchase_date",
        "invoice_number",
        "total_amount",
        "created_at",
    )

    list_filter = (
        "vendor",
        "purchase_date",
    )

    search_fields = (
        "invoice_number",
        "vendor__name",
    )

    ordering = ("-id",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Purchase Information",
            {
                "fields": (
                    "vendor",
                    "purchase_date",
                    "invoice_number",
                    "total_amount",
                    "purchase_document",
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
            module="Purchase",
            description=(
                f"Purchase '{obj.invoice_number}' was "
                f"{'updated' if is_update else 'created'}."
            ),
            object_type="Purchase",
            object_id=obj.id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

    def delete_model(self, request, obj):
        invoice_number = obj.invoice_number
        purchase_id = obj.id

        super().delete_model(request, obj)

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.DELETE,
            module="Purchase",
            description=(
                f"Purchase '{invoice_number}' was deleted."
            ),
            object_type="Purchase",
            object_id=purchase_id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )