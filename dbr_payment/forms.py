from django import forms
from django.core.exceptions import ValidationError

from .models import Company, PaymentArrangement, Payment


# class CompanyForm(forms.ModelForm):
#     class Meta:
#         model = Company
#         fields = ['name', 'email', 'contact_number', 'address']
#         widgets = {
#             'name': forms.TextInput(attrs={'class': 'form-control'}),
#             'email': forms.EmailInput(attrs={'class': 'form-control'}),
#             'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
#             'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
#         }
#
from django import forms
from .models import Company


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'name',
            'email',
            'contact_number',
            'address',
            'telegram_chat_id'  # Include this field
        ]
        # widgets = {
        #     'telegram_chat_id': forms.TextInput(attrs={
        #         'placeholder': 'Optional: Telegram Chat ID for notifications',
        #         'help_text': 'You can find this by chatting with your Telegram bot and checking the update'
        #     })
        # }

    def clean_telegram_chat_id(self):
        """
        Optional validation for Telegram Chat ID
        """
        telegram_chat_id = self.cleaned_data.get('telegram_chat_id')

        # If provided, you can add some basic validation
        if telegram_chat_id:
            # Remove any whitespace
            telegram_chat_id = telegram_chat_id.strip()

            # Optional: Add some basic format checking
            if not telegram_chat_id.isdigit():
                raise forms.ValidationError("Telegram Chat ID should be a numeric value.")

        return telegram_chat_id

class PaymentArrangementForm(forms.ModelForm):
    class Meta:
        model = PaymentArrangement
        fields = ['company', 'monthly_amount', 'number_of_months', 'start_date', 'is_active']
        widgets = {
            'company': forms.Select(attrs={
                'class': 'form-select',
            }),
            'monthly_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'number_of_months': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'initial' in kwargs and 'company' in kwargs['initial']:
            self.fields['company'].initial = kwargs['initial']['company']
            self.fields['is_active'].initial = True


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['company', 'arrangement', 'payment_date', 'amount_paid',
                  'payment_method', 'notes']
        widgets = {
            'company': forms.Select(attrs={
                'class': 'form-select'
            }),
            'arrangement': forms.Select(attrs={
                'class': 'form-select'
            }),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'amount_paid': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'payment_method': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['arrangement'].queryset = PaymentArrangement.objects.none()

        if 'company' in self.data:
            try:
                company_id = int(self.data.get('company'))
                self.fields['arrangement'].queryset = PaymentArrangement.objects.filter(
                    company_id=company_id,
                    is_active=True
                )
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.company:
            self.fields['arrangement'].queryset = PaymentArrangement.objects.filter(
                company=self.instance.company,
                is_active=True
            )