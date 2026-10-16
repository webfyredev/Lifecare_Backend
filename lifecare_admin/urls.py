from django.urls import path
from .views import *

urlpatterns = [
    path('dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('manage-users/', AdminManageUsersView.as_view(), name='admin-manage-users'),
    path('manage-users/<int:user_id>/', AdminManageUserDetailView.as_view(), name='manage-userdetail-view'),
    path('manage-users/<int:user_id>/suspend/', AdminSuspendUserView.as_view(), name='admin-suspend_user'),
    path('manage-users/<int:user_id>/restore/', AdminRestoreUserView.as_view(), name='restore-user'),
    path('manage-doctors/', AdminManageDoctorView.as_view(), name='manage-doctors'),
    path('manage-doctors/<int:doctor_id>/approve/', AdminApproveDoctorView.as_view(), name='approve-doctors'),
    path('manage-doctors/<int:doctor_id>/reject/', AdminRejectDoctorView.as_view(), name='reject-doctor'),
    path('manage-appointments/', AdminManageAppointmentView.as_view(), name='manage-appointments'),
    path('manage_appt/<int:apt_id>/delete/', AdminDeleteAppointments.as_view(), name='delete-appointments'),
    path('manage-patients-list/', AdminListPatientsView.as_view(), name='admin-manage_app_patients'),
    path('manage-prescriptions/', AdminManagePrescriptions.as_view(), name='manage-prescriptions'),
    path('manage-doctors-list/', AdminListDoctorsView.as_view(), name='doctors-list'),
    path('manage-users-list/', AdminListUsersView.as_view(), name='users-list'),
    path('manage-records/', AdminManageRecords.as_view(), name='manage-records'),
    path('manage-notif/', AdminManageNotification.as_view(), name='manage-notifications'),
    path('delete-notif/<int:notif_id>/', AdminDeleteNotification.as_view(), name='delete-notification'),
    path('manage-messsages/', AdminManageMessage.as_view(), name='manage-messages'),
    path('conversations/add/', AdminManageConversationsView.as_view(), name='add-conversations'),
    path('conversations/<int:pk>/delete/', AdminManageConversationsView.as_view(), name='delete-conversations')
    
]
