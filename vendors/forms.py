from django import forms

from .models import Purchase, Vendor


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = [
            "name",
            "contact_person",
            "email",
            "phone",
            "address",
            "notes",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter vendor name",
                }
            ),
            "contact_person": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter contact person name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter vendor email",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter vendor phone number",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter vendor address",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter additional notes",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        queryset = Vendor.objects.filter(name__iexact=name)

        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(
                "A vendor with this name already exists."
            )

        return name


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = [
            "vendor",
            "purchase_date",
            "invoice_number",
            "total_amount",
            "purchase_document",
            "notes",
        ]
        widgets = {
            "vendor": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "purchase_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "invoice_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter invoice number",
                }
            ),
            "total_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Enter total purchase amount",
                }
            ),
            "purchase_document": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter additional purchase notes",
                }
            ),
        }

    def clean_invoice_number(self):
        invoice_number = self.cleaned_data["invoice_number"].strip()

        queryset = Purchase.objects.filter(
            invoice_number__iexact=invoice_number
        )

        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(
                "A purchase with this invoice number already exists."
            )

        return invoice_number

    def clean_total_amount(self):
        total_amount = self.cleaned_data["total_amount"]

        if total_amount is not None and total_amount < 0:
            raise forms.ValidationError(
                "Purchase amount cannot be negative."
            )

        return total_amount