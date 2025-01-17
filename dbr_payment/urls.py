
# urls.py
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.CompanyListView.as_view(), name='company-list'),
    path('company/<int:pk>/', views.CompanyDetailView.as_view(), name='company-detail'),
    path('company/add/', views.add_company, name='add-company'),
    path('arrangement/add/', views.add_arrangement, name='add-arrangement'),
    path('arrangement/<int:pk>/delete/', views.delete_arrangement, name='delete-arrangement'),
    path('payment/add/', views.add_payment, name='add-payment'),
    path('get-arrangements/<int:company_id>/', views.get_arrangements, name='get-arrangements'),
    path('debug/telegram-bot/', views.telegram_bot_debug, name='telegram-bot-debug'),
    path('company/<int:pk>/delete/', views.delete_company, name='delete-company'),
    path('company/<int:pk>/monthly/', views.company_monthly_payments, name='company-monthly-payments'),
    path('api/company/monthly-payments/', views.company_monthly_payments_api, name='company-monthly-payments-api'),
]



