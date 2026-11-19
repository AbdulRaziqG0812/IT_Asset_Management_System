from django import forms

from .models import AssetRequest


class AssetRequestForm(forms.ModelForm):
    class Meta:
        model = AssetRequest

        fields = [
            "asset_category",
            "asset_name",
            "quantity",
            "reason",
            "priority",
        ]

        widgets = {
            "asset_category": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Laptop, Monitor, Printer",
                    "maxlength": 50,
                    "autocomplete": "off",
                }
            ),
            "asset_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Dell Latitude 5420",
                    "maxlength": 150,
                    "autocomplete": "off",
                }
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "step": 1,
                }
            ),
            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "maxlength": 5000,
                    "placeholder": "Explain why this asset is required.",
                }
            ),
            "priority": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def clean_asset_category(self):
        asset_category = self.cleaned_data.get("asset_category", "").strip()

        if not asset_category:
            raise forms.ValidationError(
                "Asset category is required."
            )

        if len(asset_category) > 50:
            raise forms.ValidationError(
                "Asset category cannot exceed 50 characters."
            )

        return asset_category

    def clean_asset_name(self):
        asset_name = self.cleaned_data.get("asset_name", "").strip()

        if len(asset_name) > 150:
            raise forms.ValidationError(
                "Asset name cannot exceed 150 characters."
            )

        return asset_name

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")

        if quantity is None:
            raise forms.ValidationError(
                "Quantity is required."
            )

        if quantity < 1:
            raise forms.ValidationError(
                "Quantity must be at least 1."
            )

        return quantity

    def clean_reason(self):
        reason = self.cleaned_data.get("reason", "").strip()

        if not reason:
            raise forms.ValidationError(
                "Reason is required."
            )

        if len(reason) > 5000:
            raise forms.ValidationError(
                "Reason cannot exceed 5000 characters."
            )

        return reason

    def clean_priority(self):
        priority = self.cleaned_data.get("priority")

        valid_priorities = {
            choice[0]
            for choice in AssetRequest.Priority.choices
        }

        if priority not in valid_priorities:
            raise forms.ValidationError(
                "Invalid priority selected."
            )

        return priority