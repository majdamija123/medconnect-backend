from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Roles(models.TextChoices):
        PATIENT = "PATIENT", "Patient"
        DOCTOR = "DOCTOR", "Médecin"
        AGENT = "AGENT", "Agent administratif"
        SUPERADMIN = "SUPERADMIN", "Super administrateur"
    
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.PATIENT)
    
    def __str__(self):
        return self.username