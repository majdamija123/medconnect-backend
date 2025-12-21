from django.utils import timezone
from datetime import timedelta, datetime, date, time
from .models import Appointment, AvailabilitySlot, Holiday

class AppointmentValidationService:
    @staticmethod
    def get_available_slots(doctor, target_date):
        """
        Retourne une liste de créneaux (datetime) disponibles pour une date donnée.
        """
        # 1. Vérifier si c'est un jour férié/absence
        if Holiday.objects.filter(doctor=doctor, date=target_date).exists():
            return []

        # 2. Récupérer les plages de disponibilité pour ce jour de la semaine
        weekday = target_date.weekday()  # 0=Monday
        slots_config = AvailabilitySlot.objects.filter(doctor=doctor, day_of_week=weekday)
        
        available_slots = []
        
        # 3. Récupérer les RDV existants pour ce jour
        appointments = Appointment.objects.filter(
            doctor=doctor,
            date__date=target_date,
            status__in=['PENDING', 'CONFIRMED']
        )
        
        # 4. Générer les créneaux
        for config in slots_config:
            current_time = datetime.combine(target_date, config.start_time)
            end_time = datetime.combine(target_date, config.end_time)
            
            # Rendre le datetime conscient (timezone aware)
            current_time = timezone.make_aware(current_time)
            end_time = timezone.make_aware(end_time)
            
            while current_time + timedelta(minutes=30) <= end_time:
                slot_start = current_time
                slot_end = current_time + timedelta(minutes=30)
                
                # Vérifier collision
                is_taken = False
                for appt in appointments:
                    appt_start = appt.date
                    appt_end = appt.date + timedelta(minutes=appt.duration)
                    
                    # Logique de chevauchement
                    if slot_start < appt_end and slot_end > appt_start:
                        is_taken = True
                        break
                
                if not is_taken:
                    # Vérifier si c'est dans le futur
                    if slot_start > timezone.now():
                        available_slots.append(slot_start)
                
                current_time += timedelta(minutes=30)
                
        # Trier par heure
        available_slots.sort()
        return available_slots

    @staticmethod
    def is_slot_available(doctor, start_time, duration=30, exclude_appointment_id=None):

        target_date = start_time.date()
        weekday = target_date.weekday()
        current_time_time = start_time.time()
        
        # Check Working Hours
        # Note: This checks if START time is within a slot. Ideally check full duration fit.
        starts_in_slot = AvailabilitySlot.objects.filter(
            doctor=doctor, 
            day_of_week=weekday,
            start_time__lte=current_time_time,
            end_time__gt=current_time_time # Strict gt because if end=start, it's 0 duration
        ).exists()
        
        if not starts_in_slot:
            return False

        # Check existing appointments overlap ... (existing logic)
        end_time = start_time + timedelta(minutes=duration)
        query = Appointment.objects.filter(
            doctor=doctor,
            date__date=target_date, # Optimization to filter by day first
            status__in=['PENDING', 'CONFIRMED']
        )
        potential_overlaps = query.exclude(id=exclude_appointment_id) if exclude_appointment_id else query
        
        for appt in potential_overlaps:
            appt_end = appt.date + timedelta(minutes=appt.duration)
            # Overlap:
            if start_time < appt_end and end_time > appt.date:
                return False
                
        return True

    @staticmethod
    def validate_appointment_retention(start_time):
        if start_time < timezone.now():
            return False, "Le rendez-vous ne peut pas être dans le passé."
        return True, None

