from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
import random
from datetime import datetime, timedelta
from Donation.models import BloodDonation, UserProfile

class Command(BaseCommand):
    help = 'Generates fake data for testing'

    def handle(self, *args, **kwargs):
        fake = Faker()
        
        # List of blood groups
        blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        
        # Generate 20 fake users
        for i in range(20):
            # Create user
            username = fake.user_name()
            email = fake.email()
            password = 'testpass123'  # Same password for all test users
            
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                continue
                
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=fake.first_name(),
                last_name=fake.last_name()
            )
            
            # Update user profile (it's already created by the signal)
            profile = UserProfile.objects.get(user=user)
            profile.contact = fake.phone_number()
            profile.address = fake.address()
            profile.blood_group = random.choice(blood_groups)
            profile.gender = random.choice(['M', 'F'])
            profile.date_of_birth = fake.date_of_birth(minimum_age=18, maximum_age=65)
            profile.save()
            
            # Create some blood donations for the user
            for _ in range(random.randint(0, 5)):
                donation_date = fake.date_between(start_date='-5y', end_date='today')
                BloodDonation.objects.create(
                    name=f"{user.first_name} {user.last_name}",
                    age=random.randint(18, 65),
                    gender=profile.gender,
                    blood_group=profile.blood_group,
                    contact=profile.contact,
                    email=user.email,
                    address=profile.address,
                    health_info=fake.text(max_nb_chars=200),
                    donation_date=donation_date
                )
            
            self.stdout.write(self.style.SUCCESS(f'Created user: {username}'))
        
        self.stdout.write(self.style.SUCCESS('Successfully generated fake data')) 