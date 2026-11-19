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

        if self.pk:
            active_assignment_count = (
                SoftwareLicenseAssignment.objects
                .filter(
                    license_id=self.pk,
                    is_active=True,
                )
                .count()
            )

            if active_assignment_count > self.total_licenses:
                errors["total_licenses"] = (
                    "Total licenses cannot be lower than the "
                    "number of currently active assignments."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def available_licenses(self):
        return max(
            self.total_licenses - self.assigned_licenses,
            0,
        )

    @property
    def is_expired(self):
        return (
            self.expiry_date is not None
            and self.expiry_date < timezone.now().date()
        )

    def save(self, *args, **kwargs):
        today = timezone.now().date()

        with transaction.atomic():

            if self.pk:
                SoftwareLicense.objects.select_for_update().get(
                    pk=self.pk
                )

                active_assignment_count = (
                    SoftwareLicenseAssignment.objects
                    .filter(
                        license_id=self.pk,
                        is_active=True,
                    )
                    .count()
                )

                self.assigned_licenses = active_assignment_count

            else:
                self.assigned_licenses = 0

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
        errors = {}

        if not self.license_id:
            errors["license"] = (
                "A software license is required."
            )

        if not self.employee_id:
            errors["employee"] = (
                "An employee is required."
            )

        if self.license_id and self.is_active:

            license_obj = self.license

            if license_obj.status in (
                SoftwareLicense.Status.INACTIVE,
                SoftwareLicense.Status.EXPIRED,
            ):
                errors["license"] = (
                    "Inactive or expired software licenses "
                    "cannot be assigned."
                )

            if self.employee_id:
                employee_obj = self.employee

                if (
                    employee_obj.employment_status
                    != employee_obj.EmploymentStatus.ACTIVE
                ):
                    errors["employee"] = (
                        "Software licenses can only be assigned "
                        "to active employees."
                    )

                existing_assignment = (
                    SoftwareLicenseAssignment.objects
                    .filter(
                        license_id=self.license_id,
                        employee_id=self.employee_id,
                        is_active=True,
                    )
                    .exclude(pk=self.pk)
                    .first()
                )

                if existing_assignment:
                    errors["employee"] = (
                        "This software license is already assigned "
                        "to this employee."
                    )

            active_count = (
                SoftwareLicenseAssignment.objects
                .filter(
                    license_id=self.license_id,
                    is_active=True,
                )
                .exclude(pk=self.pk)
                .count()
            )

            if active_count >= license_obj.total_licenses:
                errors["license"] = (
                    "All available licenses have already "
                    "been assigned."
                )

        if (
            self.returned_date
            and self.returned_date < self.assigned_date
        ):
            errors["returned_date"] = (
                "Returned date cannot be earlier than "
                "assigned date."
            )

        if not self.is_active and not self.returned_date:
            errors["returned_date"] = (
                "Returned date is required when an "
                "assignment is inactive."
            )

        if self.is_active and self.returned_date:
            errors["returned_date"] = (
                "An active assignment cannot have a "
                "returned date."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):

        if not self.is_active and not self.returned_date:
            self.returned_date = timezone.now().date()

        with transaction.atomic():

            old_license_id = None

            if self.pk:
                old_assignment = (
                    SoftwareLicenseAssignment.objects
                    .select_for_update()
                    .get(pk=self.pk)
                )

                old_license_id = old_assignment.license_id

            license_ids = {
                self.license_id,
            }

            if old_license_id:
                license_ids.add(old_license_id)

            license_ids = sorted(
                license_id
                for license_id in license_ids
                if license_id
            )

            locked_licenses = {}

            for license_id in license_ids:
                locked_licenses[license_id] = (
                    SoftwareLicense.objects
                    .select_for_update()
                    .get(pk=license_id)
                )

            if self.license_id:
                self.license = locked_licenses[self.license_id]

            self.full_clean()

            super().save(*args, **kwargs)

            for license_id in license_ids:
                active_count = (
                    SoftwareLicenseAssignment.objects
                    .filter(
                        license_id=license_id,
                        is_active=True,
                    )
                    .count()
                )

                SoftwareLicense.objects.filter(
                    pk=license_id
                ).update(
                    assigned_licenses=active_count
                )

    def delete(self, *args, **kwargs):

        license_id = self.license_id

        with transaction.atomic():

            SoftwareLicense.objects.select_for_update().get(
                pk=license_id
            )

            result = super().delete(*args, **kwargs)

            active_count = (
                SoftwareLicenseAssignment.objects
                .filter(
                    license_id=license_id,
                    is_active=True,
                )
                .count()
            )

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