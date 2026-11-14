from django.contrib import admin
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