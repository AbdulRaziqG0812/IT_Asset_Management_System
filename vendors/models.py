from django.core.exceptions import ValidationError
from django.db import models\



class Vendor(models.Model):

    name = models.CharField(
        max_length=150,
        unique=True,
    )

    contact_person = models.CharField(
        max_length=150,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def clean(self):
        if self.email:
            self.email = self.email.strip().lower()

        if self.name:
            self.name = self.name.strip()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Purchase(models.Model):

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="purchases",
    )

    purchase_date = models.DateField()

    invoice_number = models.CharField(
        max_length=100,
        unique=True,
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    purchase_document = models.FileField(
        upload_to="vendors/purchases/",
        blank=True,
        null=True,
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
        if self.invoice_number:
            self.invoice_number = self.invoice_number.strip()

        if self.total_amount is not None and self.total_amount < 0:
            raise ValidationError(
                {
                    "total_amount": (
                        "Purchase amount cannot be negative."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} - {self.vendor.name}"