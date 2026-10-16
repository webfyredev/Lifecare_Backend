from rest_framework.permissions import BasePermission

class IsPatient(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'patient'

class IsDoctor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'doctor'

class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

class IsPatientOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and getattr(request.user, 'role', None) in ['patient', 'admin'])

class IsDoctorOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and (request.user.role in ['doctor', 'admin'] or request.user.is_staff))