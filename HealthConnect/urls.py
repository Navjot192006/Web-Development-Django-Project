from django.urls import path
from . import views

app_name = 'health'

urlpatterns = [
    path('book-appointment/', views.book_appointment_home, name='book_appointment_home'),
    path('appointment-form/', views.appointment_form_view, name='appointment_form'),
    path('schedule-info/', views.schedule_info_view, name='schedule_info'),
    path('day-availability/', views.day_availability_view, name='day_availability'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('appointmentscheduling/', views.appointment_scheduling, name='appointmentscheduling'),
    path('my-appointment-requests/', views.my_appointment_requests, name='my_appointment_requests'),
]