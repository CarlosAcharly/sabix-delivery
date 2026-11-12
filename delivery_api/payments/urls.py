from django.urls import path
from .views import ProcessPaymentView, PlatformSettingsView

urlpatterns = [
    path('checkout/<int:order_id>/', ProcessPaymentView.as_view(), name='process-payment'),
    path('settings/', PlatformSettingsView.as_view(), name='platform-settings'),
]