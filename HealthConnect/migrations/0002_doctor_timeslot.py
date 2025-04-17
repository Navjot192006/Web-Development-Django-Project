# Generated by Django 5.2 on 2025-04-15 18:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('HealthConnect', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Doctor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('specialty', models.CharField(choices=[('Cardiology', 'Cardiology'), ('Dermatology', 'Dermatology'), ('Endocrinology', 'Endocrinology'), ('Gastroenterology', 'Gastroenterology'), ('Neurology', 'Neurology'), ('Orthopedics', 'Orthopedics'), ('Pediatrics', 'Pediatrics'), ('Psychiatry', 'Psychiatry'), ('Cardiac Electrophysiology', 'Cardiac Electrophysiology'), ('Preventive Cardiology', 'Preventive Cardiology')], max_length=100)),
                ('bio', models.TextField()),
                ('experience_years', models.IntegerField(default=0)),
                ('rating', models.DecimalField(decimal_places=1, default=4.0, max_digits=3)),
                ('reviews_count', models.IntegerField(default=0)),
                ('clinic_name', models.CharField(max_length=200)),
                ('clinic_address', models.CharField(max_length=255)),
                ('profile_image', models.URLField(default='https://images.unsplash.com/photo-1559839734-2b71ea197ec2?ixlib=rb-1.2.1&auto=format&fit=crop&w=634&q=80')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='TimeSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('time', models.CharField(max_length=10)),
                ('is_available', models.BooleanField(default=True)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='time_slots', to='HealthConnect.doctor')),
            ],
            options={
                'ordering': ['date', 'time'],
                'unique_together': {('doctor', 'date', 'time')},
            },
        ),
    ]
