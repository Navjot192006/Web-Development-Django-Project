from django.shortcuts import render, redirect, get_object_or_404  # Import necessary functions
from django.contrib import messages  # Import messages for user feedback
from django.contrib.auth.models import User # Import User model
from django.contrib.auth import authenticate, login, logout # Import authentication functions
from django.contrib.auth.decorators import login_required  # Import login_required decorator
from django.contrib.auth.password_validation import validate_password # Import password validation
from django.core.exceptions import ValidationError # Import ValidationError for password validation
from .models import Donation, BloodDonation, BloodRequest, UserProfile, Doctor, Patient, Appointment, LabReport # Import your models
from django.http import HttpResponseForbidden # Import HttpResponseForbidden for permission checks
from functools import wraps # Import wraps for custom decorators
from django.db.models import Count # Import Count for aggregation
from django.db import models # Import models for aggregation
from django.utils import timezone # Import timezone for date handling
from datetime import datetime, date, timedelta # Import datetime for date handling
from django.urls import reverse # Import reverse for URL redirection

# Custom decorator for admin-only views
def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Login Successfully")
            return redirect('home')
    return wrapper

# Create your views here.

def home(request):
    return render(request, 'home.html')

def Register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        cpassword = request.POST.get('cpassword')

        if password != cpassword:
            messages.error(request, 'Passwords do not match')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already used')
        else:
            try:
                validate_password(password)
                user = User.objects.create_user(
                    username=username, email=email, password=password)
                messages.success(
                    request, 'Registration successful! You can now login.')
                return redirect('Login')
            except ValidationError as e:
                for error in e:
                    messages.error(request, error)
    return render(request, 'Register.html')  

def ResetPassword(request):
    return render(request, 'ResetPassword.html')

def Login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        selected_role = request.POST.get('role')


        user = authenticate(request, username=username, password=password)
        if user:
            # Determine if the role matches the actual user status
            if (selected_role == 'admin' and user.is_superuser) or (selected_role == 'user' and not user.is_superuser):
                login(request, user)
                return redirect('Dashboard')
            else:
                messages.error(request, "Invalid credentials: Role mismatch")
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'signin.html')

@login_required
def Logout(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')

@login_required
def Profile(request):
    user = request.user
    try:
        profile = user.userprofile # Access related UserProfile
    except UserProfile.DoesNotExist:
        # If profile doesn't exist for some reason, create it
        profile = UserProfile.objects.create(user=user)

    # Get blood donations made by this user (for history only)
    blood_donations = BloodDonation.objects.filter(email=user.email).order_by('-donation_date')
    
    # Get regular fund donations made by this user (for history only)
    donations = Donation.objects.filter(email=user.email).order_by('-date')
    
    # Get blood requests made by this user (for history only)
    blood_requests = BloodRequest.objects.filter(email=user.email).order_by('-created_at')
    
    # Get appointments for this user
    appointments = []
    try:
        if hasattr(user, 'patient'):
            patient = user.patient
            appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date')
    except:
        pass
    
    # Calculate stats based on actual blood donation history
    donation_count = blood_donations.count()
    lives_saved = donation_count // 4 + 1 
    points = donation_count * 50
    
    # Determine donor level based on points
    donor_level = "New Donor"
    if points > 500:
        donor_level = "Platinum Donor"
    elif points > 300:
        donor_level = "Gold Donor" 
    elif points > 100:
        donor_level = "Silver Donor"
    
    context = {
        'user': user,
        'profile': profile, # Pass the UserProfile object
        'blood_donations': blood_donations,
        'donations': donations,
        'blood_requests': blood_requests,
        'donation_count': donation_count,
        'lives_saved': lives_saved,
        'points': points,
        'donor_level': donor_level,
        'appointments': appointments,  # Add appointments to the context
    }
    
    return render(request, 'Profile.html', context)

def handle_donation(request):
    # Import Razorpay with better error handling
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        import razorpay
        import json
        from django.conf import settings
        from django.views.decorators.csrf import csrf_exempt
        from django.http import JsonResponse, HttpResponse
        
        # Initialize Razorpay client
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.set_app_details({"title" : "BloodDonation Portal"})
            razorpay_integration_available = True
        except (AttributeError, Exception) as e:
            logger.warning(f"Razorpay client initialization failed. Error: {str(e)}")
            razorpay_integration_available = False
    except ImportError as e:
        logger.error(f"Razorpay module not available. Make sure it's installed in your virtual environment. Error: {str(e)}")
        # Removed the error message that was shown to users
        razorpay_integration_available = False

    if request.method == 'POST':
        # Check if it's a simulated payment submission
        if request.POST.get('simulated_payment') == 'true':
            name = request.POST.get('name')
            email = request.POST.get('email')
            amount = request.POST.get('amount')
            payment = request.POST.get('payment')
            message = request.POST.get('message')

            # Save the donation to the database
            Donation.objects.create(
                name=name,
                email=email,
                amount=amount,
                payment_method=payment + " (simulated)",
                message=message
            )

            messages.success(request, 'Thank you for your donation! (Simulated payment successful)')
            return redirect('home')
            
        # Check if it's a payment verification callback
        elif request.POST.get('razorpay_payment_id'):
            payment_id = request.POST.get('razorpay_payment_id')
            order_id = request.POST.get('razorpay_order_id')
            signature = request.POST.get('razorpay_signature')

            # Get the stored donation details from session
            donation_data = request.session.get('donation_data', {})
            
            # Verify payment signature
            if razorpay_integration_available:
                params_dict = {
                    'razorpay_payment_id': payment_id,
                    'razorpay_order_id': order_id,
                    'razorpay_signature': signature
                }
                
                try:
                    client.utility.verify_payment_signature(params_dict)
                    payment_verified = True
                except Exception:
                    payment_verified = False
            else:
                # Simulate verification in case Razorpay is not available
                payment_verified = True
            
            if payment_verified:
                # Save the donation to the database
                Donation.objects.create(
                    name=donation_data.get('name'),
                    email=donation_data.get('email'),
                    amount=donation_data.get('amount'),
                    payment_method='razorpay',
                    message=donation_data.get('message')
                )
                
                # Clear the session data
                if 'donation_data' in request.session:
                    del request.session['donation_data']
                if 'razorpay_order_id' in request.session:
                    del request.session['razorpay_order_id']
                
                messages.success(request, 'Thank you for your donation! Your payment was successful.')
                return redirect('home')
            else:
                messages.error(request, 'Payment verification failed. Please try again or contact support.')
                return redirect('DonateFunds')
                
        # If it's a regular form submission
        else:
            name = request.POST.get('name')
            email = request.POST.get('email')
            amount = request.POST.get('amount')
            payment = request.POST.get('payment')
            message = request.POST.get('message')
            
            # Get payment specific details based on the payment method
            payment_details = {}
            
            if payment == 'credit_card':
                payment_details = {
                    'card_name': request.POST.get('card_name', ''),
                    'card_number': request.POST.get('card_number', ''),
                    'expiry_date': request.POST.get('expiry_date', ''),
                    'cvv': '***'  # For security, never store actual CVV
                }
            elif payment == 'upi':
                payment_details = {
                    'upi_id': request.POST.get('upi_id', '')
                }
            elif payment == 'bank_transfer':
                payment_details = {
                    'bank_name': request.POST.get('bank_name', '')
                }
            elif payment == 'paypal':
                payment_details = {
                    'paypal_email': request.POST.get('paypal_email', '')
                }
            elif payment == 'wallet':
                payment_details = {
                    'wallet_type': request.POST.get('wallet_type', ''),
                    'wallet_number': request.POST.get('wallet_number', '')
                }
            
            # Store all data in session for later use
            request.session['donation_data'] = {
                'name': name,
                'email': email,
                'amount': amount,
                'payment': payment,
                'message': message,
                'payment_details': payment_details
            }
            
            # Validate the payment details
            is_valid = True
            
            if payment == 'credit_card':
                # Basic validation
                if not payment_details['card_name'] or not payment_details['card_number'] or not payment_details['expiry_date']:
                    is_valid = False
                    messages.error(request, 'Please fill in all card details.')
            elif payment == 'upi':
                if not payment_details['upi_id']:
                    is_valid = False
                    messages.error(request, 'Please enter a valid UPI ID.')
            elif payment == 'bank_transfer':
                if not payment_details['bank_name']:
                    is_valid = False
                    messages.error(request, 'Please select a bank.')
            elif payment == 'paypal':
                if not payment_details['paypal_email']:
                    is_valid = False
                    messages.error(request, 'Please enter your PayPal email.')
            elif payment == 'wallet':
                if not payment_details['wallet_type'] or not payment_details['wallet_number']:
                    is_valid = False
                    messages.error(request, 'Please complete all wallet details.')
            
            if not is_valid:
                return render(request, 'DonateFunds.html')
            
            # For card, UPI, net banking payments - create Razorpay order
            if payment in ['credit_card', 'upi', 'bank_transfer', 'paypal', 'wallet']:
                if razorpay_integration_available:
                    try:
                        # Convert amount to paise (Razorpay requires amount in smallest currency unit)
                        amount_in_paise = int(float(amount) * 100)
                        
                        # Create Razorpay order
                        order_data = {
                            'amount': amount_in_paise,
                            'currency': 'INR',
                            'receipt': f'donation-{email}',
                            'notes': {
                                'name': name,
                                'email': email,
                                'payment_method': payment
                            }
                        }
                        order = client.order.create(data=order_data)
                        
                        # Store order ID in session
                        request.session['razorpay_order_id'] = order['id']
                        
                        context = {
                            'name': name,
                            'email': email,
                            'amount': amount,
                            'payment_method': payment,
                            'payment_details': payment_details,
                            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                            'razorpay_order_id': order['id'],
                            'amount_in_paise': amount_in_paise,
                            'currency': 'INR',
                            'callback_url': request.build_absolute_uri(),
                        }
                        
                        return render(request, 'RazorpayPayment.html', context)
                    except Exception as e:
                        logger.error(f"Error creating Razorpay order: {str(e)}")
                        # Removed error message and just silently fallback to simulated payment
                        
                        # Fallback to simulated payment
                        context = {
                            'name': name,
                            'email': email,
                            'amount': amount,
                            'payment_method': payment,
                            'payment_details': payment_details,
                            'message': message
                        }
                        return render(request, 'SimulatePayment.html', context)
                else:
                    # Handle case where Razorpay is not available - use simulated payment page
                    context = {
                        'name': name,
                        'email': email,
                        'amount': amount,
                        'payment_method': payment,
                        'payment_details': payment_details,
                        'message': message
                    }
                    return render(request, 'SimulatePayment.html', context)
                    
    # GET request - Display the donation form
    return render(request, 'DonateFunds.html')

@admin_required
@login_required
def Dashboard(request):
    # Fetch recent blood donations & fund donations (get a few more than needed for merging)
    recent_blood_donations_qs = BloodDonation.objects.order_by('-donation_date')[:10]
    recent_fund_donations_qs = Donation.objects.order_by('-date')[:10]
    
    # Fetch HealthConnect data
    # Import necessary models from HealthConnect - moved imports here to avoid circular imports
    try:
        from HealthConnect.models import AppointmentRequest, DoctorAppointment
        
        # Get recent appointment requests
        recent_appointment_requests = AppointmentRequest.objects.order_by('-request_timestamp')[:5]
        
        # Get recent doctor appointments
        recent_doctor_appointments = DoctorAppointment.objects.order_by('-created_at')[:5]
    except (ImportError, ModuleNotFoundError):
        # Handle the case where HealthConnect models aren't available
        recent_appointment_requests = []
        recent_doctor_appointments = []
    
    # --- Prepare Activity Feed --- 
    activity_list = []
    
    # Process blood donations
    for bd in recent_blood_donations_qs:
        # Combine date with min time and make timezone aware for sorting/naturaltime
        timestamp = timezone.make_aware(datetime.combine(bd.donation_date, datetime.min.time())) 
        activity_list.append({
            'type': 'blood',
            'item': bd,
            'timestamp': timestamp
        })
        
    # Process fund donations (assuming 'date' is a DateTimeField)
    for fd in recent_fund_donations_qs:
         # Ensure fund donation date is also timezone aware if it's not already
        timestamp = fd.date 
        if timezone.is_naive(timestamp):
             timestamp = timezone.make_aware(timestamp)
        activity_list.append({
            'type': 'fund',
            'item': fd,
            'timestamp': timestamp
        })
        
    # Add appointment requests to activity feed
    for ar in recent_appointment_requests:
        activity_list.append({
            'type': 'appointment_request',
            'item': ar,
            'timestamp': ar.request_timestamp
        })
        
    # Add doctor appointments to activity feed
    for da in recent_doctor_appointments:
        activity_list.append({
            'type': 'doctor_appointment',
            'item': da,
            'timestamp': da.created_at
        })
        
    # Sort activities by timestamp, newest first
    activity_list.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Get the latest 5 activities
    recent_activities = activity_list[:5]
    # --- End Activity Feed Preparation ---

    # Calculate blood stock levels
    blood_stock = BloodDonation.objects.values('blood_group').annotate(count=Count('id')).order_by('blood_group')
    
    # Convert to a dictionary for easier template access, handling potential None or empty strings
    blood_stock_dict = {}
    all_blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'] # Define all possible groups
    
    # Initialize all groups with 0 count
    for group in all_blood_groups:
        blood_stock_dict[group] = {'name': group, 'count': 0}
        
    # Populate counts from the query
    for item in blood_stock:
        group_name = item.get('blood_group')
        if group_name and group_name.strip() in blood_stock_dict: # Check if group is valid
            blood_stock_dict[group_name.strip()]['count'] = item.get('count', 0)
            
    # Fetch overall stats (optional, can be calculated more efficiently if needed)
    total_donors = BloodDonation.objects.values('email').distinct().count()
    total_blood_donations = BloodDonation.objects.count()
    total_funds = Donation.objects.aggregate(total=models.Sum('amount'))['total'] or 0
    # lives_saved calculation depends on your logic, e.g., total_blood_donations * 3
    lives_saved_approx = total_blood_donations * 3 

    context = {
        # Pass only the limited recent donations for the tables
        'recent_blood_donations': recent_blood_donations_qs[:5], 
        'recent_fund_donations': recent_fund_donations_qs[:5],
        'recent_appointment_requests': recent_appointment_requests,
        'recent_doctor_appointments': recent_doctor_appointments,
        'blood_stock': blood_stock_dict,
        'total_donors': total_donors,
        'total_blood_donations': total_blood_donations,
        'total_funds': total_funds,
        'lives_saved_approx': lives_saved_approx,
        'recent_activities': recent_activities, # Pass the combined & sorted activity list
    }
    return render(request, 'Dashboard.html', context)

def Services(request):
    # Define all blood types
    blood_types = {
        'a_pos': {'name': 'A+', 'count': 0},
        'a_neg': {'name': 'A-', 'count': 0},
        'b_pos': {'name': 'B+', 'count': 0},
        'b_neg': {'name': 'B-', 'count': 0},
        'ab_pos': {'name': 'AB+', 'count': 0},
        'ab_neg': {'name': 'AB-', 'count': 0},
        'o_pos': {'name': 'O+', 'count': 0},
        'o_neg': {'name': 'O-', 'count': 0}
    }
    
    # Map actual blood group values to our keys
    blood_group_map = {
        'A+': 'a_pos',
        'A-': 'a_neg',
        'B+': 'b_pos',
        'B-': 'b_neg',
        'AB+': 'ab_pos',
        'AB-': 'ab_neg',
        'O+': 'o_pos',
        'O-': 'o_neg'
    }
    
    # Count donations for each blood group
    donations = BloodDonation.objects.all()
    for donation in donations:
        # Clean up and standardize the blood group
        blood_group = donation.blood_group.strip().upper()
        if blood_group in blood_group_map:
            key = blood_group_map[blood_group]
            blood_types[key]['count'] += 1
    
    context = {
        'blood_types': blood_types
    }
    
    return render(request, 'Services.html', context)

@login_required
def BloodDonate(request):
    # Pre-fill blood group from query parameter if present
    prefilled_blood_group = request.GET.get('blood_group', None) 

    if request.method == 'POST':
        name = request.POST.get('name')
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        blood_group = request.POST.get('blood-group') # Note: name is 'blood-group' in form
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        address = request.POST.get('address')
        health_info = request.POST.get('health-info')
        donation_date = request.POST.get('donation-date')
        
        # Save the blood donation request to database
        BloodDonation.objects.create(
            name=name,
            age=age,
            gender=gender,
            blood_group=blood_group,
            contact=contact,
            email=email,
            address=address,
            health_info=health_info,
            donation_date=donation_date
        )
        
        messages.success(request, 'Your blood donation request has been submitted successfully!')
        return redirect('home')
        
    # Pass the prefilled group to the template for GET requests
    context = {
        'prefilled_blood_group': prefilled_blood_group
    }
    return render(request, 'BloodDonate.html', context)

def handle_blood_request(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        blood_group = request.POST.get('blood-group')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        hospital = request.POST.get('hospital')
        address = request.POST.get('address')
        urgency = request.POST.get('urgency')
        message = request.POST.get('message')
        
        # Save the blood request to database
        BloodRequest.objects.create(
            name=name,
            age=age,
            gender=gender,
            blood_group=blood_group,
            contact=contact,
            email=email,
            hospital=hospital,
            address=address,
            urgency=urgency,
            message=message
        )
        
        messages.success(request, 'Your blood request has been submitted successfully!')
        return redirect('home')
        
    return render(request, 'BloodRequest.html')

@login_required
def organize_event(request):
    return render(request, 'OrganizeEvent.html')

@login_required
def edit_profile(request):
    user = request.user
    try:
        profile = user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)

    if request.method == 'POST':
        # Get form data
        full_name = request.POST.get('full_name', '')
        email = request.POST.get('email')
        
        # Update User model fields
        if full_name:
            name_parts = full_name.split(' ', 1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        if email and email != user.email:
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                messages.error(request, 'Email already in use by another account.')
                # Stay on the edit page if email error
                context = {'user': user, 'profile': profile}
                return render(request, 'EditProfile.html', context)
            else:
                user.email = email
        
        user.save() # Save User model changes

        # Update UserProfile model fields
        profile.contact = request.POST.get('contact', profile.contact)
        profile.address = request.POST.get('address', profile.address)
        profile.blood_group = request.POST.get('blood_group', profile.blood_group)
        profile.gender = request.POST.get('gender', profile.gender)
        profile.date_of_birth = request.POST.get('dob', profile.date_of_birth) # Assuming form field name is 'dob'
        
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
            
        profile.save() # Save UserProfile model changes
        
        messages.success(request, 'Profile updated successfully')
        return redirect('Profile') # Redirect back to profile view
    
    # Pre-fill form data for GET request
    context = {
        'user': user,
        'profile': profile,
    }
    
    return render(request, 'EditProfile.html', context)

def health_screening(request):
    """View function for the health screening information page."""
    return render(request, 'HealthScreening.html')

def blood_alerts(request):
    """View function for the blood alerts signup page."""
    if request.method == 'POST':
        email = request.POST.get('email')
        blood_group = request.POST.get('blood_group')
        notification_method = request.POST.get('notification_method')
        
        # In a real application, you would save this information to a database
        # For now, we'll just show a success message
        messages.success(request, 'You have successfully signed up for blood alerts!')
        return redirect('Services')
        
    return render(request, 'BloodAlerts.html')

@login_required
def donor_dashboard(request):
    """View function for donor dashboard page."""
    # Get the current user
    user = request.user
    
    # Get blood donations made by this user
    blood_donations = BloodDonation.objects.filter(email=user.email).order_by('-donation_date')
    
    # Get regular donations made by this user
    donations = Donation.objects.filter(email=user.email).order_by('-date')
    
    # Calculate stats
    donation_count = blood_donations.count()
    lives_saved = donation_count // 4 + 1  # Approximation: each 4 donations save a life
    
    # Calculate points (50 points per donation)
    points = donation_count * 50
    
    # Determine donor level based on points
    donor_level = "New Donor"
    if points > 500:
        donor_level = "Platinum Donor"
    elif points > 300:
        donor_level = "Gold Donor" 
    elif points > 100:
        donor_level = "Silver Donor"
    
    # Calculate health metrics
    from datetime import date, timedelta
    
    last_donation = None
    days_since_donation = None
    eligible_to_donate = True
    days_until_eligible = 0
    
    if blood_donations.exists():
        last_donation = blood_donations.first()
        days_since_donation = (date.today() - last_donation.donation_date).days
        
        # Eligibility check (usually 56 days or 8 weeks between whole blood donations)
        if days_since_donation < 56:
            eligible_to_donate = False
            days_until_eligible = 56 - days_since_donation
    
    context = {
        'user': user,
        'blood_donations': blood_donations,
        'donations': donations,
        'donation_count': donation_count,
        'lives_saved': lives_saved,
        'points': points,
        'donor_level': donor_level,
        'last_donation': last_donation,
        'days_since_donation': days_since_donation,
        'eligible_to_donate': eligible_to_donate,
        'days_until_eligible': days_until_eligible
    }
    
    return render(request, 'DonorDashboard.html', context)

@admin_required
@login_required
def admin_edit_donor(request, donor_id):
    """Allows admin to view and edit a specific blood donor's details."""
    try:
        # Fetch the specific blood donation record using the ID
        # Note: We use BloodDonation as the primary source for donor details for editing
        donor = BloodDonation.objects.get(id=donor_id)
    except BloodDonation.DoesNotExist:
        messages.error(request, "Donor not found.")
        return redirect('Dashboard') # Redirect back to the admin dashboard

    # We might also need the associated User object if standard fields like username are involved
    # Assuming email is the link; handle cases where user might not exist
    try:
        user = User.objects.get(email=donor.email)
    except User.DoesNotExist:
        user = None # Handle case where no corresponding user exists

    if request.method == 'POST':
        # Get form data
        donor.name = request.POST.get('full_name', donor.name)
        new_email = request.POST.get('email', donor.email)
        donor.contact = request.POST.get('contact', donor.contact)
        donor.address = request.POST.get('address', donor.address)
        donor.blood_group = request.POST.get('blood_group', donor.blood_group)
        donor.gender = request.POST.get('gender', donor.gender)
        # Update age if provided
        try:
            donor.age = int(request.POST.get('age', donor.age))
        except (ValueError, TypeError):
            pass # Keep original age if input is invalid

        # Update health info if provided
        donor.health_info = request.POST.get('health_info', donor.health_info)
        
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            donor.profile_picture = request.FILES['profile_picture']
            
        # Update user email if it has changed and is unique
        if user and new_email != user.email:
            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                messages.error(request, 'Email already in use by another account.')
            else:
                user.email = new_email
                donor.email = new_email # Keep emails in sync
                user.save()
                donor.save() # Save donor record after potential user save
                messages.success(request, f"Donor '{donor.name}' profile updated successfully.")
        elif not user and new_email != donor.email: 
             # If user doesn't exist but email changes, just update donor email
             # Consider if a User should be created or if this scenario is allowed
             donor.email = new_email
             donor.save()
             messages.success(request, f"Donor '{donor.name}' profile updated successfully.")
        else:
            # If email hasn't changed, just save the donor object
            donor.save()
            messages.success(request, f"Donor '{donor.name}' profile updated successfully.")
        
        # Redirect back to the same edit page after saving
        return redirect('admin_edit_donor', donor_id=donor.id)

    # Prepare context for GET request (displaying the form)
    context = {
        'donor': donor,
        'user_profile': user # Pass user object if found
    }
    
    return render(request, 'admin_edit_donor.html', context)

def groupdonate(request):
    return render(request, 'groupdonate.html')

def education(request):
    return render(request, 'EducationPrograms.html')


def contact(request):
    """View function to display the contact page."""
    context = {}
    return render(request, 'contact.html', context)

def save_life(request):
    return render(request, 'savelife.html')

def health_benefits(request):
    return render(request, 'healthbenif.html')

def community(request): 
    return render(request, 'community.html')

def terms(request):
    return render(request, 'terms.html')

def privacy(request):
    return render(request, 'privacy.html')

@login_required
def check_donation_eligibility(request):
    """Checks if the user is eligible to donate based on last donation date."""
    user = request.user
    last_donation = BloodDonation.objects.filter(email=user.email).order_by('-donation_date').first()
    
    eligible = True
    days_since_donation = None
    days_until_eligible = 0
    
    if last_donation:
        days_since_donation = (date.today() - last_donation.donation_date).days
        if days_since_donation < 56:
            eligible = False
            days_until_eligible = 56 - days_since_donation
            
    # Get the intended blood group from the query parameter, if provided
    blood_group = request.GET.get('blood_group', None)
    
    if eligible:
        # Redirect to the actual donation form, passing blood group if present
        redirect_url = reverse('BloodDonate')
        if blood_group:
            redirect_url += f'?blood_group={blood_group}'
        return redirect(redirect_url)
    else:
        # Redirect to the not eligible page, passing remaining days
        request.session['days_until_eligible'] = days_until_eligible # Store in session
        return redirect('not_eligible')

@login_required
def not_eligible(request):
    """Displays the page explaining why the user is not eligible to donate yet."""
    # Get the remaining days from the session (set in check_donation_eligibility)
    days_until_eligible = request.session.get('days_until_eligible', 0)
    
    context = {
        'days_until_eligible': days_until_eligible
    }
    return render(request, 'NotEligible.html', context)

# Dashboard Views
@login_required
def doctor_dashboard(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "You don't have a doctor profile.")
        return redirect('dashboard')
    
    # Get upcoming appointments (confirmed, future date)
    today = timezone.now().date()
    upcoming_appointments = Appointment.objects.filter(
        doctor=doctor,
        status='confirmed',
        appointment_date__gte=today
    ).order_by('appointment_date', 'appointment_time')
    
    # Get pending appointments (need confirmation)
    pending_appointments = Appointment.objects.filter(
        doctor=doctor,
        status='pending'
    ).order_by('created_at')
    
    # Get past appointments
    past_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date__lt=today
    ).order_by('-appointment_date')
    
    context = {
        'doctor': doctor,
        'upcoming_appointments': upcoming_appointments,
        'pending_appointments': pending_appointments,
        'past_appointments': past_appointments,
    }
    
    return render(request, 'Donation/dashboard/doctor_dashboard.html', context)

@login_required
def patient_dashboard(request):
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        messages.error(request, "You don't have a patient profile.")
        return redirect('dashboard')
    
    # Get all patient appointments
    appointments = Appointment.objects.filter(
        patient=patient
    ).order_by('-appointment_date')
    
    # Get donation history
    donations = BloodDonation.objects.filter(
        email=request.user.email
    ).order_by('-donation_date')
    
    # Get blood requests
    blood_requests = BloodRequest.objects.filter(
        email=request.user.email
    ).order_by('-created_at')
    
    # Get lab reports
    lab_reports = LabReport.objects.filter(
        patient=patient
    ).order_by('-report_date')
    
    context = {
        'patient': patient,
        'appointments': appointments,
        'donations': donations,
        'blood_requests': blood_requests,
        'lab_reports': lab_reports,
    }
    
    return render(request, 'Donation/dashboard/patient_dashboard.html', context)

@login_required
def dashboard(request):
    # Determine user type based on related models
    is_doctor = hasattr(request.user, 'doctor')
    is_patient = hasattr(request.user, 'patient')
    is_admin = request.user.is_superuser
    
    # If accessing directly, render the redirect page
    context = {
        'is_doctor': is_doctor,
        'is_patient': is_patient,
        'is_admin': is_admin,
    }
    
    return render(request, 'Donation/dashboard/dashboard.html', context)

# Appointment Management Views
@login_required
def view_appointment_details(request, appointment_id):
    """View appointment details"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check if the logged-in user is related to this appointment
    if request.user == appointment.patient.user or request.user == appointment.doctor.user:
        return render(request, 'view_appointment.html', {'appointment': appointment})
    else:
        # User not authorized to view this appointment
        return redirect('dashboard')

@login_required
def request_appointment(request):
    """Patient requesting a new appointment"""
    if request.method == 'POST':
        # Process form submission
        # Implementation details for appointment creation
        pass
    else:
        # Display appointment request form
        doctors = Doctor.objects.all()
        return render(request, 'request_appointment.html', {'doctors': doctors})

@login_required
def confirm_appointment(request, appointment_id):
    """Doctor confirming an appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check if the logged-in user is the doctor for this appointment
    if request.user == appointment.doctor.user:
        appointment.status = 'Confirmed'
        appointment.save()
        # Could add notification to patient here
        return redirect('doctor_dashboard')
    else:
        # User not authorized to confirm this appointment
        return redirect('dashboard')

@login_required
def cancel_appointment(request, appointment_id):
    """Cancelling an appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check if the logged-in user is related to this appointment
    if request.user == appointment.patient.user or request.user == appointment.doctor.user:
        appointment.status = 'Cancelled'
        appointment.save()
        # Could add notification to other party here
        return redirect('dashboard')
    else:
        # User not authorized to cancel this appointment
        return redirect('dashboard')

@login_required
def complete_appointment(request, appointment_id):
    """Doctor marking an appointment as completed"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check if the logged-in user is the doctor for this appointment
    if request.user == appointment.doctor.user:
        appointment.status = 'Completed'
        appointment.save()
        # Could add notification to patient here
        return redirect('doctor_dashboard')
    else:
        # User not authorized to complete this appointment
        return redirect('dashboard')

# Blood Request Views
@login_required
def create_blood_request(request):
    """Patient creating a new blood request"""
    if request.method == 'POST':
        # Process form submission
        # Implementation details for blood request creation
        pass
    else:
        # Display blood request form
        return render(request, 'create_blood_request.html')

@login_required
def view_blood_request(request, request_id):
    """View blood request details"""
    blood_request = get_object_or_404(BloodRequest, id=request_id)
    
    # Check if the logged-in user is related to this request
    if request.user == blood_request.patient.user or request.user.is_staff:
        return render(request, 'view_blood_request.html', {'blood_request': blood_request})
    else:
        # User not authorized to view this request
        return redirect('dashboard')

# Donation Views
@login_required
def schedule_donation(request):
    """Patient scheduling a blood donation"""
    if request.method == 'POST':
        # Process form submission
        # Implementation details for donation scheduling
        pass
    else:
        # Display donation scheduling form
        return render(request, 'schedule_donation.html')

@login_required
def view_donation_details(request, donation_id):
    """View donation details"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    # Check if the logged-in user is related to this donation
    if request.user == donation.donor.user or request.user.is_staff:
        return render(request, 'view_donation.html', {'donation': donation})
    else:
        # User not authorized to view this donation
        return redirect('dashboard')

# Lab Report Views
@login_required
def view_lab_report(request, report_id):
    """View lab report details"""
    lab_report = get_object_or_404(LabReport, id=report_id)
    
    # Check if the logged-in user is related to this report
    if request.user == lab_report.patient.user or request.user == lab_report.doctor.user:
        return render(request, 'view_lab_report.html', {'lab_report': lab_report})
    else:
        # User not authorized to view this report
        return redirect('dashboard')

@login_required
def record_blood_donation(request):
    """View for users to record their blood donation history."""
    if request.method == 'POST':
        donation_date = request.POST.get('donation_date')
        blood_group = request.POST.get('blood_group')
        amount = request.POST.get('amount', 450)  # Default 450ml (one unit)
        center_name = request.POST.get('center_name')
        
        # Basic validation
        if not donation_date or not blood_group or not center_name:
            messages.error(request, 'Please fill all required fields.')
            return redirect('record_blood_donation')
        
        # Calculate age from date of birth if available
        age = 0
        if hasattr(request.user, 'userprofile') and request.user.userprofile.date_of_birth:
            today = timezone.now().date()
            born = request.user.userprofile.date_of_birth
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        
        # Create the blood donation record
        BloodDonation.objects.create(
            name=request.user.get_full_name() or request.user.username,
            age=age,
            gender=request.user.userprofile.gender if hasattr(request.user, 'userprofile') else 'Unknown',
            blood_group=blood_group,
            contact=request.user.userprofile.contact if hasattr(request.user, 'userprofile') else '',
            email=request.user.email,
            address=request.user.userprofile.address if hasattr(request.user, 'userprofile') else '',
            health_info='Donated at ' + center_name,
            donation_date=donation_date
        )
        
        messages.success(request, 'Your blood donation has been recorded successfully!')
        return redirect('DonorDashboard')
    
    # For GET request, show the form
    return render(request, 'RecordBloodDonation.html')

# Add this function to handle making an appointment with a doctor
@login_required
def request_doctor_appointment(request):
    """View for users to request an appointment with a doctor."""
    if request.method == 'POST':
        preferred_date = request.POST.get('preferred_date')
        preferred_time = request.POST.get('preferred_time')
        doctor_id = request.POST.get('doctor_id')
        appointment_type = request.POST.get('appointment_type')
        reason = request.POST.get('reason')
        
        # Basic validation
        if not preferred_date or not preferred_time or not appointment_type:
            messages.error(request, 'Please fill all required fields.')
            return redirect('request_doctor_appointment')
        
        try:
            # Check if user has userprofile
            user_profile = None
            if hasattr(request.user, 'userprofile'):
                user_profile = request.user.userprofile
            
            # Create Patient object if it doesn't exist
            patient, created = Patient.objects.get_or_create(
                user=request.user,
                defaults={
                    'blood_group': user_profile.blood_group if user_profile else None,
                    'date_of_birth': user_profile.date_of_birth if user_profile else None,
                    'gender': user_profile.gender if user_profile else None,
                    'phone_number': user_profile.contact if user_profile else None,
                    'address': user_profile.address if user_profile else None
                }
            )
            
            # Get doctor if specified
            doctor = None
            if doctor_id:
                doctor = Doctor.objects.get(id=doctor_id)
            
            # Create appointment
            Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                appointment_date=preferred_date,
                appointment_time=preferred_time,
                reason=reason or f"{appointment_type} appointment",
                status='pending'
            )
            
            messages.success(request, 'Your appointment request has been submitted successfully!')
            return redirect('DonorDashboard')
            
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('request_doctor_appointment')
    
    # For GET request, show the form with available doctors
    doctors = Doctor.objects.all()
    return render(request, 'RequestDoctorAppointment.html', {'doctors': doctors})

