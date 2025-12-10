from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    class Roles(models.TextChoices):
        PATIENT = "PATIENT", "Patient"
        DOCTOR = "DOCTOR", "Médecin"
        AGENT = "AGENT", "Agent administratif"
        SUPERADMIN = "SUPERADMIN", "Super administrateur"
    
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.PATIENT)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_patient(self):
        return self.role == self.Roles.PATIENT
    
    def is_doctor(self):
        return self.role == self.Roles.DOCTOR
    
    def is_agent(self):
        return self.role == self.Roles.AGENT
    
    def is_superadmin(self):
        return self.role == self.Roles.SUPERADMIN

# Modèle pour les spécialités médicales
class Speciality(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

# Modèle pour les médecins (extension de User)
class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'role': User.Roles.DOCTOR})
    speciality = models.ForeignKey(Speciality, on_delete=models.SET_NULL, null=True, blank=True)
    license_number = models.CharField(max_length=50, unique=True)
    years_of_experience = models.IntegerField(default=0)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    bio = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.speciality}"

# Modèle pour les patients (extension de User)
class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'role': User.Roles.PATIENT})
    blood_type = models.CharField(max_length=10, blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=100, blank=True, null=True)
    emergency_phone = models.CharField(max_length=20, blank=True, null=True)
    
    def __str__(self):
        return f"Patient: {self.user.get_full_name()}"

# Modèle pour les dossiers médicaux
class MedicalRecord(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    diagnosis = models.TextField(blank=True, null=True)
    treatment = models.TextField(blank=True, null=True)
    record_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-record_date']
    
    def __str__(self):
        return f"{self.title} - {self.patient.user.get_full_name()}"