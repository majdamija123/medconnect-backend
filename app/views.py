from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, permission_classes, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from datetime import datetime

from .models import User, PatientProfile, DoctorProfile, MedicalDocument, Appointment
from .serializers import (
    UserSerializer, PatientProfileSerializer, DoctorProfileSerializer,
    RegisterPatientSerializer, LoginSerializer, PatientDashboardSerializer,
    MedicalDocumentSerializer, AggregatedMedicalRecordSerializer,
    AppointmentSerializer
)
from .permissions import IsAgentOrSuperAdmin

# Vues d'authentification
class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'], url_path='register/patient')
    def register_patient(self, request):
        """Inscription d'un nouveau patient"""
        serializer = RegisterPatientSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    patient_profile = serializer.save()
                    
                    # Créer un token pour l'utilisateur
                    token, created = Token.objects.get_or_create(user=patient_profile.user)
                    
                    # Préparer la réponse
                    response_data = {
                        'token': token.key,
                        'user': UserSerializer(patient_profile.user).data,
                        'patient_profile': PatientProfileSerializer(patient_profile).data,
                        'message': 'Inscription réussie'
                    }
                    
                    return Response(response_data, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                return Response(
                    {'error': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], url_path='login')
    def user_login(self, request):
        """Connexion d'un utilisateur"""
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Créer ou récupérer le token
            token, created = Token.objects.get_or_create(user=user)
            
            # Préparer la réponse selon le rôle
            response_data = {
                'token': token.key,
                'user': UserSerializer(user).data,
                'message': 'Connexion réussie'
            }
            
            # Ajouter les données spécifiques au rôle
            if user.is_patient():
                try:
                    patient_profile = PatientProfile.objects.get(user=user)
                    response_data['patient_profile'] = PatientProfileSerializer(patient_profile).data
                except PatientProfile.DoesNotExist:
                    pass
            elif user.is_doctor():
                try:
                    doctor_profile = DoctorProfile.objects.get(user=user)
                    response_data['doctor_profile'] = DoctorProfileSerializer(doctor_profile).data
                except DoctorProfile.DoesNotExist:
                    pass
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """Déconnexion de l'utilisateur"""
        try:
            # Supprimer le token
            Token.objects.filter(user=request.user).delete()
            logout(request)
            return Response({'message': 'Déconnexion réussie'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Vue pour la gestion des utilisateurs (admin)
class UserAdminViewSet(viewsets.ModelViewSet):
    """
    CRUD utilisateur accessible uniquement aux agents / superadmins.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAgentOrSuperAdmin]

# Vue pour les patients
class PatientViewSet(viewsets.ModelViewSet):
    """
    CRUD pour les profils patients.
    """
    queryset = PatientProfile.objects.all()
    serializer_class = PatientProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Les patients ne voient que leur propre profil
        # Les agents et admins voient tous les patients
        user = self.request.user
        if user.is_patient():
            return PatientProfile.objects.filter(user=user)
        return PatientProfile.objects.all()
    
    def get_permissions(self):
        # Autoriser l'inscription sans authentification
        if self.action == 'create':
            return [AllowAny()]
        return super().get_permissions()

from rest_framework.views import APIView

class PatientDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Vérifier si l'utilisateur est un patient
        if not user.is_patient():
            return Response(
                {"error": "Accès réservé aux patients."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = PatientDashboardSerializer(user)
        return Response(serializer.data)

class PatientProfileView(APIView):
    """
    Vue pour récupérer et modifier le profil du patient connecté.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        if not user.is_patient():
            return Response({"error": "Accès réservé aux patients."}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            profile = user.patientprofile
        except PatientProfile.DoesNotExist:
            return Response({"error": "Profil introuvable."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = PatientProfileSerializer(profile)
        return Response(serializer.data)
        
    def put(self, request):
        user = request.user
        if not user.is_patient():
            return Response({"error": "Accès réservé aux patients."}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            profile = user.patientprofile
        except PatientProfile.DoesNotExist:
            return Response({"error": "Profil introuvable."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = PatientProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DoctorViewSet(viewsets.ModelViewSet):
    queryset = DoctorProfile.objects.all()
    serializer_class = DoctorProfileSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """
        Retourne les créneaux disponibles pour une date donnée.
        Query param: date (YYYY-MM-DD)
        """
        doctor = self.get_object()
        date_str = request.query_params.get('date')
        
        if not date_str:
            return Response({"error": "Date param required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format"}, status=status.HTTP_400_BAD_REQUEST)
            
        from .services import AppointmentValidationService
        slots = AppointmentValidationService.get_available_slots(doctor, target_date)
        
        return Response({
            "doctor": doctor.user.get_full_name(),
            "date": str(target_date),
            "slots": [slot.strftime("%H:%M") for slot in slots]
        })

from .serializers import AppointmentSerializer, CreateAppointmentSerializer
from .models import Appointment

class AppointmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateAppointmentSerializer
        return AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_patient():
            return Appointment.objects.filter(patient__user=user)
        elif user.is_doctor():
            return Appointment.objects.filter(doctor__user=user)
        return Appointment.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_patient():
            serializer.save(patient=user.patientprofile)
        else:
            # Pour l'instant on empêche les médecins de créer des RDV pour eux-mêmes via cette API
            # ou on pourrait implémenter une logique différente
            raise serializers.ValidationError("Seuls les patients peuvent prendre rendez-vous pour le moment.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Utiliser le serializer de lecture pour la réponse
        read_serializer = AppointmentSerializer(serializer.instance)
        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class MedicalDocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MedicalDocumentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_patient():
            return MedicalDocument.objects.filter(patient__user=user)
        elif user.is_doctor():
            return MedicalDocument.objects.filter(doctor__user=user)
        return MedicalDocument.objects.none()

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            # Requirement: patient cannot modify/delete
            # You might want to allow doctors to modify their own issued documents
            # For now, let's stick to the simplest restriction
            return [IsAuthenticated()]
        return super().get_permissions()

    def check_permissions(self, request):
        super().check_permissions(request)
        if self.action in ['update', 'partial_update', 'destroy'] and request.user.is_patient():
            self.permission_denied(request, message="Les patients ne peuvent pas modifier ou supprimer des documents.")

    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        user = request.user
        
        # Validation file size (10MB)
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "Aucun fichier fourni"}, status=status.HTTP_400_BAD_REQUEST)
        
        if file_obj.size > 10 * 1024 * 1024:
            return Response({"error": "Fichier trop volumineux (max 10MB)"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validation extension
        ext = file_obj.name.split('.')[-1].lower()
        if ext not in ['pdf', 'jpg', 'jpeg', 'png']:
            return Response({"error": "Type de fichier non supporté (PDF, JPG, PNG uniquement)"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            if user.is_patient():
                serializer.save(
                    patient=user.patientprofile,
                    uploaded_by=MedicalDocument.UploadedBy.PATIENT
                )
            elif user.is_doctor():
                # If doctor, need to provide patient ID
                patient_id = request.data.get('patient')
                if not patient_id:
                    return Response({"error": "ID du patient requis pour l'upload par un médecin"}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    patient = PatientProfile.objects.get(id=patient_id)
                except PatientProfile.DoesNotExist:
                    return Response({"error": "Patient non trouvé"}, status=status.HTTP_404_NOT_FOUND)
                
                serializer.save(
                    patient=patient,
                    doctor=user.doctorprofile,
                    uploaded_by=MedicalDocument.UploadedBy.DOCTOR
                )
            else:
                return Response({"error": "Action non autorisée"}, status=status.HTTP_403_FORBIDDEN)
                
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MedicalRecordAggregatedViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user
        if not user.is_patient():
            return Response({"error": "Seuls les patients peuvent consulter leur dossier médical."}, status=403)
        
        try:
            profile = user.patientprofile
            serializer = AggregatedMedicalRecordSerializer(profile, context={'request': request})
            return Response(serializer.data)
        except PatientProfile.DoesNotExist:
            return Response({"error": "Profil patient introuvable."}, status=404)
