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

# Modèle pour les rendez-vous
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('CONFIRMED', 'Confirmé'),
        ('CANCELLED', 'Annulé'),
        ('COMPLETED', 'Terminé'),
    ]

    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='appointments')
    date = models.DateTimeField()
    duration = models.IntegerField(default=30, help_text="Durée en minutes")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reason = models.TextField(blank=True, null=True)
    notes_patient = models.TextField(blank=True, null=True, help_text="Notes visibles par le patient")
    notes_doctor = models.TextField(blank=True, null=True, help_text="Notes privées du médecin")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"RDV {self.patient.user.get_full_name()} avec {self.doctor.user.get_full_name()} le {self.date}"

# Modèle pour les notifications
class Notification(models.Model):
    TYPE_CHOICES = [
        ('INFO', 'Information'),
        ('WARNING', 'Avertissement'),
        ('SUCCESS', 'Succès'),
        ('ERROR', 'Erreur'),
        ('APPOINTMENT', 'Rendez-vous'),
        ('MESSAGE', 'Message'),
        ('DOCUMENT', 'Document'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    date = models.DateTimeField(default=timezone.now)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='INFO')
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.title} - {self.user.username}"

# Modèle pour les créneaux de disponibilité
class AvailabilitySlot(models.Model):
    DAYS_OF_WEEK = [
        (0, 'Lundi'), (1, 'Mardi'), (2, 'Mercredi'), 
        (3, 'Jeudi'), (4, 'Vendredi'), (5, 'Samedi'), (6, 'Dimanche'),
    ]

    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='availability_slots')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_recurring = models.BooleanField(default=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.doctor} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"

# Modèle pour les jours fériés / Absences
class Holiday(models.Model):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='holidays')
    date = models.DateField()
    reason = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        ordering = ['date']
        unique_together = ('doctor', 'date')

    def __str__(self):
        return f"Absence {self.doctor} le {self.date}"
