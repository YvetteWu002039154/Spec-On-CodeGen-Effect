# =========================
# Permissions
# =========================

from rest_framework import permissions
from rest_framework import permissions, routers, serializers, status, viewsets
from rest_framework.request import Request

from typing import Any, Dict, List, Optional, Tuple

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request: Request, view: viewsets.ViewSet) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request: Request, view: viewsets.ViewSet, obj: Any) -> bool:
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True
        if hasattr(obj, "user_id"):
            return bool(request.user and request.user.is_authenticated and obj.user_id == request.user.id)
        if hasattr(obj, "borrowing") and hasattr(obj.borrowing, "user_id"):
            return bool(request.user and request.user.is_authenticated and obj.borrowing.user_id == request.user.id)
        return False

