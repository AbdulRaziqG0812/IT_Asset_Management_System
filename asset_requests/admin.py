from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone

from .models import AssetRequest
from accounts.models import User


@admin.register(AssetRequest)
class AssetRequestAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        # Asset requests must be created through
        # the employee workflow, not Django Admin.
        return False

    def has_delete_permission(self, request, obj=None):
        # Asset requests must never be deleted through Admin.
        return False

    def has_change_permission(self, request, obj=None):
        # Super Admin can access asset requests.
        if request.user.role == User.Role.SUPER_ADMIN:
            return True

        # Department Manager can only access requests
        # belonging to their own department.
        if request.user.role == User.Role.DEPARTMENT_MANAGER:

            if request.user.department_id is None:
                return False

            if obj is None:
                return True

            return (
                obj.department_id
                == request.user.department_id
            )

        # All other roles are denied.
        return False

    list_display = (
        "id",
        "employee",
        "department",
        "asset_category",
        "asset_name",
        "quantity",
        "priority",
        "status",
        "approved_by",
        "processed_at",
        "requested_at",
    )

    list_filter = (
        "status",
        "priority",
        "department",
        "asset_category",
    )

    search_fields = (
        "employee__employee_id",
        "employee__user__username",
        "employee__user__email",
        "asset_category",
        "asset_name",
        "reason",
    )

    ordering = ("-requested_at",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        # Super Admin can see all requests.
        if request.user.role == User.Role.SUPER_ADMIN:
            return queryset

        # Department Manager can only see requests
        # from their assigned department.
        if request.user.role == User.Role.DEPARTMENT_MANAGER:

            if request.user.department_id is None:
                return queryset.none()

            return queryset.filter(
                department_id=request.user.department_id
            )

        # All other roles get no records.
        return queryset.none()

    actions = (
        "approve_requests",
        "reject_requests",
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Department Managers cannot manually edit request data.

        Super Admin also cannot manually modify processed request
        status through the form. Status changes should happen
        through the controlled approval/rejection actions.
        """

        readonly_fields = ()

        # Department Manager:
        # entire request is read-only.
        if request.user.role == User.Role.DEPARTMENT_MANAGER:
            readonly_fields = (
                "employee",
                "department",
                "asset_category",
                "asset_name",
                "quantity",
                "reason",
                "priority",
                "status",
                "manager_notes",
                "approved_by",
                "processed_at",
                "requested_at",
                "updated_at",
            )

            return readonly_fields

        # Super Admin:
        # Once a request has been processed, protect all
        # workflow fields from manual modification.
        if (
            request.user.role == User.Role.SUPER_ADMIN
            and obj is not None
            and obj.status != AssetRequest.Status.PENDING
        ):
            readonly_fields = (
                "employee",
                "department",
                "asset_category",
                "asset_name",
                "quantity",
                "reason",
                "priority",
                "status",
                "manager_notes",
                "approved_by",
                "processed_at",
                "requested_at",
                "updated_at",
            )

        return readonly_fields

    def _get_authorized_requests(self, request, queryset):
        """
        Return only pending requests that the current user
        is authorized to process.
        """

        # Super Admin can process pending requests
        # from every department.
        if request.user.role == User.Role.SUPER_ADMIN:
            return queryset.filter(
                status=AssetRequest.Status.PENDING
            )

        # Department Manager can only process pending requests
        # from their own department.
        if request.user.role == User.Role.DEPARTMENT_MANAGER:

            if request.user.department_id is None:
                return queryset.none()

            return queryset.filter(
                status=AssetRequest.Status.PENDING,
                department_id=request.user.department_id,
            )

        # All other roles have no approval authority.
        return queryset.none()

    @admin.action(description="Approve selected asset requests")
    def approve_requests(self, request, queryset):

        # Explicit authorization check.
        if request.user.role not in (
            User.Role.SUPER_ADMIN,
            User.Role.DEPARTMENT_MANAGER,
        ):
            self.message_user(
                request,
                "You are not authorized to approve asset requests.",
                level=messages.ERROR,
            )
            return

        authorized_requests = self._get_authorized_requests(
            request,
            queryset,
        )

        updated_count = 0

        with transaction.atomic():

            for asset_request in (
                authorized_requests.select_for_update()
            ):

                # Re-check the status while the record is locked.
                if asset_request.status != AssetRequest.Status.PENDING:
                    continue

                asset_request.status = (
                    AssetRequest.Status.APPROVED
                )

                asset_request.approved_by = request.user
                asset_request.processed_at = timezone.now()

                asset_request.save()

                updated_count += 1

        unauthorized_count = (
            queryset.count() - updated_count
        )

        if updated_count:
            self.message_user(
                request,
                (
                    f"{updated_count} asset request(s) "
                    "approved successfully."
                ),
                level=messages.SUCCESS,
            )

        if unauthorized_count:
            self.message_user(
                request,
                (
                    f"{unauthorized_count} selected request(s) "
                    "were skipped because they are not pending "
                    "or are outside your department."
                ),
                level=messages.WARNING,
            )

    @admin.action(description="Reject selected asset requests")
    def reject_requests(self, request, queryset):

        # Explicit authorization check.
        if request.user.role not in (
            User.Role.SUPER_ADMIN,
            User.Role.DEPARTMENT_MANAGER,
        ):
            self.message_user(
                request,
                "You are not authorized to reject asset requests.",
                level=messages.ERROR,
            )
            return

        authorized_requests = self._get_authorized_requests(
            request,
            queryset,
        )

        updated_count = 0

        with transaction.atomic():

            for asset_request in (
                authorized_requests.select_for_update()
            ):

                # Re-check the status while the record is locked.
                if asset_request.status != AssetRequest.Status.PENDING:
                    continue

                asset_request.status = (
                    AssetRequest.Status.REJECTED
                )

                asset_request.approved_by = request.user
                asset_request.processed_at = timezone.now()

                asset_request.save()

                updated_count += 1

        unauthorized_count = (
            queryset.count() - updated_count
        )

        if updated_count:
            self.message_user(
                request,
                (
                    f"{updated_count} asset request(s) "
                    "rejected successfully."
                ),
                level=messages.SUCCESS,
            )

        if unauthorized_count:
            self.message_user(
                request,
                (
                    f"{unauthorized_count} selected request(s) "
                    "were skipped because they are not pending "
                    "or are outside your department."
                ),
                level=messages.WARNING,
            )