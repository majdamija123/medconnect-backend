# app/permissions.py
from rest_framework import permissions

class IsAgentOrSuperAdmin(permissions.BasePermission):
    """
    Autorise si l'utilisateur est agent administratif ou superadmin.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        # Permet si role AGENT ou SUPERADMIN, ou si superuser Django
        return getattr(user, "role", None) in ("AGENT", "SUPERADMIN") or user.is_superuser
