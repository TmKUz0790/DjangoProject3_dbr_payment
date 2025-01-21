
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import datetime, timedelta
import calendar


from django.db import models

class Company(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    contact_number = models.CharField(max_length=20)
    address = models.TextField()
    telegram_chat_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Telegram Chat ID"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Companies"
class PaymentArrangement(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='arrangements')
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    number_of_months = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Calculate end date based on start date and number of months
        if self.start_date and self.number_of_months:
            # Add months by calculating days
            year = self.start_date.year + (self.start_date.month + self.number_of_months - 1) // 12
            month = (self.start_date.month + self.number_of_months - 1) % 12 + 1
            last_day = calendar.monthrange(year, month)[1]
            self.end_date = datetime(year, month, min(self.start_date.day, last_day)).date()
        super().save(*args, **kwargs)

    @property
    def total_amount(self):
        return self.monthly_amount * self.number_of_months

    def get_due_dates(self):
        """Returns a list of all payment due dates"""
        due_dates = []
        current_date = self.start_date

        for _ in range(self.number_of_months):
            due_dates.append(current_date)
            # Calculate next month's date
            year = current_date.year + (current_date.month) // 12
            month = current_date.month % 12 + 1
            # Handle day overflow for months with fewer days
            last_day = calendar.monthrange(year, month)[1]
            day = min(current_date.day, last_day)
            current_date = datetime(year, month, day).date()

        return due_dates

    def __str__(self):
        return f"{self.company.name} - ${self.monthly_amount}/month for {self.number_of_months} months"


from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Payment(models.Model):
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('PARTIAL', 'Partially Paid'),
        ('UNPAID', 'Unpaid'),
        ('OVERDUE', 'Overdue'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='payments')
    arrangement = models.ForeignKey(PaymentArrangement, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    payment_method = models.CharField(max_length=50)
    month_number = models.PositiveIntegerField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.arrangement and self.payment_date:
            start_date = self.arrangement.start_date
            payment_year = self.payment_date.year
            payment_month = self.payment_date.month
            start_year = start_date.year
            start_month = start_date.month

            # Calculate month number
            self.month_number = ((payment_year - start_year) * 12 + payment_month - start_month) + 1
            self.month_number = min(self.month_number, self.arrangement.number_of_months)
            self.month_number = max(1, self.month_number)

            # Set status based on payment amount
            monthly_amount = self.arrangement.monthly_amount
            if self.amount_paid >= monthly_amount:
                self.status = 'COMPLETED'
            elif self.amount_paid > 0:
                self.status = 'PARTIAL'
            else:
                self.status = 'UNPAID'

        super().save(*args, **kwargs)

    def get_month_name(self):
        if self.arrangement and self.month_number:
            start_date = self.arrangement.start_date
            target_month = start_date.month + (self.month_number - 1)
            target_year = start_date.year + (target_month - 1) // 12
            actual_month = ((target_month - 1) % 12) + 1
            return f"{calendar.month_name[actual_month]} {target_year}"
        return ""

    class Meta:
        ordering = ['arrangement', 'month_number']

    def __str__(self):
        month_display = self.get_month_name()
        return f"{self.company.name} - {month_display} - ${self.amount_paid}"






