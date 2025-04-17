from django.db import models
from django.conf import settings # To get the User model

# Create your models here.

class Doctor(models.Model):
    SPECIALTY_CHOICES = [
        ('Cardiology', 'Cardiology'),
        ('Dermatology', 'Dermatology'),
        ('Endocrinology', 'Endocrinology'),
        ('Gastroenterology', 'Gastroenterology'),
        ('Neurology', 'Neurology'),
        ('Orthopedics', 'Orthopedics'),
        ('Pediatrics', 'Pediatrics'),
        ('Psychiatry', 'Psychiatry'),
        ('Cardiac Electrophysiology', 'Cardiac Electrophysiology'),
        ('Preventive Cardiology', 'Preventive Cardiology'),
    ]
    
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100, choices=SPECIALTY_CHOICES)
    bio = models.TextField()
    experience_years = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.0)
    reviews_count = models.IntegerField(default=0)
    clinic_name = models.CharField(max_length=200)
    clinic_address = models.CharField(max_length=255)
    profile_image = models.URLField(default="https://images.unsplash.com/photo-1559839734-2b71ea197ec2?ixlib=rb-1.2.1&auto=format&fit=crop&w=634&q=80")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Dr. {self.name} - {self.specialty}"
    
    class Meta:
        ordering = ['name']

class DoctorAppointment(models.Model):
    STATUS_CHOICES = [
        ('Requested', 'Requested'),
        ('Confirmed', 'Confirmed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    APPOINTMENT_TYPE_CHOICES = [
        ('In-Person', 'In-Person'),
        ('Virtual', 'Virtual'),
    ]

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_appointments')
    doctor_name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100)
    appointment_date = models.DateField()
    appointment_time = models.CharField(max_length=20) # e.g., "9:00 AM", "10:30 AM"
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPE_CHOICES, default='In-Person')
    reason_for_visit = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Requested')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Appointment for {self.patient.username} with {self.doctor_name} on {self.appointment_date} at {self.appointment_time}"

    class Meta:
        ordering = ['-appointment_date', '-appointment_time']

# New model specifically for the general request form (ScheduleInfo.html)
class AppointmentRequest(models.Model):
    REQUEST_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Reviewed', 'Reviewed'),
        ('Contacted', 'Contacted'),
        ('Scheduled', 'Scheduled'),
        ('Declined', 'Declined'),
    ]
    APPOINTMENT_TYPE_CHOICES = DoctorAppointment.APPOINTMENT_TYPE_CHOICES # Reuse choices

    # Assuming the request is made by a logged-in user
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointment_requests')
    preferred_date = models.DateField()
    preferred_time = models.CharField(max_length=20) # Store formatted time, e.g., "8:00 AM"
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPE_CHOICES)
    selected_doctor = models.CharField(max_length=150, blank=True, null=True) # Stores the string like "Dr. Smith - Cardiologist" or "Any available doctor"
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=REQUEST_STATUS_CHOICES, default='Pending')
    request_timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request by {self.requested_by.username} for {self.preferred_date} around {self.preferred_time}"

    class Meta:
        ordering = ['-request_timestamp']

class TimeSlot(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='time_slots')
    date = models.DateField()
    time = models.CharField(max_length=10)  # e.g. "9:00 AM"
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.doctor.name} - {self.date} - {self.time} - {'Available' if self.is_available else 'Booked'}"
    
    class Meta:
        ordering = ['date', 'time']
        unique_together = ['doctor', 'date', 'time']
