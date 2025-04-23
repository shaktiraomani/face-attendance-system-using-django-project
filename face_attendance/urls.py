from django.urls import path
from . import views

urlpatterns = [
    # Home page
    path('', views.index, name='index'),
    
    # Students
    path('students/', views.students_list, name='students_list'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/delete/<int:student_id>/', views.delete_student, name='delete_student'),
    
    # Schedules
    path('schedules/', views.schedules, name='schedules'),
    path('schedules/add/', views.add_schedule, name='add_schedule'),
    path('schedules/delete/<int:schedule_id>/', views.delete_schedule, name='delete_schedule'),
    
    # Attendance
    path('attendance/setup/', views.attendance_setup, name='attendance_setup'),
    path('attendance/start/', views.start_attendance, name='start_attendance'),
    path('attendance/video_feed/', views.video_feed, name='video_feed'),
    path('attendance/status/', views.attendance_status, name='attendance_status'),
    path('attendance/stop/', views.stop_attendance, name='stop_attendance'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/export/', views.export_report, name='export_report'),
    path('reports/email/', views.email_report, name='email_report'),
    
    # Settings
    path('settings/', views.settings_view, name='settings'),
    path('settings/delete_contact/<int:contact_id>/', views.delete_contact, name='delete_contact'),
]