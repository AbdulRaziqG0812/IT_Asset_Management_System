from django.db import models
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