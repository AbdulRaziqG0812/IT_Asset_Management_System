from django import forms

from .models import Department


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = [
            "name",
            "code",
            "description",
            "is_active",
        ]

        labels = {
            "name": "Department Name",
            "code": "Department Code",
            "description": "Description",
            "is_active": "Active Department",
        }

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter department name",
                    "maxlength": 100,
                }
            ),
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter department code",
                    "maxlength": 30,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter department description",
                    "rows": 4,
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

        if not name:
            raise forms.ValidationError(
                "Department name is required."
            )

        return name

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()

        if not code:
            raise forms.ValidationError(
                "Department code is required."
            )

        return code