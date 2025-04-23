from django import forms
from .models import Student, Schedule, Contact, SMTPSettings

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class StudentForm(forms.ModelForm):
    photos = MultipleFileField(required=True, help_text="Upload at least 4 photos of the student for face recognition")
    
    class Meta:
        model = Student
        fields = ['name', 'surname', 'father_name', 'faculty', 'direction', 'group']
        
class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['day', 'start_time', 'late_time', 'end_time']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'late_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email']

class SMTPSettingsForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    
    class Meta:
        model = SMTPSettings
        fields = ['email', 'smtp_server', 'smtp_port', 'password']

class AttendanceSetupForm(forms.Form):
    MODE_CHOICES = [
        ('manual', 'Manual Mode'),
        ('schedule', 'Schedule Mode'),
    ]
    
    DEADLINE_CHOICES = [
        ('time', 'Specific Time'),
        ('timer', 'Timer'),
    ]
    
    TIMER_CHOICES = [
        ('5', '5 minutes'),
        ('10', '10 minutes'),
        ('15', '15 minutes'),
        ('30', '30 minutes'),
    ]
    
    mode = forms.ChoiceField(choices=MODE_CHOICES, widget=forms.RadioSelect)
    database = forms.CharField(widget=forms.HiddenInput(), initial="default")
    schedule = forms.ModelChoiceField(queryset=Schedule.objects.all(), required=False)
    camera = forms.ChoiceField(choices=[(0, 'Camera 0 (Default)'), (1, 'Camera 1'), (2, 'Camera 2'), ('ip', 'IP Camera')])
    ip_camera = forms.URLField(required=False)
    
    late_deadline_type = forms.ChoiceField(choices=DEADLINE_CHOICES, widget=forms.RadioSelect, required=False)
    late_hour = forms.IntegerField(min_value=0, max_value=23, required=False)
    late_minute = forms.IntegerField(min_value=0, max_value=59, required=False)
    late_timer = forms.ChoiceField(choices=TIMER_CHOICES, required=False)
    
    deadline_type = forms.ChoiceField(choices=DEADLINE_CHOICES, widget=forms.RadioSelect, required=False)
    hour = forms.IntegerField(min_value=0, max_value=23, required=False)
    minute = forms.IntegerField(min_value=0, max_value=59, required=False)
    timer = forms.ChoiceField(choices=TIMER_CHOICES, required=False)

class ReportFilterForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    group = forms.CharField(required=False)
    faculty = forms.CharField(required=False)

class EmailReportForm(forms.Form):
    recipient = forms.EmailField()
    subject = forms.CharField(max_length=100, initial="Attendance Report")
    message = forms.CharField(widget=forms.Textarea, initial="Please find the attendance report attached.")