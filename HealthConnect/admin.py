from django.contrib import admin
from .models import DoctorAppointment, AppointmentRequest

# Register your models here.

@admin.register(DoctorAppointment)
class DoctorAppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor_name', 'specialty', 'appointment_date', 'appointment_time', 'status', 'created_at')
    list_filter = ('status', 'appointment_date', 'specialty')
    search_fields = ('patient__username', 'patient__email', 'doctor_name', 'specialty')
    date_hierarchy = 'appointment_date'

# Register the new model
@admin.register(AppointmentRequest)
class AppointmentRequestAdmin(admin.ModelAdmin):
    list_display = ('requested_by', 'preferred_date', 'preferred_time', 'appointment_type', 'selected_doctor', 'status', 'request_timestamp')
    list_filter = ('status', 'preferred_date', 'appointment_type')
    search_fields = ('requested_by__username', 'requested_by__email', 'selected_doctor', 'reason')
    date_hierarchy = 'request_timestamp'
