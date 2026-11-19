from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log

from .models import MaintenanceRequest


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "asset",
        "employee",
        "request_type",
        "priority",
        "status",
        "requested_at",
        "started_at",
        "completed_at",
    )

    list_filter = (
        "request_type",
        "priority",
        "status",
        "requested_at",
    )

    search_fields = (
        "asset__asset_id",
        "asset__asset_name",
        "asset__serial_number",
        "employee__employee_id",
        "employee__user__username",
        "employee__user__email",
        "issue_description",
        "technician_notes",
        "resolution_notes",
    )

    ordering = ("-requested_at", "-id")

    readonly_fields = (
        "employee",
        "asset",
        "request_type",
        "issue_description",
        "priority",
        "requested_at",
        "started_at",
        "completed_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Request Information",
            {
                "fields": (
                    "employee",
                    "asset",
                    "request_type",
                    "issue_description",
                    "priority",
                    "status",
                )
            },
        ),
        (
            "Maintenance Processing",
            {
                "fields": (
                    "technician_notes",
                    "resolution_notes",
                    "started_at",
                    "completed_at",
                )
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "requested_at",
                    "updated_at",
                )
            },
        ),
    )

    actions = (
        "start_maintenance",
        "complete_maintenance",
        "reject_maintenance",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if request.user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        ):
            return queryset

        return queryset.none()

    def _is_authorized(self, request):
        return request.user.role in (
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        )

    def _get_pending_requests(self, queryset):
        return queryset.filter(
            status=MaintenanceRequest.Status.PENDING
        )

    @admin.action(description="Start selected maintenance requests")
    def start_maintenance(self, request, queryset):

        if not self._is_authorized(request):
            self.message_user(
                request,
                "You are not authorized to start maintenance requests.",
                level=messages.ERROR,
            )
            return

        requests = self._get_pending_requests(queryset)

        updated_count = 0

        with transaction.atomic():

            for maintenance_request in requests.select_for_update():

                if maintenance_request.status != (
                    MaintenanceRequest.Status.PENDING
                ):
                    continue

                maintenance_request.status = (
                    MaintenanceRequest.Status.IN_PROGRESS
                )
                maintenance_request.started_at = timezone.now()

                maintenance_request.save()

                create_audit_log(
                    user=request.user,
                    action=AuditLog.Action.UPDATE,
                    module="Maintenance",
                    object_type="MaintenanceRequest",
                    object_id=maintenance_request.id,
                    description=(
                        f"Maintenance request #{maintenance_request.id} "
                        f"for asset '{maintenance_request.asset.asset_id}' "
                        "was started."
                    ),
                    ip_address=request.META.get("REMOTE_ADDR"),
                )

                updated_count += 1

        if updated_count:
            self.message_user(
                request,
                (
                    f"{updated_count} maintenance request(s) "
                    "started successfully."
                ),
                level=messages.SUCCESS,
            )

        skipped_count = queryset.count() - updated_count

        if skipped_count:
            self.message_user(
                request,
                (
                    f"{skipped_count} request(s) were skipped because "
                    "they are not pending."
                ),
                level=messages.WARNING,
            )

    @admin.action(description="Complete selected maintenance requests")
    def complete_maintenance(self, request, queryset):

        if not self._is_authorized(request):
            self.message_user(
                request,
                "You are not authorized to complete maintenance requests.",
                level=messages.ERROR,
            )
            return

        requests = queryset.filter(
            status=MaintenanceRequest.Status.IN_PROGRESS
        )

        updated_count = 0

        with transaction.atomic():

            for maintenance_request in requests.select_for_update():

                if maintenance_request.status != (
                    MaintenanceRequest.Status.IN_PROGRESS
                ):
                    continue

                maintenance_request.status = (
                    MaintenanceRequest.Status.COMPLETED
                )
                maintenance_request.completed_at = timezone.now()

                maintenance_request.save()

                create_audit_log(
                    user=request.user,
                    action=AuditLog.Action.UPDATE,
                    module="Maintenance",
                    object_type="MaintenanceRequest",
                    object_id=maintenance_request.id,
                    description=(
                        f"Maintenance request #{maintenance_request.id} "
                        f"for asset '{maintenance_request.asset.asset_id}' "
                        "was completed."
                    ),
                    ip_address=request.META.get("REMOTE_ADDR"),
                )

                updated_count += 1

        if updated_count:
            self.message_user(
                request,
                (
                    f"{updated_count} maintenance request(s) "
                    "completed successfully."
                ),
                level=messages.SUCCESS,
            )

        skipped_count = queryset.count() - updated_count

        if skipped_count:
            self.message_user(
                request,
                (
                    f"{skipped_count} request(s) were skipped because "
                    "they are not in progress."
                ),
                level=messages.WARNING,
            )

    @admin.action(description="Reject selected maintenance requests")
    def reject_maintenance(self, request, queryset):

        if not self._is_authorized(request):
            self.message_user(
                request,
                "You are not authorized to reject maintenance requests.",
                level=messages.ERROR,
            )
            return

        requests = self._get_pending_requests(queryset)

        updated_count = 0

        with transaction.atomic():

            for maintenance_request in requests.select_for_update():

                if maintenance_request.status != (
                    MaintenanceRequest.Status.PENDING
                ):
                    continue

                maintenance_request.status = (
                    MaintenanceRequest.Status.REJECTED
                )

                maintenance_request.save()

                create_audit_log(
                    user=request.user,
                    action=AuditLog.Action.REJECT,
                    module="Maintenance",
                    object_type="MaintenanceRequest",
                    object_id=maintenance_request.id,
                    description=(
                        f"Maintenance request #{maintenance_request.id} "
                        f"for asset '{maintenance_request.asset.asset_id}' "
                        "was rejected."
                    ),
                    ip_address=request.META.get("REMOTE_ADDR"),
                )

                updated_count += 1

        if updated_count:
            self.message_user(
                request,
                (
                    f"{updated_count} maintenance request(s) "
                    "rejected successfully."
                ),
                level=messages.SUCCESS,
            )

        skipped_count = queryset.count() - updated_count

        if skipped_count:
            self.message_user(
                request,
                (
                    f"{skipped_count} request(s) were skipped because "
                    "they are not pending."
                ),
                level=messages.WARNING,
            )