from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
import json
import cv2
import numpy as np
import pandas as pd
import os
import tempfile
from datetime import datetime, timedelta
from deepface import DeepFace
from .models import Student, Schedule, Attendance, Contact, SMTPSettings
from .forms import (
    StudentForm, ScheduleForm, ContactForm, SMTPSettingsForm, 
    AttendanceSetupForm, ReportFilterForm, EmailReportForm
)
from .services import FaceRecognitionService

# Initialize face recognition service
face_service = None

def get_face_service():
    global face_service
    if face_service is None:
        face_service = FaceRecognitionService()
    return face_service

def index(request):
    """Home page view"""
    return render(request, 'face_attendance/index.html')

def students_list(request):
    """List all students"""
    students = Student.objects.all()
    return render(request, 'face_attendance/students.html', {'students': students})

def add_student(request):
    """Add a new student"""
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            # Process form data
            student = form.save(commit=False)
            
            # Process uploaded images
            face_embeddings = []
            valid_images = 0
            
            for image_file in request.FILES.getlist('photos'):
                try:
                    # Save the image temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                        for chunk in image_file.chunks():
                            temp_file.write(chunk)
                        temp_file_path = temp_file.name
                    
                    # Process the image with DeepFace
                    try:
                        # Extract faces
                        faces = DeepFace.extract_faces(
                            img_path=temp_file_path,
                            detector_backend="opencv",
                            enforce_detection=False
                        )
                        
                        if faces:
                            # Get embedding for the first face
                            embedding = DeepFace.represent(
                                img_path=temp_file_path,
                                model_name="VGG-Face",
                                detector_backend="opencv",
                                enforce_detection=False
                            )
                            
                            if embedding:
                                face_embeddings.append(embedding)
                                valid_images += 1
                        else:
                            messages.warning(request, f"No face detected in {image_file.name}")
                    except Exception as e:
                        messages.warning(request, f"Error processing {image_file.name}: {e}")
                    
                    # Clean up the temporary file
                    os.unlink(temp_file_path)
                except Exception as e:
                    messages.error(request, f"Error processing {image_file.name}: {e}")
            
            if valid_images < 4:
                messages.error(request, "At least 4 valid face images are required")
                return render(request, 'face_attendance/add_student.html', {'form': form})
            
            # Save student with face embeddings
            student.set_face_embeddings(face_embeddings)
            student.save()
            
            # Reload face recognition service data
            get_face_service().load_student_data()
            
            messages.success(request, f"Student {student.name} {student.surname} added successfully")
            return redirect('students_list')
    else:
        form = StudentForm()
    
    return render(request, 'face_attendance/add_student.html', {'form': form})
def delete_student(request, student_id):
    """Delete a student"""
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        student.delete()
        # Reload face recognition service data
        get_face_service().load_student_data()
        messages.success(request, f"Student {student.name} {student.surname} deleted successfully")
        return redirect('students_list')
    
    return render(request, 'face_attendance/delete_student.html', {'student': student})

def schedules(request):
    """List all schedules"""
    schedules = Schedule.objects.all()
    return render(request, 'face_attendance/schedules.html', {'schedules': schedules})

def add_schedule(request):
    """Add a new schedule"""
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        if form.is_valid():
            # Check if times are in correct order
            start_time = form.cleaned_data['start_time']
            late_time = form.cleaned_data['late_time']
            end_time = form.cleaned_data['end_time']
            
            if not (start_time < late_time < end_time):
                messages.error(request, "Times must be in order: Start < Late < End")
                return render(request, 'face_attendance/add_schedule.html', {'form': form})
            
            # Check if schedule for this day already exists
            day = form.cleaned_data['day']
            existing_schedule = Schedule.objects.filter(day=day).first()
            
            if existing_schedule:
                # Update existing schedule
                existing_schedule.start_time = start_time
                existing_schedule.late_time = late_time
                existing_schedule.end_time = end_time
                existing_schedule.save()
                messages.success(request, f"Schedule for {day} updated successfully")
            else:
                # Create new schedule
                form.save()
                messages.success(request, f"Schedule for {day} added successfully")
            
            return redirect('schedules')
    else:
        form = ScheduleForm()
    
    return render(request, 'face_attendance/add_schedule.html', {'form': form})

def delete_schedule(request, schedule_id):
    """Delete a schedule"""
    schedule = get_object_or_404(Schedule, id=schedule_id)
    if request.method == 'POST':
        schedule.delete()
        messages.success(request, f"Schedule for {schedule.day} deleted successfully")
        return redirect('schedules')
    
    return render(request, 'face_attendance/delete_schedule.html', {'schedule': schedule})

def attendance_setup(request):
    """Setup attendance tracking"""
    if request.method == 'POST':
        form = AttendanceSetupForm(request.POST)
        if form.is_valid():
            # Process form data
            mode = form.cleaned_data['mode']
            camera_source = form.cleaned_data['camera']
            
            # Store form data in session for use in attendance view
            request.session['attendance_setup'] = {
                'mode': mode,
                'camera': camera_source,
            }
            
            if camera_source == 'ip':
                request.session['attendance_setup']['ip_camera'] = form.cleaned_data['ip_camera']
            
            if mode == 'manual':
                late_deadline_type = form.cleaned_data['late_deadline_type']
                deadline_type = form.cleaned_data['deadline_type']
                
                request.session['attendance_setup']['late_deadline_type'] = late_deadline_type
                request.session['attendance_setup']['deadline_type'] = deadline_type
                
                if late_deadline_type == 'time':
                    request.session['attendance_setup']['late_hour'] = form.cleaned_data['late_hour']
                    request.session['attendance_setup']['late_minute'] = form.cleaned_data['late_minute']
                else:
                    request.session['attendance_setup']['late_timer'] = form.cleaned_data['late_timer']
                
                if deadline_type == 'time':
                    request.session['attendance_setup']['hour'] = form.cleaned_data['hour']
                    request.session['attendance_setup']['minute'] = form.cleaned_data['minute']
                else:
                    request.session['attendance_setup']['timer'] = form.cleaned_data['timer']
            else:
                request.session['attendance_setup']['schedule_id'] = form.cleaned_data['schedule'].id
            
            return redirect('start_attendance')
    else:
        form = AttendanceSetupForm()
    
    return render(request, 'face_attendance/attendance_setup.html', {'form': form})

def start_attendance(request):
    """Start attendance tracking"""
    # Get setup data from session
    setup_data = request.session.get('attendance_setup', {})
    if not setup_data:
        messages.error(request, "Attendance setup data not found")
        return redirect('attendance_setup')
    
    # Calculate deadlines
    now = datetime.now()
    late_deadline = None
    deadline = None
    
    if setup_data['mode'] == 'manual':
        if setup_data['late_deadline_type'] == 'time':
            late_hour = setup_data.get('late_hour', 0)
            late_minute = setup_data.get('late_minute', 0)
            late_deadline = datetime.combine(now.date(), datetime.min.time()).replace(hour=late_hour, minute=late_minute)
            if late_deadline < now:
                late_deadline += timedelta(days=1)
        else:
            late_timer = int(setup_data.get('late_timer', 5))
            late_deadline = now + timedelta(minutes=late_timer)
        
        if setup_data['deadline_type'] == 'time':
            hour = setup_data.get('hour', 0)
            minute = setup_data.get('minute', 0)
            deadline = datetime.combine(now.date(), datetime.min.time()).replace(hour=hour, minute=minute)
            if deadline < now:
                deadline += timedelta(days=1)
        else:
            timer = int(setup_data.get('timer', 5))
            deadline = now + timedelta(minutes=timer)
    else:
        # Get schedule
        schedule_id = setup_data.get('schedule_id')
        try:
            schedule = Schedule.objects.get(id=schedule_id)
            
            # Calculate deadlines based on schedule
            late_deadline = datetime.combine(now.date(), schedule.late_time)
            deadline = datetime.combine(now.date(), schedule.end_time)
            
            if late_deadline < now:
                late_deadline += timedelta(days=1)
            if deadline < now:
                deadline += timedelta(days=1)
        except Schedule.DoesNotExist:
            messages.error(request, "Schedule not found")
            return redirect('attendance_setup')
    
    # Store deadlines in session
    request.session['attendance_deadlines'] = {
        'late_deadline': late_deadline.isoformat() if late_deadline else None,
        'deadline': deadline.isoformat() if deadline else None,
    }
    
    return render(request, 'face_attendance/start_attendance.html', {
        'setup_data': setup_data,
        'late_deadline': late_deadline,
        'deadline': deadline,
    })

def gen_frames():
    """Generate video frames with face recognition"""
    # Get face recognition service
    service = get_face_service()
    
    # Open camera
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        yield (b'--frame\r\n'
               b'Content-Type: text/plain\r\n\r\n'
               b'Camera not available\r\n')
        return
    
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Process frame with face recognition
            processed_frame = service.process_frame(frame)
            
            # Encode the frame in JPEG format
            ret, buffer = cv2.imencode('.jpg', processed_frame)
            frame = buffer.tobytes()
            
            # Yield the frame in byte format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    camera.release()

def video_feed(request):
    """Video feed for attendance tracking"""
    return StreamingHttpResponse(gen_frames(), content_type='multipart/x-mixed-replace; boundary=frame')

def attendance_status(request):
    """Get current attendance status"""
    # Get today's attendance records
    today = datetime.now().date()
    attendance_records = Attendance.objects.filter(date=today).select_related('student')
    
    # Count statistics
    present_count = attendance_records.filter(status='Present').count()
    late_count = attendance_records.filter(status='Late').count()
    
    # Get all students
    all_students = Student.objects.all()
    total_count = all_students.count()
    absent_count = total_count - present_count - late_count
    
    # Get recent records
    recent_records = []
    for record in attendance_records.order_by('-arrival_time')[:10]:
        recent_records.append({
            'name': f"{record.student.name} {record.student.surname}",
            'time': record.arrival_time.strftime('%H:%M:%S'),
            'status': record.status,
            'probability': f"{record.recognition_probability:.2f}%"
        })
    
    # Check if deadline has passed
    deadline_str = request.session.get('attendance_deadlines', {}).get('deadline')
    session_expired = False
    
    if deadline_str:
        deadline = datetime.fromisoformat(deadline_str)
        if datetime.now() > deadline:
            session_expired = True
    
    return JsonResponse({
        'present': present_count,
        'late': late_count,
        'absent': absent_count,
        'total': total_count,
        'recent_records': recent_records,
        'session_expired': session_expired
    })

def stop_attendance(request):
    """Stop attendance tracking and show summary"""
    # Clear session data
    if 'attendance_setup' in request.session:
        del request.session['attendance_setup']
    if 'attendance_deadlines' in request.session:
        del request.session['attendance_deadlines']
    
    # Get today's attendance records
    today = datetime.now().date()
    attendance_records = Attendance.objects.filter(date=today).select_related('student')
    
    # Mark absent students
    all_students = Student.objects.all()
    present_student_ids = attendance_records.values_list('student_id', flat=True)
    
    for student in all_students:
        if student.id not in present_student_ids:
            Attendance.objects.create(
                student=student,
                date=today,
                status='Absent'
            )
    
    # Refresh attendance records
    attendance_records = Attendance.objects.filter(date=today).select_related('student')
    
    return render(request, 'face_attendance/attendance_summary.html', {
        'attendance_records': attendance_records,
        'present_count': attendance_records.filter(status='Present').count(),
        'late_count': attendance_records.filter(status='Late').count(),
        'absent_count': attendance_records.filter(status='Absent').count(),
        'total_count': all_students.count()
    })

def reports(request):
    """View attendance reports"""
    form = ReportFilterForm(request.GET)
    
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    group = request.GET.get('group')
    faculty = request.GET.get('faculty')
    
    # Build query
    attendance_records = Attendance.objects.select_related('student').all()
    
    if start_date:
        attendance_records = attendance_records.filter(date__gte=start_date)
    if end_date:
        attendance_records = attendance_records.filter(date__lte=end_date)
    if group:
        attendance_records = attendance_records.filter(student__group=group)
    if faculty:
        attendance_records = attendance_records.filter(student__faculty=faculty)
    
    # Get unique groups and faculties for filter dropdowns
    groups = Student.objects.values_list('group', flat=True).distinct()
    faculties = Student.objects.values_list('faculty', flat=True).distinct()
    
    return render(request, 'face_attendance/reports.html', {
        'form': form,
        'records': attendance_records,
        'groups': groups,
        'faculties': faculties,
        'present_count': attendance_records.filter(status='Present').count(),
        'late_count': attendance_records.filter(status='Late').count(),
        'absent_count': attendance_records.filter(status='Absent').count(),
    })

def export_report(request):
    """Export attendance report to Excel"""
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    group = request.GET.get('group')
    faculty = request.GET.get('faculty')
    
    # Build query
    attendance_records = Attendance.objects.select_related('student').all()
    
    if start_date:
        attendance_records = attendance_records.filter(date__gte=start_date)
    if end_date:
        attendance_records = attendance_records.filter(date__lte=end_date)
    if group:
        attendance_records = attendance_records.filter(student__group=group)
    if faculty:
        attendance_records = attendance_records.filter(student__faculty=faculty)
    
    # Create DataFrame
    data = []
    for record in attendance_records:
        data.append({
            'Name': record.student.name,
            'Surname': record.student.surname,
            'Father Name': record.student.father_name,
            'Faculty': record.student.faculty,
            'Direction': record.student.direction,
            'Group': record.student.group,
            'Date': record.date,
            'Status': record.status,
            'Arrival Time': record.arrival_time,
            'Recognition Probability': f"{record.recognition_probability:.2f}%" if record.recognition_probability > 0 else None
        })
    
    df = pd.DataFrame(data)
    
    # Create Excel file
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = f'attachment; filename=attendance_report_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'
    
    # Write DataFrame to Excel
    df.to_excel(response, index=False)
    
    return response

def email_report(request):
    """Email attendance report"""
    if request.method == 'POST':
        form = EmailReportForm(request.POST)
        if form.is_valid():
            recipient = form.cleaned_data['recipient']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            # Get filter parameters
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            group = request.GET.get('group')
            faculty = request.GET.get('faculty')
            
            # Build query
            attendance_records = Attendance.objects.select_related('student').all()
            
            if start_date:
                attendance_records = attendance_records.filter(date__gte=start_date)
            if end_date:
                attendance_records = attendance_records.filter(date__lte=end_date)
            if group:
                attendance_records = attendance_records.filter(student__group=group)
            if faculty:
                attendance_records = attendance_records.filter(student__faculty=faculty)
            
            # Create DataFrame
            data = []
            for record in attendance_records:
                data.append({
                    'Name': record.student.name,
                    'Surname': record.student.surname,
                    'Father Name': record.student.father_name,
                    'Faculty': record.student.faculty,
                    'Direction': record.student.direction,
                    'Group': record.student.group,
                    'Date': record.date,
                    'Status': record.status,
                    'Arrival Time': record.arrival_time,
                    'Recognition Probability': f"{record.recognition_probability:.2f}%" if record.recognition_probability > 0 else None
                })
            
            df = pd.DataFrame(data)
            
            # Create Excel file
            filename = f'attendance_report_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'
            filepath = os.path.join(tempfile.gettempdir(), filename)
            df.to_excel(filepath, index=False)
            
            # Send email
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.EMAIL_HOST_USER,
                to=[recipient]
            )
            
            # Attach Excel file
            with open(filepath, 'rb') as f:
                email.attach(filename, f.read(), 'application/vnd.ms-excel')
            
            try:
                email.send()
                os.unlink(filepath)  # Delete temporary file
                messages.success(request, f"Report sent to {recipient} successfully")
                return redirect('reports')
            except Exception as e:
                messages.error(request, f"Error sending email: {e}")
    else:
        form = EmailReportForm()
    
    return render(request, 'face_attendance/email_report.html', {'form': form})

def settings_view(request):
    """View and manage settings"""
    contacts = Contact.objects.all()
    
    # Get or create SMTP settings
    smtp_settings = SMTPSettings.objects.first()
    if not smtp_settings:
        smtp_settings = SMTPSettings()
    
    if request.method == 'POST':
        if 'contact_form' in request.POST:
            contact_form = ContactForm(request.POST)
            smtp_form = SMTPSettingsForm(instance=smtp_settings)
            
            if contact_form.is_valid():
                contact_form.save()
                messages.success(request, "Contact added successfully")
                return redirect('settings')
        else:
            contact_form = ContactForm()
            smtp_form = SMTPSettingsForm(request.POST, instance=smtp_settings)
            
            if smtp_form.is_valid():
                smtp_form.save()
                messages.success(request, "SMTP settings saved successfully")
                return redirect('settings')
    else:
        contact_form = ContactForm()
        smtp_form = SMTPSettingsForm(instance=smtp_settings)
    
    return render(request, 'face_attendance/settings.html', {
        'contacts': contacts,
        'contact_form': contact_form,
        'smtp_form': smtp_form
    })

def delete_contact(request, contact_id):
    """Delete a contact"""
    contact = get_object_or_404(Contact, id=contact_id)
    if request.method == 'POST':
        contact.delete()
        messages.success(request, f"Contact {contact.name} deleted successfully")
        return redirect('settings')
    
    return render(request, 'face_attendance/delete_contact.html', {'contact': contact})