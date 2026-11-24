from django import forms
from django.core.exceptions import ValidationError

from accounts.models import EmployeeProfile
from .models import Asset, AssetIncident


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = (
            "asset_name",
            "category",
            "brand_model",
            "serial_number",
            "purchase_date",
            "purchase_price",
            "warranty_expiry_date",
            "vendor_name",
            "department",
            "asset_location",
            "condition",
            "status",
            "description",
            "invoice_document",
            "asset_image",
        )

        widgets = {
            "asset_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Dell Latitude 5420",
                    "autocomplete": "off",
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "brand_model": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Dell Latitude 5420",
                    "autocomplete": "off",
                }
            ),
            "serial_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter unique serial number",
                    "autocomplete": "off",
                }
            ),
            "purchase_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "purchase_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0",
                    "inputmode": "decimal",
                }
            ),
            "warranty_expiry_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "vendor_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Vendor / Supplier name",
                    "autocomplete": "organization",
                }
            ),
            "department": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "asset_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Islamabad Office",
                    "autocomplete": "off",
                }
            ),
            "condition": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Enter additional information about this asset...",
                }
            ),
            "invoice_document": forms.ClearableFileInput(
                attrs={
                    "class": "form-control file-input",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                }
            ),
            "asset_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control file-input",
                    "accept": ".jpg,.jpeg,.png,.webp",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["department"].required = False
        self.fields["purchase_date"].required = False
        self.fields["purchase_price"].required = False
        self.fields["warranty_expiry_date"].required = False
        self.fields["vendor_name"].required = False
        self.fields["asset_location"].required = False
        self.fields["description"].required = False
        self.fields["invoice_document"].required = False
        self.fields["asset_image"].required = False

        required_fields = (
            "asset_name",
            "category",
            "brand_model",
            "serial_number",
            "condition",
            "status",
        )

        for field_name in required_fields:
            self.fields[field_name].required = True
            self.fields[field_name].widget.attrs["required"] = "required"

        self.fields["asset_name"].widget.attrs["autocomplete"] = "off"
        self.fields["brand_model"].widget.attrs["autocomplete"] = "off"
        self.fields["serial_number"].widget.attrs["autocomplete"] = "off"

    def clean_asset_name(self):
        asset_name = self.cleaned_data.get("asset_name", "").strip()

        if not asset_name:
            raise ValidationError("Asset name is required.")

        return asset_name

    def clean_brand_model(self):
        brand_model = self.cleaned_data.get("brand_model", "").strip()

        if not brand_model:
            raise ValidationError("Brand / Model is required.")

        return brand_model

    def clean_serial_number(self):
        serial_number = self.cleaned_data.get("serial_number", "").strip()

        if not serial_number:
            raise ValidationError("Serial number is required.")

        queryset = Asset.objects.filter(
            serial_number__iexact=serial_number
        )

        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise ValidationError(
                "An asset with this serial number already exists."
            )

        return serial_number

    def clean_purchase_price(self):
        purchase_price = self.cleaned_data.get("purchase_price")

        if purchase_price is not None and purchase_price < 0:
            raise ValidationError(
                "Purchase price cannot be negative."
            )

        return purchase_price

    def clean(self):
        cleaned_data = super().clean()

        purchase_date = cleaned_data.get("purchase_date")
        warranty_expiry_date = cleaned_data.get(
            "warranty_expiry_date"
        )

        if (
            purchase_date
            and warranty_expiry_date
            and warranty_expiry_date < purchase_date
        ):
            self.add_error(
                "warranty_expiry_date",
                "Warranty expiry date cannot be before purchase date.",
            )

        return cleaned_data

    def clean_invoice_document(self):
        document = self.cleaned_data.get("invoice_document")

        if not document:
            return document

        max_size = 10 * 1024 * 1024

        if document.size > max_size:
            raise ValidationError(
                "Invoice document must not exceed 10 MB."
            )

        allowed_extensions = (
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
        )

        if not document.name.lower().endswith(allowed_extensions):
            raise ValidationError(
                "Invoice must be a PDF, JPG, JPEG, or PNG file."
            )

        return document

    def clean_asset_image(self):
        image = self.cleaned_data.get("asset_image")

        if not image:
            return image

        max_size = 5 * 1024 * 1024

        if image.size > max_size:
            raise ValidationError(
                "Asset image must not exceed 5 MB."
            )

        allowed_extensions = (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        )

        if not image.name.lower().endswith(allowed_extensions):
            raise ValidationError(
                "Asset image must be JPG, JPEG, PNG, or WEBP."
            )

        return image


class AssetIncidentForm(forms.ModelForm):

    class Meta:
        model = AssetIncident
        fields = (
            "asset",
            "incident_type",
            "description",
        )

        widgets = {
            "asset": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "incident_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": (
                        "Describe what happened to the asset..."
                    ),
                }
            ),
        }

    def __init__(self, *args, employee=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.employee = employee

        self.fields["asset"].queryset = Asset.objects.none()

        if employee is not None:
            self.fields["asset"].queryset = (
                Asset.objects
                .filter(
                    assignments__employee=employee,
                    assignments__is_active=True,
                )
                .distinct()
                .order_by("asset_id")
            )

        self.fields["asset"].required = True
        self.fields["incident_type"].required = True
        self.fields["description"].required = True

        self.fields["description"].widget.attrs["maxlength"] = "5000"

    def clean_asset(self):
        asset = self.cleaned_data.get("asset")

        if not asset:
            raise ValidationError(
                "Please select an assigned asset."
            )

        if self.employee is None:
            raise ValidationError(
                "Employee profile is required."
            )

        is_assigned = asset.assignments.filter(
            employee=self.employee,
            is_active=True,
        ).exists()

        if not is_assigned:
            raise ValidationError(
                "You can only report an asset currently assigned to you."
            )

        if asset.status != Asset.Status.ASSIGNED:
            raise ValidationError(
                "Only an asset currently marked as Assigned can be reported."
            )

        return asset

    def clean_description(self):
        description = self.cleaned_data.get(
            "description",
            "",
        ).strip()

        if not description:
            raise ValidationError(
                "Please describe the damage or loss."
            )

        return description

    def clean(self):
        cleaned_data = super().clean()

        asset = cleaned_data.get("asset")

        if asset and self.employee:

            active_incident_exists = (
                AssetIncident.objects
                .filter(
                    asset=asset,
                    employee=self.employee,
                    status=AssetIncident.Status.PENDING,
                )
                .exists()
            )

            if self.instance.pk:
                active_incident_exists = (
                    AssetIncident.objects
                    .filter(
                        asset=asset,
                        employee=self.employee,
                        status=AssetIncident.Status.PENDING,
                    )
                    .exclude(pk=self.instance.pk)
                    .exists()
                )

            if active_incident_exists:
                raise ValidationError(
                    "You already have a pending damaged/lost report "
                    "for this asset."
                )

        return cleaned_data