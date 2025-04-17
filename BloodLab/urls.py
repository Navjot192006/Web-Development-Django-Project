from django.urls import path
from . import views

app_name = 'bloodlab'

urlpatterns = [
    path('', views.labtest_home, name='labtest_home'),
    path('test-form/', views.blood_test_form_view, name='test_form'),
    path('submit-appointment/', views.submit_appointment, name='submit_appointment'),
    path('appointment/confirmation/', views.appointment_confirmation, name='appointment_confirmation'),
    path('get-available-slots/', views.get_available_slots, name='get_available_slots'),
    path('insurance-verification/', views.InsuranceVerification, name='insurance_verification'),
    path('about/', views.test_about, name='test_about'),
    path('pricing/', views.test_prices, name='test_prices'),
]