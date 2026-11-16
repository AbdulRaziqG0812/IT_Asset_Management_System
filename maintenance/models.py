from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from assets.models import Asset
from accounts.models import EmployeeProfile


class MaintenanceRequest(models.Model):

    class RequestType(models.TextChoices):
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        REPAIR = "REPAIR", "Repair"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        REJECTED = "REJECTED", "Rejected"

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="maintenance_requests",
    )

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="maintenance_requests",
    )

    request_type = models.CharField(
        max_length=20,
        choices=RequestType.choices,
    )

    issue_description = models.TextField()

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    technician_notes = models.TextField(
        blank=True,
    )

    resolution_notes = models.TextField(
        blank=True,
    )

    requested_at = models.DateTimeField(
        auto_now_add=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def clean(self):
        if self._state.adding and self.asset_id and self.employee_id:
            active_assignment = self.asset.assignments.filter(
                employee=self.employee,
                is_active=True,
            ).exists()

            if not active_assignment:
                raise ValidationError(
                    "Maintenance request can only be created for an asset currently assigned to this employee."
                )

        if self.status == self.Status.IN_PROGRESS:
            if not self.started_at:
                raise ValidationError(
                    "Started time is required when maintenance is in progress."
                )

        if self.status == self.Status.COMPLETED:
            if not self.completed_at:
                raise ValidationError(
                    "Completed time is required when maintenance is completed."
                )

        if self.pk:
            old_status = (
                MaintenanceRequest.objects
                .only("status")
                .get(pk=self.pk)
                .status
            )

            allowed_statuses = {
                self.Status.PENDING: {
                    self.Status.IN_PROGRESS,
                    self.Status.REJECTED,
                },
                self.Status.IN_PROGRESS: {
                    self.Status.COMPLETED,
                    self.Status.REJECTED,
                },
                self.Status.COMPLETED: set(),
                self.Status.REJECTED: set(),
            }

            if (
                self.status != old_status
                and self.status not in allowed_statuses.get(
                    old_status,
                    set(),
                )
            ):
                raise ValidationError(
                    {
                        "status": (
                            f"Invalid maintenance request status transition: "
                            f"{old_status} → {self.status}."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        if (
            self.status == self.Status.IN_PROGRESS
            and not self.started_at
        ):
            self.started_at = timezone.now()

        if (
            self.status == self.Status.COMPLETED
            and not self.completed_at
        ):
            self.completed_at = timezone.now()

        self.full_clean()

        with transaction.atomic():

            super().save(*args, **kwargs)

            if self.status == self.Status.IN_PROGRESS:

                Asset.objects.filter(
                    pk=self.asset_id
                ).update(
                    status=Asset.Status.UNDER_MAINTENANCE
                )

            elif self.status in (
                self.Status.COMPLETED,
                self.Status.REJECTED,
            ):

                active_assignment = self.asset.assignments.filter(
                    is_active=True
                ).exists()

                if active_assignment:
                    Asset.objects.filter(
                        pk=self.asset_id
                    ).update(
                        status=Asset.Status.ASSIGNED
                    )
                else:
                    Asset.objects.filter(
                        pk=self.asset_id
                    ).update(
                        status=Asset.Status.AVAILABLE
                    )

    def __str__(self):
        return (
            f"Maintenance #{self.id} - "
            f"{self.asset.asset_id} - "
            f"{self.employee.employee_id}"
        )