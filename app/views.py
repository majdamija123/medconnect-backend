# app/views.py (extrait)
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer
from .permissions import IsAgentOrSuperAdmin
from rest_framework.permissions import IsAuthenticated

class UserAdminViewSet(viewsets.ModelViewSet):
    """
    CRUD utilisateur accessible uniquement aux agents / superadmins.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAgentOrSuperAdmin]
