from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Speciality, DoctorProfile, PatientProfile, MedicalRecord

# ==============================================
# ADMIN POUR LE MODÈLE USER PERSONNALISÉ
# ==============================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Interface d'administration pour le modèle User personnalisé."""
    
    # Configuration des champs dans le formulaire d'édition
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Informations personnelles"), {
            "fields": ("first_name", "last_name", "email", "phone", "role", 
                      "date_of_birth", "address")
        }),
        (_("Permissions"), {
            "fields": ("is_active", "is_staff", "is_superuser", 
                      "groups", "user_permissions"),
        }),
        (_("Dates importantes"), {"fields": ("last_login", "date_joined")}),
    )
    
    # Configuration des champs dans le formulaire d'ajout
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", 
                      "phone", "role", "is_staff", "is_active"),
        }),
    )
    
    # Configuration de la liste principale
    list_display = ("username", "email", "first_name", "last_name", 
                   "phone", "role", "is_staff", "is_active", "date_joined")
    
    # Filtres disponibles
    list_filter = ("role", "is_staff", "is_superuser", "is_active", "date_joined")
    
    # Champs de recherche
    search_fields = ("username", "email", "first_name", "last_name", "phone")
    
    # Tri par défaut
    ordering = ("-date_joined",)
    
    # Actions personnalisées
    actions = ['activate_users', 'deactivate_users', 'make_agents', 'make_patients']
    
    def activate_users(self, request, queryset):
        """Activer les utilisateurs sélectionnés."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} utilisateur(s) activé(s).")
    activate_users.short_description = _("Activer les utilisateurs sélectionnés")
    
    def deactivate_users(self, request, queryset):
        """Désactiver les utilisateurs sélectionnés."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} utilisateur(s) désactivé(s).")
    deactivate_users.short_description = _("Désactiver les utilisateurs sélectionnés")
    
    def make_agents(self, request, queryset):
        """Transformer les utilisateurs en agents administratifs."""
        updated = queryset.update(role=User.Roles.AGENT)
        self.message_user(request, f"{updated} utilisateur(s) transformé(s) en agents.")
    make_agents.short_description = _("Définir comme agents administratifs")
    
    def make_patients(self, request, queryset):
        """Transformer les utilisateurs en patients."""
        updated = queryset.update(role=User.Roles.PATIENT)
        self.message_user(request, f"{updated} utilisateur(s) transformé(s) en patients.")
    make_patients.short_description = _("Définir comme patients")

# ==============================================
# ADMINS POUR LES MODÈLES MÉTIERS
# ==============================================

@admin.register(Speciality)
class SpecialityAdmin(admin.ModelAdmin):
    """Administration des spécialités médicales."""
    
    list_display = ('name', 'doctor_count', 'description')
    search_fields = ('name', 'description')
    list_per_page = 20
    
    def doctor_count(self, obj):
        """Nombre de médecins dans cette spécialité."""
        return obj.doctorprofile_set.count()
    doctor_count.short_description = _("Nombre de médecins")

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    """Administration des profils médecins."""
    
    list_display = ('get_full_name', 'speciality', 'license_number', 
                   'is_available', 'consultation_fee', 'years_of_experience')
    list_filter = ('speciality', 'is_available', 'years_of_experience')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 
                    'license_number', 'speciality__name')
    raw_id_fields = ('user', 'speciality')
    list_per_page = 20
    list_editable = ('is_available', 'consultation_fee')
    
    def get_full_name(self, obj):
        """Affiche le nom complet du médecin."""
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = _("Médecin")
    get_full_name.admin_order_field = 'user__last_name'

@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    """Administration des profils patients."""
    
    list_display = ('get_full_name', 'blood_type', 'emergency_contact', 
                   'emergency_phone', 'medical_record_count')
    list_filter = ('blood_type',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 
                    'emergency_contact', 'emergency_phone')
    raw_id_fields = ('user',)
    list_per_page = 20
    
    def get_full_name(self, obj):
        """Affiche le nom complet du patient."""
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = _("Patient")
    get_full_name.admin_order_field = 'user__last_name'
    
    def medical_record_count(self, obj):
        """Nombre de dossiers médicaux du patient."""
        return obj.medical_records.count()
    medical_record_count.short_description = _("Dossiers médicaux")

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    """Administration des dossiers médicaux."""
    
    list_display = ('title', 'patient_name', 'doctor_name', 'record_date', 
                   'created_at', 'updated_at')
    list_filter = ('record_date', 'doctor', 'created_at')
    search_fields = ('title', 'description', 'diagnosis', 'treatment',
                    'patient__user__username', 'patient__user__first_name',
                    'doctor__user__username', 'doctor__user__first_name')
    date_hierarchy = 'record_date'
    raw_id_fields = ('patient', 'doctor')
    list_per_page = 30
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('title', 'patient', 'doctor')
        }),
        (_('Contenu médical'), {
            'fields': ('description', 'diagnosis', 'treatment'),
            'classes': ('wide',)
        }),
        (_('Dates'), {
            'fields': ('record_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def patient_name(self, obj):
        """Affiche le nom du patient."""
        return obj.patient.user.get_full_name()
    patient_name.short_description = _("Patient")
    patient_name.admin_order_field = 'patient__user__last_name'
    
    def doctor_name(self, obj):
        """Affiche le nom du médecin."""
        return obj.doctor.user.get_full_name() if obj.doctor else "-"
    doctor_name.short_description = _("Médecin")
    doctor_name.admin_order_field = 'doctor__user__last_name'

# ==============================================
# PERSONNALISATION DE L'INTERFACE ADMIN GLOBALE
# ==============================================

# Titre de l'admin
admin.site.site_header = _("Administration MedConnect")
admin.site.site_title = _("Portail d'administration MedConnect")
admin.site.index_title = _("Gestion de la plateforme médicale")