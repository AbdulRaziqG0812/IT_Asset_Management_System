from django import forms

from departments.models import Department

from .models import EmployeeProfile


class EmployeeEditForm(forms.ModelForm):
    """
    HR employee information editing form.

    HR is allowed to update only:
    - Department
    - Phone
    - Job Title
    - Joining Date
    - Address

    Sensitive account and employment workflow fields such as
    employee ID, username, email, employment status, resignation,
    exit and asset-return status are intentionally excluded.
    """

    joining_date = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={
                "class": "form-control",
                "type": "date",
            },
        ),
        label="Joining Date",
        help_text=(
            "Date on which the employee joined the organization."
        ),
    )

    class Meta:
        model = EmployeeProfile

        fields = [
            "department",
            "phone",
            "job_title",
            "address",
        ]

        widgets = {
            "department": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter employee phone number",
                    "autocomplete": "tel",
                }
            ),
            "job_title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter employee job title",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter employee address",
                    "rows": 4,
                }
            ),
        }

        labels = {
            "department": "Department",
            "phone": "Phone",
            "job_title": "Job Title",
            "address": "Address",
        }

        help_texts = {
            "department": (
                "Select the employee's current department."
            ),
            "phone": (
                "Enter the employee's current contact number."
            ),
            "job_title": (
                "Enter the employee's current job title."
            ),
            "address": (
                "Enter the employee's current address."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["department"].queryset = (
            Department.objects
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["department"].empty_label = (
            "Select Department"
        )

        self.fields["phone"].required = False
        self.fields["job_title"].required = False
        self.fields["address"].required = False

        if self.instance and self.instance.pk:
            self.fields["joining_date"].initial = (
                self.instance.date_of_joining
            )

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "")
        return phone.strip()

    def clean_job_title(self):
        job_title = self.cleaned_data.get("job_title", "")
        return job_title.strip()

    def clean_address(self):
        address = self.cleaned_data.get("address", "")
        return address.strip()

    def save(self, commit=True):
        employee = super().save(commit=False)

        employee.date_of_joining = self.cleaned_data.get(
            "joining_date"
        )

        if commit:
            employee.save()

        return employee