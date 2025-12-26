from rest_framework import viewsets, status, generics, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import logout
from django.db import transaction
from datetime import datetime, time
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from .models import (
    User, PatientProfile, DoctorProfile, MedicalDocument,
    Appointment, MedicalRecord
)
from .serializers import (
    UserSerializer, PatientProfileSerializer, DoctorProfileSerializer,
    RegisterPatientSerializer, LoginSerializer, PatientDashboardSerializer,
    MedicalDocumentSerializer, RegisterDoctorSerializer,
    AppointmentSerializer, CreateAppointmentSerializer,
    MedicalRecordSerializer
)
from .permissions import IsAgentOrSuperAdmin


# ✅ Auth
class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'], url_path='register/patient')
    def register_patient(self, request):
        serializer = RegisterPatientSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    patient_profile = serializer.save()
                    token, created = Token.objects.get_or_create(user=patient_profile.user)

                    return Response({
                        'token': token.key,
                        'user': UserSerializer(patient_profile.user).data,
                        'patient_profile': PatientProfileSerializer(patient_profile).data,
                        'message': 'Inscription réussie'
                    }, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='register/doctor')
    def register_doctor(self, request):
        serializer = RegisterDoctorSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    doctor_profile = serializer.save()
                    token, created = Token.objects.get_or_create(user=doctor_profile.user)

                    return Response({
                        'token': token.key,
                        'user': UserSerializer(doctor_profile.user).data,
                        'doctor_profile': DoctorProfileSerializer(doctor_profile).data,
                        'message': 'Inscription médecin réussie'
                    }, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='login')
    def user_login(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)

            response_data = {
                'token': token.key,
                'user': UserSerializer(user).data,
                'message': 'Connexion réussie'
            }

            if user.is_patient():
                try:
                    patient_profile = PatientProfile.objects.get(user=user)
                    response_data['patient_profile'] = PatientProfileSerializer(patient_profile).data
                except PatientProfile.DoesNotExist:
                    pass

            if user.is_doctor():
                try:
                    doctor_profile = DoctorProfile.objects.get(user=user)
                    response_data['doctor_profile'] = DoctorProfileSerializer(doctor_profile).data
                except DoctorProfile.DoesNotExist:
                    pass

            return Response(response_data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        Token.objects.filter(user=request.user).delete()
        logout(request)
        return Response({'message': 'Déconnexion réussie'}, status=status.HTTP_200_OK)


# ✅ Admin Users
class UserAdminViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAgentOrSuperAdmin]


# ✅ Patient ViewSet
class PatientViewSet(viewsets.ModelViewSet):
    queryset = PatientProfile.objects.all()
    serializer_class = PatientProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_patient():
            return PatientProfile.objects.filter(user=user)
        return PatientProfile.objects.all()

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return super().get_permissions()


# ✅ Dashboard patient
class PatientDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_patient():
            return Response({"error": "Accès réservé aux patients."}, status=status.HTTP_403_FORBIDDEN)

        serializer = PatientDashboardSerializer(user)
        return Response(serializer.data)


# ✅ Patient profile
class PatientProfileView(APIView):
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


# ✅ Doctor ViewSet
class DoctorViewSet(viewsets.ModelViewSet):
    queryset = DoctorProfile.objects.all()
    serializer_class = DoctorProfileSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
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

    @action(detail=False, methods=['get'])
    def my_patients(self, request):
        user = request.user
        if not user.is_doctor():
            return Response({"error": "Accès réservé aux médecins"}, status=status.HTTP_403_FORBIDDEN)

        doctor = user.doctorprofile
        patient_ids = Appointment.objects.filter(doctor=doctor).values_list('patient', flat=True).distinct()
        patients = PatientProfile.objects.filter(id__in=patient_ids)

        serializer = PatientProfileSerializer(patients, many=True)
        return Response(serializer.data)


# ✅ Doctor Dashboard
class DoctorDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_doctor():
            return Response({"error": "Accès réservé aux médecins"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            doctor = user.doctorprofile
        except DoctorProfile.DoesNotExist:
             return Response({"error": "Profil médecin introuvable"}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        today = now.date()

        # Stats
        patients_seen_count = Appointment.objects.filter(doctor=doctor).values('patient').distinct().count()
        upcoming_appointments_count = Appointment.objects.filter(
            doctor=doctor, 
            status__in=['PENDING', 'CONFIRMED'], 
            date__gte=now
        ).count()
        unread_messages_count = 0 # Placeholder

        # Today's Appointments
        today_appts_qs = Appointment.objects.filter(
            doctor=doctor, 
            date__date=today
        ).select_related('patient__user').order_by('date')
        
        today_appointments = []
        for appt in today_appts_qs:
            today_appointments.append({
                "id": appt.id,
                "doctor_name": appt.patient.user.get_full_name(), # Mapped to Patient Name for frontend reuse
                "specialty": appt.reason or "Consultation",       # Mapped to Type/Reason
                "date": appt.date.isoformat(),
                "status": appt.status
            })

        # Notifications (Generated from recent activity)
        # On prend les 5 derniers RDV modifiés ou créés
        recent_appts = Appointment.objects.filter(doctor=doctor).order_by('-id')[:5]
        recent_notifications = []
        
        for appt in recent_appts:
            notif_title = "Mise à jour RDV"
            notif_msg = f"RDV avec {appt.patient.user.get_full_name()}"
            notif_type = "INFO"
            
            if appt.status == 'PENDING':
                notif_title = "Nouveau RDV"
                notif_msg = f"Demande de {appt.patient.user.get_full_name()}"
            elif appt.status == 'CANCELLED':
                notif_title = "RDV Annulé"
                notif_type = "WARNING"
            elif appt.status == 'REFUSED':
                notif_title = "RDV Refusé"
                notif_type = "WARNING"
            elif appt.status == 'CONFIRMED':
                notif_title = "RDV Confirmé"
                notif_type = "SUCCESS"

            recent_notifications.append({
                "id": appt.id,
                "title": notif_title,
                "message": notif_msg,
                "date": appt.date.isoformat(),
                "type": notif_type
            })

        data = {
            "doctor_profile": {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "specialty": doctor.speciality.name if doctor.speciality else "Généraliste"
            },
            "patients_seen_count": patients_seen_count,
            "upcoming_appointments_count": upcoming_appointments_count,
            "unread_messages_count": unread_messages_count,
            "today_appointments": today_appointments,
            "recent_notifications": recent_notifications
        }
        
        return Response(data)


# ✅ Pagination
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# ✅ Appointment ViewSet (corrigé)
class AppointmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

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
            raise serializers.ValidationError("Seuls les patients peuvent prendre rendez-vous.")

    @action(detail=False, methods=['get'], url_path='doctor/my')
    def my_appointments(self, request):
        user = request.user
        if not user.is_doctor():
            return Response({"error": "Accès réservé aux médecins"}, status=status.HTTP_403_FORBIDDEN)

        doctor = user.doctorprofile
        queryset = Appointment.objects.filter(doctor=doctor).order_by("date")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AppointmentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AppointmentSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='confirm')
    def confirm(self, request, pk=None):
        appointment = self.get_object()
        user = request.user

        if not user.is_doctor() or appointment.doctor.user != user:
            return Response({"error": "Action non autorisée"}, status=status.HTTP_403_FORBIDDEN)

        if appointment.status != "PENDING":
            return Response({"error": f"RDV pas confirmable, statut = {appointment.status}"},
                            status=status.HTTP_400_BAD_REQUEST)

        if appointment.date < timezone.now():
            return Response({"error": "RDV déjà passé"}, status=status.HTTP_400_BAD_REQUEST)

        appointment.status = "CONFIRMED"
        appointment.save()
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=True, methods=['patch'], url_path='refuse')
    def refuse(self, request, pk=None):
        appointment = self.get_object()
        user = request.user

        if not user.is_doctor() or appointment.doctor.user != user:
            return Response({"error": "Action non autorisée"}, status=status.HTTP_403_FORBIDDEN)

        if appointment.status != "PENDING":
            return Response({"error": f"RDV pas refusé, statut = {appointment.status}"},
                            status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get("reason")
        if not reason:
            return Response({"error": "La raison est obligatoire"}, status=status.HTTP_400_BAD_REQUEST)

        appointment.status = "REFUSED"
        if hasattr(appointment, "notes_doctor"):
            appointment.notes_doctor = reason
        appointment.save()

        return Response(AppointmentSerializer(appointment).data)

    @action(detail=True, methods=['patch'], url_path='cancel')
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        user = request.user

        if not user.is_doctor() or appointment.doctor.user != user:
            return Response({"error": "Action non autorisée"}, status=status.HTTP_403_FORBIDDEN)

        if appointment.status != "CONFIRMED":
            return Response({"error": f"RDV pas annulable, statut = {appointment.status}"},
                            status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get("reason", "")

        appointment.status = "CANCELLED"
        if reason and hasattr(appointment, "notes_doctor"):
            appointment.notes_doctor = reason
        appointment.save()

        return Response(AppointmentSerializer(appointment).data)


# ✅ MedicalDocument
class MedicalDocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MedicalDocumentSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = MedicalDocument.objects.all()

        patient_id = self.request.query_params.get('patient')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        if user.is_patient():
            return queryset.filter(patient__user=user)
        elif user.is_doctor():
            return queryset.filter(doctor__user=user)
        return MedicalDocument.objects.none()


# ✅ MedicalRecord
class MedicalRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MedicalRecordSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = MedicalRecord.objects.all()

        patient_id = self.request.query_params.get('patient')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        if user.is_patient():
            return queryset.filter(patient__user=user)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_doctor():
            raise serializers.ValidationError("Seuls les médecins peuvent créer des dossiers médicaux.")
        serializer.save(doctor=user.doctorprofile)


# ✅ dossier médical complet patient
class PatientMedicalRecordView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_patient():
            return Response({"error": "Accès réservé aux patients"}, status=status.HTTP_403_FORBIDDEN)

        try:
            profile = user.patientprofile
        except PatientProfile.DoesNotExist:
            return Response({"error": "Profil patient introuvable"}, status=status.HTTP_404_NOT_FOUND)

        patient_info = {
            "full_name": user.get_full_name(),
            "blood_type": profile.blood_type,
            "allergies": profile.allergies,
            "height": profile.height,
            "weight": profile.weight,
            "emergency_contact": profile.emergency_contact,
            "emergency_phone": profile.emergency_phone,
        }

        records = MedicalRecord.objects.filter(patient=profile).select_related('doctor', 'doctor__user').order_by('-record_date')

        consultations = []
        for record in records:
            doctor_name = record.doctor.user.get_full_name() if record.doctor else "Inconnu"
            consultations.append({
                "id": record.id,
                "doctor_name": doctor_name,
                "date": record.record_date.isoformat(),
                "reason": record.title,
                "notes_patient": record.description or ""
            })

        documents_qs = MedicalDocument.objects.filter(patient=profile).select_related('doctor', 'doctor__user').order_by('-created_at')
        documents_data = MedicalDocumentSerializer(documents_qs, many=True, context={'request': request}).data

        return Response({
            "patient_info": patient_info,
            "consultations": consultations,
            "documents": documents_data
        })
