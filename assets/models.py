from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from accounts.models import EmployeeProfile
from departments.models import Department


class Asset(models.Model):

    class Category(models.TextChoices):
        LAPTOP = "LAPTOP", "Laptop"
        DESKTOP = "DESKTOP", "Desktop Computer"
        MONITOR = "MONITOR", "Monitor"
        KEYBOARD_MOUSE = "KEYBOARD_MOUSE", "Keyboard and Mouse"
        PRINTER_SCANNER = "PRINTER_SCANNER", "Printer and Scanner"
        NETWORKING = "NETWORKING", "Networking Equipment"
        SERVER_STORAGE = "SERVER_STORAGE", "Server and Storage Devices"
        MOBILE_TABLET = "MOBILE_TABLET", "Mobile Phones and Tablets"
        UPS_POWER = "UPS_POWER", "UPS and Power Equipment"
        OTHER = "OTHER", "Other IT Accessories"

    class Condition(models.TextChoices):
        NEW = "NEW", "New"
        GOOD = "GOOD", "Good"
        FAIR = "FAIR", "Fair"
        DAMAGED = "DAMAGED", "Damaged"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ASSIGNED = "ASSIGNED", "Assigned"
        UNDER_MAINTENANCE = "UNDER_MAINTENANCE", "Under Maintenance"
        DAMAGED = "DAMAGED", "Damaged"
        LOST = "LOST", "Lost"
        RETIRED = "RETIRED", "Retired"
        DISPOSED = "DISPOSED", "Disposed"

    asset_id = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
    )

    asset_name = models.CharField(
        max_length=150,
    )

    category = models.CharField(
        max_length=30,
        choices=Category.choices,
    )

    brand_model = models.CharField(
        max_length=150,
    )

    serial_number = models.CharField(
        max_length=150,
        unique=True,
    )

    purchase_date = models.DateField(
        null=True,
        blank=True,
    )

    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    warranty_expiry_date = models.DateField(
        null=True,
        blank=True,
    )

    vendor_name = models.CharField(
        max_length=150,
        blank=True,
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets",
    )

    asset_location = models.CharField(
        max_length=255,
        blank=True,
    )

    condition = models.CharField(
        max_length=20,
        choices=Condition.choices,
        default=Condition.NEW,
    )

    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )

    description = models.TextField(
        blank=True,
    )

    invoice_document = models.FileField(
        upload_to="assets/invoices/",
        null=True,
        blank=True,
    )

    asset_image = models.ImageField(
        upload_to="assets/images/",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def save(self, *args, **kwargs):

        if not self.asset_id:
            last_asset = (
                Asset.objects
                .order_by("-id")
                .first()
            )

            if last_asset:
                next_number = last_asset.id + 1
            else:
                next_number = 1

            self.asset_id = f"AST-{next_number:04d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asset_id} - {self.asset_name}"


class AssetIncident(models.Model):

    class IncidentType(models.TextChoices):
        DAMAGED = "DAMAGED", "Damaged"
        LOST = "LOST", "Lost"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="incidents",
    )

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="asset_incidents",
    )

    incident_type = models.CharField(
        max_length=20,
        choices=IncidentType.choices,
    )

    description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    reported_at = models.DateTimeField(
        auto_now_add=True,
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    processed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="processed_asset_incidents",
    )

    admin_notes = models.TextField(
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ("-reported_at", "-id")
        indexes = [
            models.Index(
                fields=("employee", "status"),
            ),
            models.Index(
                fields=("asset", "status"),
            ),
            models.Index(
                fields=("incident_type", "status"),
            ),
        ]

    def clean(self):
        if self.asset_id and self.employee_id:

            active_assignment = self.asset.assignments.filter(
                employee=self.employee,
                is_active=True,
            ).exists()

            if self._state.adding and not active_assignment:
                raise ValidationError(
                    "An asset incident can only be reported for "
                    "an asset currently assigned to this employee."
                )

        if self._state.adding:
            if self.status != self.Status.PENDING:
                raise ValidationError(
                    "A new asset incident must start with Pending status."
                )

            if self.processed_at:
                raise ValidationError(
                    "A new asset incident cannot have a processed time."
                )

            if self.processed_by_id:
                raise ValidationError(
                    "A new asset incident cannot have a processor."
                )

        if self.status == self.Status.PENDING:
            if self.processed_at or self.processed_by_id:
                raise ValidationError(
                    "A pending asset incident cannot have processing details."
                )

        if self.status in (
            self.Status.APPROVED,
            self.Status.REJECTED,
        ):
            if not self.processed_at:
                raise ValidationError(
                    "Processed time is required for a processed incident."
                )

            if not self.processed_by_id:
                raise ValidationError(
                    "Processed by is required for a processed incident."
                )

        if self.pk:
            old_status = (
                AssetIncident.objects
                .only("status")
                .get(pk=self.pk)
                .status
            )

            allowed_statuses = {
                self.Status.PENDING: {
                    self.Status.APPROVED,
                    self.Status.REJECTED,
                },
                self.Status.APPROVED: set(),
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
                            "Invalid asset incident status transition: "
                            f"{old_status} → {self.status}."
                        )
                    }
                )

    def save(self, *args, **kwargs):

        if self.status in (
            self.Status.APPROVED,
            self.Status.REJECTED,
        ) and not self.processed_at:
            self.processed_at = timezone.now()

        self.full_clean()

        with transaction.atomic():

            super().save(*args, **kwargs)

            if self.status == self.Status.APPROVED:

                new_asset_status = (
                    Asset.Status.DAMAGED
                    if self.incident_type == self.IncidentType.DAMAGED
                    else Asset.Status.LOST
                )

                Asset.objects.filter(
                    pk=self.asset_id,
                ).update(
                    status=new_asset_status,
                )

    def __str__(self):
        return (
            f"Incident #{self.id} - "
            f"{self.asset.asset_id} - "
            f"{self.employee.employee_id} - "
            f"{self.get_incident_type_display()}"
        )