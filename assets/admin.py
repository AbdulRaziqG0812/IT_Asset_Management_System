from django.contrib import admin

from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):

    list_display = (
        "asset_id",
        "asset_name",
        "category",
        "brand_model",
        "serial_number",
        "department",
        "condition",
        "status",
    )

    list_filter = (
        "category",
        "department",
        "condition",
        "status",
    )

    search_fields = (
        "asset_id",
        "asset_name",
        "serial_number",
        "brand_model",
        "vendor_name",
    )

    ordering = (
        "-id",
    )

    