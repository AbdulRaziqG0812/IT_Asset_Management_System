from django.db import models
from accounts.models import EmployeeProfile
from departments.models import Department


class AssetRequest(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="asset_requests",
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="asset_requests",
    )

    asset_category = models.CharField(
        max_length=50,
    )

    asset_name = models.CharField(
        max_length=150,
        blank=True,
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    reason = models.TextField()

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

    manager_notes = models.TextField(
        blank=True,
    )

    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_asset_requests",
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    requested_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def clean(self):
        from django.core.exceptions import ValidationError

        # Quantity validation
        if self.quantity < 1:
            raise ValidationError(
                {
                    "quantity": "Quantity must be at least 1."
                }
            )

        # Employee department and request department
        # must always match.
        if self.employee_id and self.department_id:
            employee_department_id = (
                self.employee.department_id
            )

            if employee_department_id != self.department_id:
                raise ValidationError(
                    {
                        "department": (
                            "The request department must match "
                            "the employee's department."
                        )
                    }
                )

        # Processed requests must have an approver
        # and processing timestamp.
        if self.status in (
            self.Status.APPROVED,
            self.Status.REJECTED,
        ):
            if self.approved_by_id is None:
                raise ValidationError(
                    {
                        "approved_by": (
                            "Approved by is required when "
                            "a request is processed."
                        )
                    }
                )

            if self.processed_at is None:
                raise ValidationError(
                    {
                        "processed_at": (
                            "Processed time is required when "
                            "a request is processed."
                        )
                    }
                )

        # Protect status transitions.
        # A request can move only:
        # Pending -> Approved
        # Pending -> Rejected
        #
        # Once Approved or Rejected, it cannot be
        # changed to another status.
        if self.pk:
            old_status = (
                AssetRequest.objects
                .only("status")
                .get(pk=self.pk)
                .status
            )

            if old_status != self.status:
                allowed_statuses = {
                    self.Status.PENDING: {
                        self.Status.APPROVED,
                        self.Status.REJECTED,
                    },
                    self.Status.APPROVED: set(),
                    self.Status.REJECTED: set(),
                }

                if self.status not in allowed_statuses.get(
                    old_status,
                    set(),
                ):
                    raise ValidationError(
                        {
                            "status": (
                                "This asset request status "
                                "transition is not allowed."
                            )
                        }
                    )


def save(self, *args, **kwargs):
    self.full_clean()
    super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)        

    def __str__(self):
        return (
            f"Request #{self.id} - "
            f"{self.employee.employee_id} - "
            f"{self.asset_category}"
        )