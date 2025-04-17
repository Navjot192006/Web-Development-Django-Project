from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import DoctorAppointment, AppointmentRequest, Doctor, TimeSlot
from datetime import datetime, date # To parse the date
import re # For parsing doctor string

# Create your views here.

# View for the main booking page (showing doctors)
@login_required
def book_appointment_home(request):
    # Get all doctors by default
    doctors = Doctor.objects.all()
    
    # Handle search and filters if the form is submitted
    if request.method == 'POST':
        # Get search term
        search_term = request.POST.get('search_term', '').strip()
        
        # Get specialties
        specialties = request.POST.getlist('specialty')
        
        # Get appointment date
        appointment_date_str = request.POST.get('appointment_date')
        if appointment_date_str:
            try:
                appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
            except ValueError:
                appointment_date = None
        else:
            appointment_date = None
            
        # Get appointment type
        appointment_type = request.POST.get('appointment_type')
        
        # Get health concerns
        health_concerns = request.POST.getlist('concern')
        
        # Apply filters
        if search_term:
            doctors = doctors.filter(
                Q(name__icontains=search_term) | Q(specialty__icontains=search_term)
            )
            
        if specialties:
            doctors = doctors.filter(specialty__in=specialties)
            
        # For other filters like appointment date, type, and health concerns,
        # you would need additional logic depending on your data model
        # For example, if doctors have available_dates or appointment_types fields
        
    # Prepare context
    context = {
        'doctors': doctors,
        'today': date.today().strftime('%Y-%m-%d')
    }
    
    return render(request, 'BookAppointment.html', context)

# View for the form to request a different time / book a specific slot
@login_required
def appointment_form_view(request):
    if request.method == 'POST':
        # Data submitted from the booking form
        try:
            doctor_name = request.POST.get('doctor_name')
            specialty = request.POST.get('specialty')
            # We need the date the appointment is for, not just today's date.
            # This should come from the form or the link that led here.
            # For now, using the hidden input added previously:
            appointment_date_str = request.POST.get('appointment_date') # Get date as string

            # Convert date string to date object - Adjust format if needed
            # The format depends on how it's passed. Assuming MM/DD/YYYY from previous example
            try:
                appointment_date_obj = datetime.strptime(appointment_date_str, '%m/%d/%Y').date()
            except (ValueError, TypeError):
                # Fallback or error handling if date isn't passed or format is wrong
                messages.error(request, "Invalid or missing appointment date.")
                # Consider redirecting back with error or using a default
                return redirect('health:book_appointment_home') # Redirect home for now

            selected_time = request.POST.get('selected_time_slot')
            reason = request.POST.get('reason_for_visit', '') # Optional field

            # Basic validation
            if not all([doctor_name, specialty, selected_time, appointment_date_obj]):
                messages.error(request, "Missing required appointment details (Doctor, Specialty, Date, or Time).")
                return redirect('health:book_appointment_home')

            # Create and save the appointment
            appointment = DoctorAppointment.objects.create(
                patient=request.user,
                doctor_name=doctor_name,
                specialty=specialty,
                appointment_date=appointment_date_obj,
                appointment_time=selected_time,
                reason_for_visit=reason,
                status='Confirmed' # Assuming direct booking confirms it
                # Add appointment_type if needed based on form
            )
            # No need to call appointment.save() when using create()

            messages.success(request, f"Appointment with {doctor_name} on {appointment_date_obj.strftime('%m/%d/%Y')} at {selected_time} booked successfully!")
            # Redirect to a success page, user profile, or dashboard
            return redirect('health:book_appointment_home') # Redirect home for now

        except Exception as e:
            messages.error(request, f"An error occurred while booking: {e}")
            # Log the error e for debugging
            return redirect('health:book_appointment_home') # Redirect home on error

    else: # GET request
        # Display the form, potentially pre-filled from GET parameters
        doctor_name = request.GET.get('doctor', 'Doctor Name Not Provided')
        specialty = request.GET.get('specialty', 'Specialty Not Provided')
        # TODO: Get the ACTUAL date from the previous page (e.g., DayAvailability or BookAppointment)
        # For now, using today as placeholder like before
        appointment_date_display = datetime.now().strftime('%m/%d/%Y') # Example date
        example_time_slots = ["9:00 AM", "10:30 AM", "12:00 PM", "2:00 PM", "3:30 PM", "5:00 PM"] # Match template examples

        context = {
            'doctor_name': doctor_name,
            'specialty': specialty,
            'appointment_date': appointment_date_display, # Pass date for display and hidden input
            'time_slots': example_time_slots # Pass example time slots
        }
        return render(request, 'appointment_form.html', context)

# Placeholder views for other URLs if needed
@login_required
def schedule_info_view(request):
    if request.method == 'POST':
        try:
            # Extract data from POST request
            appointment_type = request.POST.get('appointmentType')
            appointment_date_str = request.POST.get('appointmentDate')
            appointment_time_24hr = request.POST.get('appointmentTime') # e.g., "08:00"
            doctor_selection = request.POST.get('doctor', '') # Optional, default to empty string
            reason = request.POST.get('reason')

            # --- Data Validation and Processing ---
            if not all([appointment_type, appointment_date_str, appointment_time_24hr, reason]):
                 messages.error(request, "Please fill in all required fields.")
                 # Get doctors for the form
                 doctors = Doctor.objects.all()
                 return render(request, 'ScheduleInfo.html', {'doctors': doctors}) # Re-render form

            # Convert date
            try:
                appointment_date_obj = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, "Invalid date format.")
                # Get doctors for the form
                doctors = Doctor.objects.all()
                return render(request, 'ScheduleInfo.html', {'doctors': doctors})

            # Convert time (e.g., "08:00" to "8:00 AM")
            try:
                time_obj = datetime.strptime(appointment_time_24hr, '%H:%M')
                preferred_time_display = time_obj.strftime("%I:%M %p").lstrip('0') # Format as 8:00 AM
            except ValueError:
                 preferred_time_display = appointment_time_24hr # Use raw value if format fails

            # Process doctor selection (use raw value, can be empty)
            selected_doctor_str = doctor_selection if doctor_selection else "Any available doctor"

            # --- Create AppointmentRequest ---
            appointment_request = AppointmentRequest.objects.create(
                requested_by=request.user,
                preferred_date=appointment_date_obj,
                preferred_time=preferred_time_display,
                appointment_type=appointment_type,
                selected_doctor=selected_doctor_str,
                reason=reason,
                # status defaults to 'Pending' as defined in the model
            )

            messages.success(request, f"Appointment request for {appointment_date_obj.strftime('%m/%d/%Y')} around {preferred_time_display} submitted successfully! We will contact you to confirm.")
            return redirect('health:book_appointment_home') # Redirect after successful request

        except Exception as e:
            messages.error(request, f"An error occurred while submitting your request: {e}")
            # Log the error e for debugging
            # Get doctors for the form
            doctors = Doctor.objects.all()
            return render(request, 'ScheduleInfo.html', {'doctors': doctors}) # Re-render form on error

    else: # GET request
        # Just display the empty form with doctors list
        doctors = Doctor.objects.all()
        return render(request, 'ScheduleInfo.html', {'doctors': doctors})

def day_availability_view(request):
    # Logic for DayAvailability page GET request
    # Need POST handling or revised logic based on user interaction
    return render(request, 'DayAvailability.html', {})

def about(request):
    return render(request, 'About1.html')

def services(request):
    return render(request, 'services1.html')

def appointment_scheduling(request):
    return render(request, 'AppointmentScheduling.html')

def schedule_appointment_info(request):
    """Renders the detailed appointment scheduling information page."""
    return render(request, 'ScheduleInfo.html')

@login_required
def my_appointment_requests(request):
    """Displays the user's appointment requests."""
    appointment_requests = AppointmentRequest.objects.filter(requested_by=request.user).order_by('-request_timestamp')
    context = {
        'appointment_requests': appointment_requests,
    }
    return render(request, 'my_appointment_requests.html', context)