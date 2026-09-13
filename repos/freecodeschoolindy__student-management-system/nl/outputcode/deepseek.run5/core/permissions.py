from rest_framework import permissions

class IsOwnerOrOrganizer(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or organizers to view/edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Organizers can view/edit any object
        if request.user.role == 'organizer' or request.user.is_staff:
            return True
        # Object must have a 'user' attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False

class IsOrganizer(permissions.BasePermission):
    """
    Allows access only to organizers.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.role == 'organizer' or request.user.is_staff)

