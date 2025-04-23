from django.contrib import admin
from .models import Student, Schedule, Attendance, Contact, SMTPSettings

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'surname', 'faculty', 'group')
    search_fields = ('name', 'surname', 'group')
    list_filter = ('faculty', 'group')

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('day', 'start_time', 'late_time', 'end_time')
    list_filter = ('day',)

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'status', 'arrival_time', 'recognition_probability')
    list_filter = ('date', 'status')
    search_fields = ('student__name', 'student__surname')
    date_hierarchy = 'date'

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')
    search_fields = ('name', 'email')

@admin.register(SMTPSettings)
class SMTPSettingsAdmin(admin.ModelAdmin):
    list_display = ('email', 'smtp_server', 'smtp_port')