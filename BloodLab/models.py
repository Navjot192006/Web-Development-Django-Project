from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from Donation.models import Patient
import uuid

class BloodTest(models.Model):
    """Model for individual blood tests that can be selected"""
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField()
    test_code = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class TestAppointment(models.Model):
    """Model for blood test appointments"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    appointment_id = models.CharField(max_length=15, primary_key=True, unique=True)
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Patient information (required even if not linked to existing patient)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    
    # Appointment details
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Additional information
    insurance_provider = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Generate appointment ID if not set
        if not self.appointment_id:
            today = timezone.now().date()
            prefix = f"BL-{today.year}-{today.month:02d}-"
            last_appointment = TestAppointment.objects.filter(
                appointment_id__startswith=prefix
            ).order_by('-appointment_id').first()
            
            if last_appointment:
                # Extract number from last appointment ID and increment
                last_num = int(last_appointment.appointment_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
                
            self.appointment_id = f"{prefix}{new_num:04d}"
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.appointment_id} - {self.first_name} {self.last_name}"

class SelectedTest(models.Model):
    """Model for tests selected in an appointment"""
    appointment = models.ForeignKey(TestAppointment, on_delete=models.CASCADE, related_name='selected_tests')
    test = models.ForeignKey(BloodTest, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('appointment', 'test')
    
    def __str__(self):
        return f"{self.appointment.appointment_id} - {self.test.name}"