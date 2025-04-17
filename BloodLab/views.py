from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import BloodTest, TestAppointment, SelectedTest
from Donation.models import Patient
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime, timedelta
import uuid

def labtest_home(request):
    # Add logic later to fetch doctors, specialties etc.
    context = {}
    return render(request, 'LabTests.html', context)

def blood_test_form_view(request):
    # If we need to load some initial data
    blood_tests = get_or_create_test_data()
    
    # Get all tests grouped by category for the form
    tests_by_category = {}
    for test in blood_tests:
        if test.category not in tests_by_category:
            tests_by_category[test.category] = []
        tests_by_category[test.category].append(test)
    
    context = {
        'tests_by_category': tests_by_category
    }
    
    return render(request, 'TestForm.html', context)

@csrf_exempt
def submit_appointment(request):
    if request.method == 'POST':
        try:
            # Handle form submission data instead of JSON
            # Get all data from POST dictionary
            post_data = request.POST
            
            # Validate required fields
            required_fields = ['firstName', 'lastName', 'email', 'phone', 'dob', 
                              'gender', 'address', 'city', 'state', 'zipCode', 
                              'appointmentDate', 'appointmentTime', 'selectedTests']
            
            for field in required_fields:
                if field not in post_data or not post_data[field]:
                    messages.error(request, f'Field {field} is required')
                    return redirect('bloodlab:test_form')
            
            # Handle date and time
            try:
                appointment_date = datetime.strptime(post_data['appointmentDate'], '%Y-%m-%d').date()
                appointment_time = datetime.strptime(post_data['appointmentTime'], '%H:%M').time()
                date_of_birth = datetime.strptime(post_data['dob'], '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Invalid date or time format')
                return redirect('bloodlab:test_form')
            
            # Create appointment
            appointment = TestAppointment(
                first_name=post_data['firstName'],
                last_name=post_data['lastName'],
                email=post_data['email'],
                phone=post_data['phone'],
                date_of_birth=date_of_birth,
                gender=post_data['gender'],
                address=post_data['address'],
                city=post_data['city'],
                state=post_data['state'],
                zip_code=post_data['zipCode'],
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                insurance_provider=post_data.get('insurance', ''),
                notes=post_data.get('notes', '')
            )
            
            # Try to link to existing patient if user is logged in
            if request.user.is_authenticated:
                try:
                    patient = Patient.objects.get(user=request.user)
                    appointment.patient = patient
                except Patient.DoesNotExist:
                    pass  # Continue without linking
            
            appointment.save()
            
            # Add selected tests - tests come as comma-separated string
            total_price = 0
            selected_tests = post_data['selectedTests'].split(',')
            for test_code in selected_tests:
                try:
                    test = BloodTest.objects.get(test_code=test_code)
                    SelectedTest.objects.create(
                        appointment=appointment,
                        test=test
                    )
                    total_price += float(test.price)
                except BloodTest.DoesNotExist:
                    # Log this but continue with valid tests
                    pass
            
            # Update total price
            appointment.total_price = total_price
            appointment.save()
            
            # Store appointment ID in session to display on confirmation page
            request.session['appointment_id'] = appointment.appointment_id
            
            # Redirect to a confirmation page instead of returning JSON
            return redirect('bloodlab:appointment_confirmation')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('bloodlab:test_form')
    
    return redirect('bloodlab:test_form')

def appointment_confirmation(request):
    """Display appointment confirmation page"""
    appointment_id = request.session.get('appointment_id')
    
    if not appointment_id:
        messages.error(request, 'No appointment information found')
        return redirect('bloodlab:test_form')
    
    try:
        appointment = TestAppointment.objects.get(appointment_id=appointment_id)
        selected_tests = appointment.selected_tests.all()
        
        context = {
            'appointment': appointment,
            'selected_tests': selected_tests
        }
        return render(request, 'appointment_confirmation.html', context)
    except TestAppointment.DoesNotExist:
        messages.error(request, 'Appointment not found')
        return redirect('bloodlab:test_form')

def get_available_slots(request):
    """Get available time slots for a specific date"""
    date_str = request.GET.get('date')
    
    try:
        requested_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid date format'}, status=400)
    
    # Get all booked slots for this date
    booked_slots = TestAppointment.objects.filter(
        appointment_date=requested_date,
        status__in=['pending', 'confirmed']
    ).values_list('appointment_time', flat=True)
    
    # Generate all possible slots from 8:00 to 16:30 in 30-minute increments
    all_slots = []
    current_time = datetime.strptime('08:00', '%H:%M').time()
    end_time = datetime.strptime('16:30', '%H:%M').time()
    
    while current_time <= end_time:
        slot = current_time.strftime('%H:%M')
        is_available = current_time not in booked_slots
        all_slots.append({
            'time': slot,
            'available': is_available
        })
        
        # Add 30 minutes
        dt = datetime.combine(datetime.today(), current_time) + timedelta(minutes=30)
        current_time = dt.time()
    
    return JsonResponse({
        'success': True,
        'slots': all_slots
    })

def InsuranceVerification(request):
    return render(request, 'InsuranceVerification.html')

def test_about(request):
    context = {}
    return render(request, 'TestAbout.html', context)

def test_prices(request):
    blood_tests = get_or_create_test_data()
    context = {
        'tests': blood_tests
    }
    return render(request, 'TestPricing.html', context)

def get_or_create_test_data():
    """Initialize test data if none exists"""
    if BloodTest.objects.count() == 0:
        # Create test data for different categories
        test_data = [
            # General Health
            {'name': 'Complete Blood Count', 'category': 'general', 'price': 49, 
             'description': 'Measures your overall health and detects a wide range of disorders.', 
             'test_code': 'cbc'},
            {'name': 'Basic Metabolic Panel', 'category': 'general', 'price': 59, 
             'description': 'Provides information about your body\'s metabolism.', 
             'test_code': 'metabolic'},
            {'name': 'Liver Function Panel', 'category': 'general', 'price': 65, 
             'description': 'Evaluates how well your liver is working.', 
             'test_code': 'liver'},
             
            # Hormones
            {'name': 'Thyroid Panel', 'category': 'hormones', 'price': 89, 
             'description': 'Evaluates how well your thyroid is working.', 
             'test_code': 'thyroid_panel'},
            {'name': 'Testosterone Test', 'category': 'hormones', 'price': 79, 
             'description': 'Measures testosterone levels in your blood.', 
             'test_code': 'testosterone'},
             
            # Vitamins & Nutrition
            {'name': 'Vitamin D Test', 'category': 'vitamins', 'price': 69, 
             'description': 'Measures vitamin D levels in your blood.', 
             'test_code': 'vitamin_d'},
            {'name': 'B Vitamins Panel', 'category': 'vitamins', 'price': 99, 
             'description': 'Comprehensive assessment of B vitamin levels.', 
             'test_code': 'b_vitamins'},
            {'name': 'Iron Panel', 'category': 'vitamins', 'price': 75, 
             'description': 'Evaluates iron levels and iron-binding capacity.', 
             'test_code': 'iron_panel'},
             
            # Cardiac Risk
            {'name': 'Lipid Panel', 'category': 'cardiac', 'price': 55, 
             'description': 'Measures cholesterol and triglycerides in your blood.', 
             'test_code': 'lipid_panel'},
            {'name': 'Cardiac Markers', 'category': 'cardiac', 'price': 119, 
             'description': 'Tests for indicators of heart damage or stress.', 
             'test_code': 'cardiac_markers'},
             
            # Diabetes
            {'name': 'Fasting Glucose', 'category': 'diabetes', 'price': 35, 
             'description': 'Measures blood sugar levels after an overnight fast.', 
             'test_code': 'glucose'},
            {'name': 'Hemoglobin A1C', 'category': 'diabetes', 'price': 49, 
             'description': 'Measures average blood sugar levels over past 3 months.', 
             'test_code': 'a1c'},
             
            # Thyroid
            {'name': 'TSH Test', 'category': 'thyroid', 'price': 45, 
             'description': 'Measures thyroid-stimulating hormone levels.', 
             'test_code': 'tsh'},
            {'name': 'Free T4 Test', 'category': 'thyroid', 'price': 55, 
             'description': 'Measures free thyroxine hormone levels.', 
             'test_code': 'free_t4'},
             
            # Allergy
            {'name': 'Food Allergy Panel', 'category': 'allergy', 'price': 199, 
             'description': 'Tests for allergies to common food allergens.', 
             'test_code': 'food_allergy'},
            {'name': 'Environmental Allergy Panel', 'category': 'allergy', 'price': 179, 
             'description': 'Tests for allergies to environmental factors.', 
             'test_code': 'environmental_allergy'},
             
            # Immunity
            {'name': 'Immune System Panel', 'category': 'immunity', 'price': 149, 
             'description': 'Comprehensive assessment of immune system function.', 
             'test_code': 'immune_panel'},
            {'name': 'CRP Test', 'category': 'immunity', 'price': 59, 
             'description': 'Measures C-reactive protein, a marker of inflammation.', 
             'test_code': 'crp'},
        ]
        
        for test_info in test_data:
            BloodTest.objects.create(
                name=test_info['name'],
                category=test_info['category'],
                price=test_info['price'],
                description=test_info['description'],
                test_code=test_info['test_code']
            )
    
    return BloodTest.objects.all()