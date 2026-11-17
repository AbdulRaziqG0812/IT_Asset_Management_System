from django.contrib import admin

from accounts.models import User
from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log

from .models import Assignment


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "asset",
        "employee",
        "assigned_date",
        "return_date",
        "is_active",
    )

    list_filter = (
        "is_active",
        "assigned_date",
        "return_date",
    )

    search_fields = (
        "asset__asset_id",
        "asset__asset_name",
        "asset__serial_number",
        "employee__employee_id",
        "employee__user__username",
        "employee__user__email",
    )

    ordering = ("-id",)

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
        is_return = not obj.is_active

        super().save_model(request, obj, form, change)

        if change:
            action = (
                AuditLog.Action.RETURN
                if is_return
                else AuditLog.Action.UPDATE
            )

            if action == AuditLog.Action.RETURN:
                description = (
                    f"Asset '{obj.asset.asset_id}' was returned "
                    f"from employee '{obj.employee.employee_id}'."
                )
            else:
                description = (
                    f"Assignment for asset '{obj.asset.asset_id}' "
                    f"was updated."
                )
        else:
            action = AuditLog.Action.ASSIGN

            description = (
                f"Asset '{obj.asset.asset_id}' was assigned "
                f"to employee '{obj.employee.employee_id}'."
            )

        create_audit_log(
            user=request.user,
            action=action,
            module="Asset Assignment",
            description=description,
            object_type="Assignment",
            object_id=obj.id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

    def delete_model(self, request, obj):
        assignment_id = obj.id
        asset_id = obj.asset.asset_id
        employee_id = obj.employee.employee_id

        super().delete_model(request, obj)

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.DELETE,
            module="Asset Assignment",
            description=(
                f"Assignment #{assignment_id} for asset "
                f"'{asset_id}' and employee '{employee_id}' was deleted."
            ),
            object_type="Assignment",
            object_id=assignment_id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )