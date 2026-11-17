from django.contrib import admin

from accounts.models import User
from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log

from .models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "code",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "code",
    )

    ordering = (
        "name",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if request.user.role == User.Role.SUPER_ADMIN:
            return queryset

        return queryset.none()

    def has_view_permission(self, request, obj=None):
        return request.user.role == User.Role.SUPER_ADMIN

    def has_add_permission(self, request):
        return request.user.role == User.Role.SUPER_ADMIN

    def has_change_permission(self, request, obj=None):
        return request.user.role == User.Role.SUPER_ADMIN

    def has_delete_permission(self, request, obj=None):
        return request.user.role == User.Role.SUPER_ADMIN

    def save_model(self, request, obj, form, change):
        old_name = None
        old_code = None
        old_is_active = None

        if change:
            try:
                old_department = Department.objects.get(pk=obj.pk)
                old_name = old_department.name
                old_code = old_department.code
                old_is_active = old_department.is_active
            except Department.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)

        if not change:
            action = AuditLog.Action.CREATE
            description = (
                f"Department '{obj.name}' ({obj.code}) was created."
            )
        elif old_is_active is not None and old_is_active != obj.is_active:
            action = AuditLog.Action.UPDATE
            status = "activated" if obj.is_active else "deactivated"
            description = (
                f"Department '{obj.name}' ({obj.code}) was {status}."
            )
        elif old_name != obj.name or old_code != obj.code:
            action = AuditLog.Action.UPDATE
            description = (
                f"Department '{obj.name}' ({obj.code}) was updated."
            )
        else:
            action = AuditLog.Action.UPDATE
            description = (
                f"Department '{obj.name}' ({obj.code}) was updated."
            )

        create_audit_log(
            user=request.user,
            action=action,
            module="Department Management",
            description=description,
            object_type="Department",
            object_id=obj.id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

    def delete_model(self, request, obj):
        department_name = obj.name
        department_code = obj.code
        department_id = obj.id

        super().delete_model(request, obj)

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.DELETE,
            module="Department Management",
            description=(
                f"Department '{department_name}' "
                f"({department_code}) was deleted."
            ),
            object_type="Department",
            object_id=department_id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )