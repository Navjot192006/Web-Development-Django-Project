from django.contrib import admin
from .models import Donation, BloodDonation, BloodRequest

# Register your models here.

class DonationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'amount', 'payment_method', 'date')  # Fields to display in the admin list view
    search_fields = ('name', 'email')  # Enable search by name and email
    list_filter = ('payment_method', 'date')  # Add filters for payment method and date

# Register the Donation model with the custom admin class
admin.site.register(Donation, DonationAdmin)

class BloodDonationAdmin(admin.ModelAdmin):
    list_display = ('name', 'blood_group', 'age', 'gender', 'contact', 'donation_date')
    search_fields = ('name', 'email', 'blood_group')
    list_filter = ('blood_group', 'gender', 'donation_date')
    
admin.site.register(BloodDonation, BloodDonationAdmin)

class BloodRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'blood_group', 'urgency', 'hospital', 'contact', 'created_at')
    search_fields = ('name', 'email', 'blood_group', 'hospital')
    list_filter = ('blood_group', 'urgency', 'created_at')
    
admin.site.register(BloodRequest, BloodRequestAdmin)

    