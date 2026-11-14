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
                    "placeholder": "e.g. Laptop, Monitor, Printer",
                }
            ),
            "asset_name": forms.TextInput(
                attrs={
                    "placeholder": "e.g. Dell Latitude 5420",
                }
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "min": 1,
                }
            ),
            "reason": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Explain why this asset is required.",
                }
            ),
            "priority": forms.Select(),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]

        if quantity < 1:
            raise forms.ValidationError(
                "Quantity must be at least 1."
            )

        return quantity

    def clean_asset_category(self):
        asset_category = self.cleaned_data["asset_category"].strip()

        if not asset_category:
            raise forms.ValidationError(
                "Asset category is required."
            )

        return asset_category

    def clean_reason(self):
        reason = self.cleaned_data["reason"].strip()

        if not reason:
            raise forms.ValidationError(
                "Reason is required."
            )

        return reason