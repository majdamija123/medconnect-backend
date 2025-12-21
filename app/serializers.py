from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, PatientProfile, DoctorProfile, Appointment, Notification
from django.utils import timezone

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", 
                 "phone", "role", "password", "is_active", "date_of_birth", "address"]
        extra_kwargs = {
            'password': {'write_only': True},
            'is_active': {'read_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

class PatientProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = PatientProfile
        fields = ['id', 'user', 'blood_type', 'allergies', 
                 'emergency_contact', 'emergency_phone', 'height', 'weight']
        read_only_fields = ['id']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        password = user_data.pop('password', None)
        
        # Créer l'utilisateur
        user = User.objects.create(**user_data)
        if password:
            user.set_password(password)
            user.save()
        
        # Créer le profil patient
        patient_profile = PatientProfile.objects.create(user=user, **validated_data)
        return patient_profile

class DoctorProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    speciality_name = serializers.CharField(source='speciality.name', read_only=True)

    class Meta:
        model = DoctorProfile
        fields = ['id', 'user', 'speciality', 'speciality_name', 'license_number', 
                 'years_of_experience', 'consultation_fee', 
                 'is_available', 'bio']
        read_only_fields = ['id']

# Serializers pour l'authentification
class RegisterPatientSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    blood_type = serializers.CharField(max_length=10, required=False, allow_blank=True)
    allergies = serializers.CharField(required=False, allow_blank=True)
    emergency_contact = serializers.CharField(max_length=100, required=False, allow_blank=True)
    emergency_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return value

    def create(self, validated_data):
        # Extraire les données du patient
        blood_type = validated_data.pop('blood_type', '')
        allergies = validated_data.pop('allergies', '')
        emergency_contact = validated_data.pop('emergency_contact', '')
        emergency_phone = validated_data.pop('emergency_phone', '')
        
        # Créer l'utilisateur
        password = validated_data.pop('password')
        user = User.objects.create(
            **validated_data,
            role=User.Roles.PATIENT,
            is_active=True
        )
        user.set_password(password)
        user.save()
        
        # Créer le profil patient
        patient_profile = PatientProfile.objects.create(
            user=user,
            blood_type=blood_type or None,
            allergies=allergies or None,
            emergency_contact=emergency_contact or None,
            emergency_phone=emergency_phone or None
        )
        
        return patient_profile

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        # Trouver l'utilisateur par email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Identifiants incorrects.")
        
        # Vérifier le mot de passe
        if not user.check_password(password):
            raise serializers.ValidationError("Identifiants incorrects.")
        
        # Vérifier si l'utilisateur est actif
        if not user.is_active:
            raise serializers.ValidationError("Ce compte est désactivé.")
        
        data['user'] = user
        return data

class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    specialty = serializers.CharField(source='doctor.speciality.name', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'doctor', 'patient', 'doctor_name', 'patient_name', 
            'specialty', 'date', 'duration', 'status', 'reason', 
            'notes_patient', 'created_at'
        ]
        read_only_fields = ['id', 'doctor', 'patient', 'status', 'created_at', 'notes_patient']

class CreateAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['doctor', 'date', 'reason']

    def validate(self, data):
        from .services import AppointmentValidationService
        
        doctor = data['doctor']
        date = data['date']
        
        # Validation 1: Date dans le futur
        is_valid_time, message = AppointmentValidationService.validate_appointment_retention(date)
        if not is_valid_time:
            raise serializers.ValidationError(message)

        # Validation 2: Disponibilité (chevauchement)
        if not AppointmentValidationService.is_slot_available(doctor, date):
            raise serializers.ValidationError("Ce créneau n'est pas disponible.")
            
        return data

    def create(self, validated_data):
        # Le patient est ajouté dans la vue via perform_create
        return super().create(validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'date', 'type']

class PatientDashboardSerializer(serializers.Serializer):
    user_info = serializers.SerializerMethodField()
    patient_profile = serializers.SerializerMethodField()
    next_appointment = serializers.SerializerMethodField()
    unread_messages_count = serializers.IntegerField(default=0) # Placeholder logic
    new_documents_count = serializers.IntegerField(default=0)   # Placeholder logic
    recent_notifications = serializers.SerializerMethodField()

    def get_user_info(self, obj):
        # obj is the user instance
        return {
            "first_name": obj.first_name,
            "last_name": obj.last_name,
            "email": obj.email,
            "phone": obj.phone
        }

    def get_patient_profile(self, obj):
        try:
            profile = obj.patientprofile
            return {
                "blood_type": profile.blood_type,
                "allergies": profile.allergies,
                "emergency_contact": profile.emergency_contact,
                "emergency_phone": profile.emergency_phone
            }
        except PatientProfile.DoesNotExist:
            return None

    def get_next_appointment(self, obj):
        try:
            profile = obj.patientprofile
            next_appt = Appointment.objects.filter(
                patient=profile, 
                date__gte=timezone.now(),
                status__in=['PENDING', 'CONFIRMED']
            ).order_by('date').first()
            if next_appt:
                return AppointmentSerializer(next_appt).data
            return None
        except PatientProfile.DoesNotExist:
            return None

    def get_recent_notifications(self, obj):
        notifications = Notification.objects.filter(user=obj).order_by('-date')[:5]
        return NotificationSerializer(notifications, many=True).data
