from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Model for storing general fund donations
class Donation(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    message = models.TextField(blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} - ${self.amount}"

# Model for storing blood donation records/requests 
# (Should primarily store donation EVENT data)
class BloodDonation(models.Model):
    name = models.CharField(max_length=100) # Consider linking to UserProfile instead
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10)
    blood_group = models.CharField(max_length=3)
    contact = models.CharField(max_length=15) # Consider linking to UserProfile instead
    email = models.EmailField() # Consider linking to UserProfile instead
    address = models.TextField() # Consider linking to UserProfile instead
    health_info = models.TextField(blank=True, null=True)
    donation_date = models.DateField()
    # Removed profile picture from here - moved to UserProfile
    # profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.blood_group}) - {self.donation_date}"

# Model for storing user profile information
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    blood_group = models.CharField(max_length=3, blank=True, null=True)
    contact = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True, default='profile_pictures/default.png')
    # Add any other profile-specific fields here

    def __str__(self):
        return self.user.username

# Model for storing blood requests
class BloodRequest(models.Model):
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10)
    blood_group = models.CharField(max_length=3)
    contact = models.CharField(max_length=15)
    email = models.EmailField()
    hospital = models.CharField(max_length=200)
    address = models.TextField()
    urgency_choices = [
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency'),
    ]
    urgency = models.CharField(max_length=10, choices=urgency_choices, default='normal')
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Request for {self.blood_group} by {self.name} ({self.created_at.strftime('%Y-%m-%d')})"

# Model for storing doctor information
class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor')
    specialty = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50)
    years_of_experience = models.PositiveIntegerField(default=0)
    contact_number = models.CharField(max_length=15, blank=True)
    profile_image = models.ImageField(upload_to='doctor_profiles/', blank=True, null=True)
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"

# Model for storing patient information
class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient')
    blood_group = models.CharField(max_length=3, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=100, blank=True, null=True)
    
    # Medical information
    height = models.PositiveIntegerField(blank=True, null=True, help_text="Height in cm")
    weight = models.PositiveIntegerField(blank=True, null=True, help_text="Weight in kg")
    allergies = models.TextField(blank=True, null=True)
    chronic_conditions = models.TextField(blank=True, null=True)
    current_medications = models.TextField(blank=True, null=True)
    past_surgeries = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()}"

# Model for storing appointment information
class Appointment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    reason = models.TextField()
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.patient.user.get_full_name()} - {self.appointment_date}"
    
    def get_status_display(self):
        return dict(self.STATUS_CHOICES)[self.status]

# Model for storing lab reports
class LabReport(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lab_reports')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='lab_reports', null=True, blank=True)
    report_date = models.DateField()
    report_type = models.CharField(max_length=100)
    results = models.TextField()
    comments = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='lab_reports/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.patient.user.get_full_name()} - {self.report_type} - {self.report_date}"