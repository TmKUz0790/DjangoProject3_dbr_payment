# serializers.py
from rest_framework import serializers
from .models import Company

class CompanyRequestSerializer(serializers.Serializer):
    company_name = serializers.CharField(required=True)

class MonthlyPaymentStatusSerializer(serializers.Serializer):
    month = serializers.IntegerField()
    month_name = serializers.CharField()
    year = serializers.IntegerField()
    expected = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    remaining = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()
    arrangement_id = serializers.IntegerField()

class CompanyMonthlyPaymentsSerializer(serializers.ModelSerializer):
    monthly_payment_statuses = MonthlyPaymentStatusSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        fields = ['id', 'name', 'monthly_payment_statuses']