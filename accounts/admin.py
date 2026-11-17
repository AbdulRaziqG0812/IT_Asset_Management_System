from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log

from .models import EmployeeProfile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "department",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "role",
        "is_active",
        "is_staff",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    ordering = (
        "username",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "username",
                    "password",
                ),
            },
        ),
        (
            "Personal Information",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                ),
            },
        ),
        (
            "ITARMS Role",
            {
                "fields": (
                    "role",
                    "department",
                ),
            },
        ),
        (
            "Account Status",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Important Dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                ),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": (
                    "wide",
                ),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "role",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):

    list_display = (
        "employee_id",
        "user",
        "department",
        "phone",
        "job_title",
        "date_of_joining",
    )

    search_fields = (
        "employee_id",
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )

    list_filter = (
        "department",
        "job_title",
        "date_of_joining",
    )

    ordering = (
        "-id",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if request.user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.HR_MANAGER,
        ):
            return queryset

        return queryset.none()

    def has_view_permission(self, request, obj=None):
        return request.user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.HR_MANAGER,
        )

    def has_add_permission(self, request):
        return request.user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.HR_MANAGER,
        )

    def has_change_permission(self, request, obj=None):
        return request.user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.HR_MANAGER,
        )

    def has_delete_permission(self, request, obj=None):
        return request.user.role == User.Role.SUPER_ADMIN

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        employee_name = (
            obj.user.get_full_name()
            or obj.user.username
        )

        if not change:
            action = AuditLog.Action.CREATE
            description = (
                f"Employee '{obj.employee_id}' - "
                f"'{employee_name}' was created."
            )
        else:
            action = AuditLog.Action.UPDATE
            description = (
                f"Employee '{obj.employee_id}' - "
                f"'{employee_name}' was updated."
            )

        create_audit_log(
            user=request.user,
            action=action,
            module="Employee Management",
            description=description,
            object_type="EmployeeProfile",
            object_id=obj.id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

    def delete_model(self, request, obj):
        employee_id = obj.employee_id
        employee_name = (
            obj.user.get_full_name()
            or obj.user.username
        )
        employee_pk = obj.id

        super().delete_model(request, obj)

        create_audit_log(
            user=request.user,
            action=AuditLog.Action.DELETE,
            module="Employee Management",
            description=(
                f"Employee '{employee_id}' - "
                f"'{employee_name}' was deleted."
            ),
            object_type="EmployeeProfile",
            object_id=employee_pk,
            ip_address=request.META.get("REMOTE_ADDR"),
        )