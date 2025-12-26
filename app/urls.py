from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuthViewSet, UserAdminViewSet, PatientViewSet, AppointmentViewSet,
    PatientDashboardView, DoctorViewSet, PatientProfileView, MedicalDocumentViewSet,
    MedicalRecordViewSet, PatientMedicalRecordView, DoctorDashboardAPIView,
)

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'users', UserAdminViewSet, basename='user')
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'patient/documents', MedicalDocumentViewSet, basename='patient-documents')
router.register(r'medical-records', MedicalRecordViewSet, basename='medical-record')

urlpatterns = [
    # ✅ ROUTES API UNIQUEMENT
    path('api/', include(router.urls)),

    # ✅ Routes APIView patient
    path('api/patient/dashboard/', PatientDashboardView.as_view(), name='patient-dashboard'),
    path('api/patient/profile/', PatientProfileView.as_view(), name='patient-profile'),
    path('api/patient/medical-record/', PatientMedicalRecordView.as_view(), name='patient-medical-record'),

    # ✅ Route Dashboard Médecin
    path('api/doctor/dashboard/', DoctorDashboardAPIView.as_view(), name='doctor-dashboard'),

    # Auth DRF Browsable API
    path('api-auth/', include('rest_framework.urls')),
]

# ✅ Routes manuelles confirm/refuse/cancel (fix 404)
appointment_confirm = AppointmentViewSet.as_view({'patch': 'confirm'})
appointment_refuse = AppointmentViewSet.as_view({'patch': 'refuse'})
appointment_cancel = AppointmentViewSet.as_view({'patch': 'cancel'})

urlpatterns += [
    path('api/appointments/<int:pk>/confirm/', appointment_confirm, name='appointment-confirm'),
    path('api/appointments/<int:pk>/refuse/', appointment_refuse, name='appointment-refuse'),
    path('api/appointments/<int:pk>/cancel/', appointment_cancel, name='appointment-cancel'),
]
