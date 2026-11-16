from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class SoftwareLicense(models.Model):

    class LicenseType(models.TextChoices):
        SUBSCRIPTION = "SUBSCRIPTION", "Subscription"
        PERPETUAL = "PERPETUAL", "Perpetual"
        OEM = "OEM", "OEM"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        EXPIRING_SOON = "EXPIRING_SOON", "Expiring Soon"
        EXPIRED = "EXPIRED", "Expired"
        INACTIVE = "INACTIVE", "Inactive"

    software_name = models.CharField(
        max_length=150
    )

    version = models.CharField(
        max_length=100,
        blank=True
    )

    license_type = models.CharField(
        max_length=20,
        choices=LicenseType.choices
    )

    license_key = models.CharField(
        max_length=255,
        unique=True
    )

    total_licenses = models.PositiveIntegerField(
        default=1
    )

    assigned_licenses = models.PositiveIntegerField(
        default=0
    )

    purchase_date = models.DateField(
        null=True,
        blank=True
    )

    expiry_date = models.DateField(
        null=True,
        blank=True
    )

    vendor_name = models.CharField(
        max_length=150,
        blank=True
    )

    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def clean(self):
        errors = {}

        if self.total_licenses < 1:
            errors["total_licenses"] = (
                "Total licenses must be at least 1."
            )

        if self.assigned_licenses > self.total_licenses:
            errors["assigned_licenses"] = (
                "Assigned licenses cannot exceed total licenses."
            )

        if (
            self.purchase_date
            and self.expiry_date
            and self.expiry_date < self.purchase_date
        ):
            errors["expiry_date"] = (
                "Expiry date cannot be earlier than purchase date."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def available_licenses(self):
        return self.total_licenses - self.assigned_licenses

    @property
    def is_expired(self):
        return (
            self.expiry_date is not None
            and self.expiry_date < timezone.now().date()
        )

    def save(self, *args, **kwargs):
        today = timezone.now().date()

        if self.status != self.Status.INACTIVE:
            if self.expiry_date:
                if self.expiry_date < today:
                    self.status = self.Status.EXPIRED

                elif (self.expiry_date - today).days <= 30:
                    self.status = self.Status.EXPIRING_SOON

                else:
                    self.status = self.Status.ACTIVE

            else:
                self.status = self.Status.ACTIVE

        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.software_name} - {self.license_key}"
    

class SoftwareLicenseAssignment(models.Model):

    license = models.ForeignKey(
        SoftwareLicense,
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    employee = models.ForeignKey(
        "accounts.EmployeeProfile",
        on_delete=models.PROTECT,
        related_name="software_license_assignments",
    )

    assigned_date = models.DateField(
        default=timezone.now,
    )

    returned_date = models.DateField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def clean(self):
        if self.is_active:

            existing_assignment = (
                SoftwareLicenseAssignment.objects
                .filter(
                    license=self.license,
                    employee=self.employee,
                    is_active=True,
                )
                .exclude(pk=self.pk)
                .first()
            )

            if existing_assignment:
                raise ValidationError(
                    "This software license is already assigned "
                    "to this employee."
                )

            active_count = (
                SoftwareLicenseAssignment.objects
                .filter(
                    license=self.license,
                    is_active=True,
                )
                .exclude(pk=self.pk)
                .count()
            )

            if active_count >= self.license.total_licenses:
                raise ValidationError(
                    "All available licenses have already been assigned."
                )

        if self.returned_date and self.returned_date < self.assigned_date:
            raise ValidationError(
                {
                    "returned_date":
                    "Returned date cannot be earlier than assigned date."
                }
            )

        if not self.is_active and not self.returned_date:
            raise ValidationError(
                {
                    "returned_date":
                    "Returned date is required when an assignment is inactive."
                }
            )

    def save(self, *args, **kwargs):
        if not self.is_active and not self.returned_date:
            self.returned_date = timezone.now().date()

        self.full_clean()

        super().save(*args, **kwargs)

        active_count = self.license.assignments.filter(
            is_active=True
        ).count()

        SoftwareLicense.objects.filter(
            pk=self.license_id
        ).update(
            assigned_licenses=active_count
        )

    def delete(self, *args, **kwargs):
        license_id = self.license_id

        with transaction.atomic():
            result = super().delete(*args, **kwargs)

            active_count = SoftwareLicenseAssignment.objects.filter(
                license_id=license_id,
                is_active=True,
            ).count()

            SoftwareLicense.objects.filter(
                pk=license_id
            ).update(
                assigned_licenses=active_count
            )

        return result    

    def __str__(self):
        return (
            f"{self.license.software_name} → "
            f"{self.employee.employee_id}"
        )