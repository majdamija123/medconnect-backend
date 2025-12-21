from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet, UserAdminViewSet, PatientViewSet, AppointmentViewSet, PatientDashboardView, DoctorViewSet

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'users', UserAdminViewSet, basename='user')
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'appointments', AppointmentViewSet, basename='appointment')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/patient/dashboard/', PatientDashboardView.as_view(), name='patient-dashboard'),
    path('api-auth/', include('rest_framework.urls')),
]