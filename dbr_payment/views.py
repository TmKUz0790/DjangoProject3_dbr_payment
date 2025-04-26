



from calendar import month_name, calendar

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from .models import Company, PaymentArrangement, Payment
from .forms import CompanyForm, PaymentArrangementForm, PaymentForm
from django.views.generic import ListView

import requests
from django.utils import timezone
from django.conf import settings

import calendar
from django.utils import timezone
import requests
from django.conf import settings

from .serializers import CompanyMonthlyPaymentsSerializer


def send_telegram_notification(company, monthly_status):
    """
    Send Telegram notification for current month's payment status

    Args:
        company (Company): The company object
        monthly_status (list): List of monthly payment statuses
    """
    # Get Telegram bot token from global settings
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)

    # Get company-specific chat ID
    chat_id = getattr(company, 'telegram_chat_id', None)

    if not bot_token or not chat_id:
        print(f"Telegram notification not configured for {company.name}")
        return

    # Check if today is the 15th of the month
    today = timezone.now().day
    if today != 15:
        return

    # Get current month's status
    current_month_status = None
    for status in monthly_status:
        if status['status'] in ['UNPAID', 'PARTIAL']:
            current_month_status = status
            break

    if not current_month_status:
        return

    # Calculate remaining amount
    remaining_amount = current_month_status['expected'] - current_month_status['paid']

    # Get arrangements to determine start date
    arrangements = company.arrangements.filter(is_active=True)
    if not arrangements.exists():
        print(f"Active shartnoma mavjud emas {company.name}")
        return

    # Use the first arrangement's start date
    start_date = arrangements.first().start_date

    # Correctly calculate month name and year
    target_month = start_date.month + (current_month_status['month'] - 1)
    target_year = start_date.year + (target_month - 1) // 12
    actual_month = ((target_month - 1) % 12) + 1
    month_name_str = f"{calendar.month_name[actual_month]} {target_year}"

    # Construct message
    if current_month_status['status'] == 'UNPAID':
        message = f"📢 Xurmatli {company.name} kampaniyasi sizni kampaniyamiz xizmatlaridan foydalanish uchun to'lovni amalga oshirishingizni so'raymiz\n\n"
        message += f"Oy: {month_name_str}\n"
        message += f"Oylik Summa: ${current_month_status['expected']:.2f}\n"
        message += f"To'langan Summa: $0.00\n"
        message += f"To'lanishi kerak bo'lgan summa: ${current_month_status['expected']:.2f}\n\n"
        message += "❗ Bu oy uchun to'lov amalga oshirilmagan "
        message += "To'lovni amalga oshiringizni so'raymiz\n\n."
        message+= "Xurmat bilan DBS campaniyasi"

    elif current_month_status['status'] == 'PARTIAL':
        message = f"📢 Xurmatli {company.name} kampaniyasi sizni kampaniyamiz xizmatlaridan foydalanish uchun to'lovni amalga oshirishingizni so'raymiz\n\n"
        message += f"Oy: {month_name_str}\n"
        message += f"Oylik kelishuv: ${current_month_status['expected']:.2f}\n"
        message += f"To'langan summa: ${current_month_status['paid']:.2f}\n"
        message += f"To'lanishi kerak bo'lgan summa: ${remaining_amount:.2f}\n\n"
        message += "To'lovni amalga oshiringizni so'raymiz\n\n."
        message += "Xurmat bilan DBS campaniyasi"

    # Send Telegram notification
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        params = {
            "chat_id": chat_id,
            "text": message
        }
        response = requests.post(url, params=params)
        response.raise_for_status()
        print(f"Telegram notification sent for {company.name}")
    except Exception as e:
        print(f"Failed to send Telegram notification for {company.name}: {e}")

import datetime
from django.shortcuts import render
from django.views.generic import ListView

from calendar import month_name
from django.utils import timezone


class CompanyListView(ListView):
    model = Company
    template_name = 'payments/company_list.html'
    context_object_name = 'companies'
    ordering = ['name']

    def get_queryset(self):
        companies = []
        queryset = super().get_queryset()
        today = timezone.now().date()

        for company in queryset:
            company_info = {
                'company': company,
                'monthly_status': [],
                'total_to_pay': Decimal('0'),
                'total_paid': Decimal('0'),
                'current_due': Decimal('0'),  # Due up to current month
                'payment_percentage': 0
            }

            # Get all active arrangements for the company
            arrangements = company.arrangements.filter(is_active=True)

            total_expected_until_now = Decimal('0')
            total_paid = Decimal('0')

            for arrangement in arrangements:
                start_date = arrangement.start_date
                payments = company.payments.filter(arrangement=arrangement)

                # Calculate months elapsed since arrangement start
                months_elapsed = (
                        (today.year - start_date.year) * 12
                        + today.month - start_date.month
                        + 1  # Include current month
                )

                # Cap at arrangement duration
                months_to_consider = min(months_elapsed, arrangement.number_of_months)

                # Only consider positive month counts
                if months_to_consider > 0:
                    # Calculate expected payment until now
                    expected_until_now = arrangement.monthly_amount * months_to_consider
                    total_expected_until_now += expected_until_now

                    # Calculate actual payments made
                    arrangement_payments = payments.filter(month_number__lte=months_to_consider)
                    paid_amount = arrangement_payments.aggregate(
                        total=Sum('amount_paid'))['total'] or Decimal('0')
                    total_paid += paid_amount

                # Calculate total amount that will eventually be due for this arrangement
                company_info['total_to_pay'] += (arrangement.monthly_amount * arrangement.number_of_months)

                # Calculate monthly status for display
                for month in range(1, arrangement.number_of_months + 1):
                    target_month = start_date.month + (month - 1)
                    target_year = start_date.year + (target_month - 1) // 12
                    actual_month = ((target_month - 1) % 12) + 1
                    month_name_str = f"{month_name[actual_month]} {target_year}"

                    month_payments = payments.filter(month_number=month)
                    total_month_paid = month_payments.aggregate(
                        total=Sum('amount_paid'))['total'] or Decimal('0')

                    if total_month_paid >= arrangement.monthly_amount:
                        status = 'PAID'
                    elif total_month_paid > 0:
                        status = 'PARTIAL'
                    else:
                        status = 'UNPAID'

                    month_data = {
                        'month': month,
                        'month_name': month_name_str,
                        'expected': arrangement.monthly_amount,
                        'paid': total_month_paid,
                        'status': status
                    }
                    company_info['monthly_status'].append(month_data)

            # Update company info with calculated values
            company_info['total_paid'] = total_paid
            company_info['current_due'] = total_expected_until_now - total_paid

            # Calculate payment percentage based on current dues
            if total_expected_until_now > 0:
                payment_percentage = (total_paid / total_expected_until_now) * 100
                company_info['payment_percentage'] = round(payment_percentage, 2)

            companies.append(company_info)

        return companies

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class CompanyDetailView(DetailView):
    model = Company
    template_name = 'payments/company_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arrangements'] = self.object.arrangements.all().order_by('-created_at')
        context['payments'] = self.object.payments.all().order_by('-payment_date')
        return context


def add_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                payment = form.save()
                messages.success(request, 'Tolov amalga oshdi!')
                return redirect('payments:company-detail', pk=payment.company.pk)
            except Exception as e:
                messages.error(request, f'Error recording payment: {str(e)}')
                return render(request, 'payments/payment_form.html', {'form': form})
    else:
        initial_data = {}
        company_id = request.GET.get('company')
        if company_id:
            initial_data['company'] = company_id
        form = PaymentForm(initial=initial_data)

    return render(request, 'payments/payment_form.html', {'form': form})
def add_company(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save()
            messages.success(request, 'Kampaniya kiritil !')
            return redirect('payments:company-list')
    else:
        form = CompanyForm()

    return render(request, 'payments/company_form.html', {'form': form})


def add_arrangement(request):
    if request.method == 'POST':
        form = PaymentArrangementForm(request.POST)
        if form.is_valid():
            arrangement = form.save()
            messages.success(request, 'Shartnoma qoshildi')
            return redirect('payments:company-detail', pk=arrangement.company.pk)
    else:
        company_id = request.GET.get('company')
        initial_data = {}
        if company_id:
            initial_data['company'] = company_id
        form = PaymentArrangementForm(initial=initial_data)

    return render(request, 'payments/arrangement_form.html', {'form': form})


def get_arrangements(request, company_id):
    arrangements = PaymentArrangement.objects.filter(
        company_id=company_id,
        is_active=True
    ).values('id', 'monthly_amount', 'start_date', 'number_of_months')

    arrangements_list = list(arrangements)
    for arrangement in arrangements_list:
        arrangement['monthly_amount'] = float(arrangement['monthly_amount'])
        arrangement['start_date'] = arrangement['start_date'].strftime('%Y-%m-d')

    return JsonResponse(arrangements_list, safe=False)


def delete_arrangement(request, pk):
    arrangement = get_object_or_404(PaymentArrangement, pk=pk)
    company_id = arrangement.company.id
    arrangement.delete()
    messages.success(request, 'Shartnoma bekor qilindi')
    return redirect('payments:company-detail', pk=company_id)


from django.db.models import Sum
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone


class CompanyDetailView(DetailView):
    model = Company
    template_name = 'payments/company_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get arrangements and payments
        arrangements = self.object.arrangements.all().order_by('-created_at')
        payments = self.object.payments.all().order_by('-payment_date')

        # Calculate total amounts
        total_to_pay = sum(arr.monthly_amount * arr.number_of_months for arr in arrangements)
        total_paid = sum(payment.amount_paid for payment in payments)
        remaining_balance = total_to_pay - total_paid
        payment_percentage = (total_paid / total_to_pay * 100) if total_to_pay > 0 else 0



        # Process payments and arrangements for monthly status
        monthly_status = []

        for arrangement in arrangements:
            for month in range(1, arrangement.number_of_months + 1):
                month_payments = [
                    payment for payment in payments
                    if payment.month_number == month
                       and payment.arrangement_id == arrangement.id
                ]

                # Calculate total paid for this month
                total_month_paid = sum(payment.amount_paid for payment in month_payments)

                if total_month_paid >= arrangement.monthly_amount:
                    status = 'PAID'
                elif total_month_paid > 0:
                    status = 'PARTIAL'
                else:
                    status = 'UNPAID'

                monthly_status.append({
                    'month': month,
                    'expected': arrangement.monthly_amount,
                    'paid': total_month_paid,
                    'status': status,
                    'arrangement_id': arrangement.id
                })

        # Debug logging
        print(f"Company: {self.object.name}")
        print(f"Telegram Chat ID: {getattr(self.object, 'telegram_chat_id', 'Not Set')}")

        # Send Telegram notification if applicable
        if hasattr(self.object, 'telegram_chat_id') and self.object.telegram_chat_id:
            send_telegram_notification(self.object, monthly_status)
        else:
            print(f"Skipping Telegram notification for {self.object.name} - No Chat ID")

        context.update({
            'arrangements': arrangements,
            'payments': payments,
            'total_to_pay': total_to_pay,
            'total_paid': total_paid,
            'remaining_balance': remaining_balance,
            'payment_percentage': payment_percentage,
            'monthly_status': sorted(monthly_status, key=lambda x: (x['arrangement_id'], x['month']))
        })

        return context

from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from .telegram_utils import debug_telegram_bot



@staff_member_required
@require_http_methods(["GET"])
def telegram_bot_debug(request):
    """
    Debug endpoint for Telegram bot
    """
    # Get company ID from query parameter if provided
    company_id = request.GET.get('company_id')

    if company_id:
        try:
            company = Company.objects.get(pk=company_id)
            debug_result = debug_telegram_bot(company)
        except Company.DoesNotExist:
            debug_result = {
                'success': False,
                'error': f'Company with ID {company_id} not found'
            }
    else:
        # Global debug
        debug_result = debug_telegram_bot()

    return JsonResponse(debug_result)


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages


@login_required
def delete_company(request, pk):
    """
    View to delete a company with confirmation
    """
    # Get the company or return 404 if not found
    company = get_object_or_404(Company, pk=pk)

    # Handle POST request (actual deletion)
    if request.method == 'POST':
        # Check if the user confirmed the deletion
        if request.POST.get('confirm') == 'yes':
            try:
                # Delete the company
                company_name = company.name
                company.delete()

                # Add success message
                messages.success(request, f'Company "{company_name}" has been deleted successfully.')

                # Redirect to company list
                return redirect('payments:company-list')
            except Exception as e:
                # Handle any deletion errors
                messages.error(request, f'Error deleting company: {str(e)}')
                return redirect('payments:company-list')
        else:
            # If not confirmed, redirect back to list
            messages.warning(request, 'Company deletion cancelled.')
            return redirect('payments:company-list')

    # GET request - show confirmation page
    return render(request, 'payments/company_delete_confirm.html', {
        'company': company
    })


from django.shortcuts import render, get_object_or_404
from .models import Company

def company_monthly_payments(request, pk):
    company = get_object_or_404(Company, pk=pk)
    arrangements = company.arrangements.filter(is_active=True)
    monthly_payment_statuses = []
    today = datetime.date.today()
    current_month = today.month
    current_year = today.year

    # Initialize total trackers
    total_expected = Decimal('0')
    total_paid = Decimal('0')
    current_due = Decimal('0')  # Only for months up to current month

    for arrangement in arrangements:
        first_arrangement_month = arrangement.start_date.month
        first_arrangement_year = arrangement.start_date.year

        last_arrangement_month = (arrangement.start_date.month + arrangement.number_of_months - 1) % 12
        last_arrangement_year = arrangement.start_date.year + (
                    arrangement.start_date.month + arrangement.number_of_months - 1) // 12

        if (first_arrangement_year < current_year or (
                first_arrangement_year == current_year and first_arrangement_month <= current_month)) and (
                last_arrangement_year > current_year or (
                last_arrangement_year == current_year and last_arrangement_month >= current_month)):
            if current_year > first_arrangement_year:
                month_diff = (current_year - first_arrangement_year) * 12 + (
                            current_month - first_arrangement_month) + 1
            else:
                month_diff = current_month - first_arrangement_month + 1

            for month in range(1, arrangement.number_of_months + 1):
                target_month = arrangement.start_date.month + (month - 1)
                target_year = arrangement.start_date.year + (target_month - 1) // 12
                actual_month = ((target_month - 1) % 12) + 1

                # Check if this month is current or past
                is_past_or_current = (
                        target_year < current_year or
                        (target_year == current_year and actual_month <= current_month)
                )

                payments_this_month = company.payments.filter(arrangement=arrangement, month_number=month)
                total_paid_this_month = payments_this_month.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
                monthly_due = arrangement.monthly_amount
                remaining_in_month = monthly_due - total_paid_this_month

                status = 'UNPAID'
                if total_paid_this_month == monthly_due:
                    status = 'PAID'
                elif total_paid_this_month > Decimal('0') and total_paid_this_month < monthly_due:
                    status = 'PARTIALLY_PAID'

                # Update running totals
                total_expected += monthly_due
                total_paid += total_paid_this_month

                # Only add to current_due if it's a past or current month
                if is_past_or_current:
                    current_due += remaining_in_month

                monthly_payment_statuses.append({
                    'month': month,
                    'month_name': calendar.month_name[actual_month],
                    'year': target_year,
                    'expected': monthly_due,
                    'paid': total_paid_this_month,
                    'remaining': remaining_in_month,
                    'status': status,
                    'arrangement_id': arrangement.id,
                    'is_past_or_current': is_past_or_current  # Added this flag for template use
                })

    # Sort the payment statuses by year and month
    monthly_payment_statuses.sort(key=lambda x: (x['year'], list(calendar.month_name).index(x['month_name'])))

    context = {
        'company': company,
        'monthly_payment_statuses': monthly_payment_statuses,
        'total_expected': total_expected,
        'total_paid': total_paid,
        'current_due': current_due  # Changed from total_remaining to current_due
    }

    return render(request, 'payments/company_monthly_payments.html', context)
from django.shortcuts import get_object_or_404

# views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from decimal import Decimal
from django.db.models import Sum
import calendar
import datetime


@api_view(['POST'])
def company_monthly_payments_api(request):
    # Get credentials from request
    username = request.data.get('username')
    password = request.data.get('password')
    company_name = request.data.get('company_name')

    # Validate required fields
    if not all([username, password, company_name]):
        return Response({
            'error': 'Username, password, and company_name are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Authenticate user
    user = authenticate(username=username, password=password)
    if not user:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)

    # Get company
    try:
        company = Company.objects.get(name=company_name)
    except Company.DoesNotExist:
        return Response({
            'error': f"Company with name '{company_name}' not found"
        }, status=status.HTTP_404_NOT_FOUND)

    # Get arrangements and calculate payments
    arrangements = company.arrangements.filter(is_active=True)
    monthly_payment_statuses = []
    total_to_pay = Decimal('0')
    total_paid = Decimal('0')
    total_current_due = Decimal('0')

    today = datetime.date.today()
    current_month = today.month
    current_year = today.year

    for arrangement in arrangements:
        first_arrangement_month = arrangement.start_date.month
        first_arrangement_year = arrangement.start_date.year

        last_arrangement_month = (arrangement.start_date.month + arrangement.number_of_months - 1) % 12
        last_arrangement_year = arrangement.start_date.year + (
                    arrangement.start_date.month + arrangement.number_of_months - 1) // 12

        # Calculate total to pay for this arrangement
        arrangement_total = arrangement.monthly_amount * arrangement.number_of_months
        total_to_pay += arrangement_total

        # Calculate months elapsed since arrangement start
        months_elapsed = (current_year - first_arrangement_year) * 12 + (current_month - first_arrangement_month) + 1

        if (first_arrangement_year < current_year or
            (first_arrangement_year == current_year and first_arrangement_month <= current_month)) and \
                (last_arrangement_year > current_year or
                 (last_arrangement_year == current_year and last_arrangement_month >= current_month)):

            if current_year > first_arrangement_year:
                month_diff = (current_year - first_arrangement_year) * 12 + (
                            current_month - first_arrangement_month) + 1
            else:
                month_diff = current_month - first_arrangement_month + 1

            # Calculate how many months should be included in current due
            months_to_consider = min(months_elapsed, arrangement.number_of_months)
            if months_to_consider > 0:
                expected_amount_till_now = arrangement.monthly_amount * months_to_consider
                actual_paid = company.payments.filter(
                    arrangement=arrangement,
                    month_number__lte=months_to_consider
                ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
                total_current_due += expected_amount_till_now - actual_paid

            for month in range(1, arrangement.number_of_months + 1):
                target_month = arrangement.start_date.month + (month - 1)
                target_year = arrangement.start_date.year + (target_month - 1) // 12
                actual_month = ((target_month - 1) % 12) + 1

                payments_this_month = company.payments.filter(arrangement=arrangement, month_number=month)
                total_paid_this_month = payments_this_month.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
                total_paid += total_paid_this_month

                monthly_due = arrangement.monthly_amount
                remaining_in_month = monthly_due - total_paid_this_month

                # Initialize status
                payment_status = 'UNPAID'  # Default status

                if total_paid_this_month >= monthly_due:
                    payment_status = 'PAID'
                elif total_paid_this_month > Decimal('0'):
                    payment_status = 'PARTIALLY_PAID'

                monthly_payment_statuses.append({
                    'month': month,
                    'month_name': calendar.month_name[actual_month],
                    'year': target_year,
                    'expected': monthly_due,
                    'paid': total_paid_this_month,
                    'remaining': remaining_in_month,
                    'status': payment_status,
                    'arrangement_id': arrangement.id
                })

    # Calculate payment percentage
    payment_percentage = (total_paid / total_to_pay * 100) if total_to_pay > 0 else 0

    response_data = {
        'id': company.id,
        'name': company.name,
        'total_to_pay': total_to_pay,
        'total_paid': total_paid,
        'total_current_due': total_current_due,
        'remaining_balance': total_to_pay - total_paid,
        'payment_percentage': round(payment_percentage, 2),
        'monthly_payment_statuses': sorted(monthly_payment_statuses,
                                           key=lambda x: (x['year'], x['month']))
    }

    return Response(response_data)


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Payment


@login_required
def delete_payment(request, pk):
    """
    View to delete a payment with confirmation
    """
    # Get the payment or return 404 if not found
    payment = get_object_or_404(Payment, pk=pk)
    company_id = payment.company.id

    # Handle POST request (actual deletion)
    if request.method == 'POST':
        # Check if the user confirmed the deletion
        if request.POST.get('confirm') == 'yes':
            try:
                # Store payment details for message
                payment_amount = payment.amount_paid
                payment_date = payment.payment_date

                # Delete the payment
                payment.delete()

                # Add success message
                messages.success(
                    request,
                    f'Payment of ${payment_amount} made on {payment_date} has been deleted successfully.'
                )

                # Redirect to company detail page
                return redirect('payments:company-detail', pk=company_id)
            except Exception as e:
                # Handle any deletion errors
                messages.error(request, f'Error deleting payment: {str(e)}')
                return redirect('payments:company-detail', pk=company_id)
        else:
            # If not confirmed, redirect back to company detail
            messages.warning(request, 'Payment deletion cancelled.')
            return redirect('payments:company-detail', pk=company_id)

    # GET request - show confirmation page
    return render(request, 'payments/payment_delete_confirm.html', {
        'payment': payment
    })


def all_companies_payments(request):
    companies = Company.objects.filter(arrangements__is_active=True).distinct()
    company_payment_data = []
    today = datetime.date.today()
    current_month = today.month
    current_year = today.year

    for company in companies:
        arrangements = company.arrangements.filter(is_active=True)
        total_expected = Decimal('0')
        total_paid = Decimal('0')
        current_due = Decimal('0')

        for arrangement in arrangements:
            first_arrangement_month = arrangement.start_date.month
            first_arrangement_year = arrangement.start_date.year

            for month in range(1, arrangement.number_of_months + 1):
                target_month = arrangement.start_date.month + (month - 1)
                target_year = arrangement.start_date.year + (target_month - 1) // 12
                actual_month = ((target_month - 1) % 12) + 1

                # Check if this month is current or past
                is_past_or_current = (
                        target_year < current_year or
                        (target_year == current_year and actual_month <= current_month)
                )

                payments_this_month = company.payments.filter(
                    arrangement=arrangement,
                    month_number=month
                )
                total_paid_this_month = payments_this_month.aggregate(
                    total=Sum('amount_paid')
                )['total'] or Decimal('0')

                monthly_due = arrangement.monthly_amount
                remaining_in_month = monthly_due - total_paid_this_month

                # Update running totals
                total_expected += monthly_due
                total_paid += total_paid_this_month

                # Only add to current_due if it's a past or current month
                if is_past_or_current:
                    current_due += remaining_in_month

        # Calculate payment status for the company
        if current_due == 0:
            payment_status = 'PAID'
        elif total_paid == 0:
            payment_status = 'UNPAID'
        else:
            payment_status = 'PARTIALLY_PAID'

        company_payment_data.append({
            'company': company,
            'total_expected': total_expected,
            'total_paid': total_paid,
            'current_due': current_due,
            'payment_status': payment_status,
            'arrangements_count': arrangements.count(),
            'last_payment_date': company.payments.order_by(
                '-payment_date').first().payment_date if company.payments.exists() else None
        })

    # Calculate grand totals
    grand_total_expected = sum(data['total_expected'] for data in company_payment_data)
    grand_total_paid = sum(data['total_paid'] for data in company_payment_data)
    grand_total_due = sum(data['current_due'] for data in company_payment_data)

    context = {
        'company_payment_data': company_payment_data,
        'grand_total_expected': grand_total_expected,
        'grand_total_paid': grand_total_paid,
        'grand_total_due': grand_total_due,
    }

    return render(request, 'payments/all_companies_payments.html', context)