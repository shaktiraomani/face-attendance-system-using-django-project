from django.db import models
import json
import numpy as np

class Student(models.Model):
    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    faculty = models.CharField(max_length=100)
    direction = models.CharField(max_length=100)
    group = models.CharField(max_length=50)
    face_embeddings = models.TextField()  # Store face embeddings as JSON string
    
    def set_face_embeddings(self, embeddings_list):
        self.face_embeddings = json.dumps([e.tolist() if isinstance(e, np.ndarray) else e for e in embeddings_list])
    
    def get_face_embeddings(self):
        embeddings = json.loads(self.face_embeddings)
        return [np.array(e) for e in embeddings]
    
    def __str__(self):
        return f"{self.name} {self.surname}"

class Schedule(models.Model):
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]
    
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    start_time = models.TimeField()
    late_time = models.TimeField()
    end_time = models.TimeField()
    
    class Meta:
        unique_together = ['day']
    
    def __str__(self):
        return f"{self.day}: {self.start_time} - {self.end_time}"

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Late', 'Late'),
        ('Absent', 'Absent'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    arrival_time = models.TimeField(null=True, blank=True)
    recognition_probability = models.FloatField(default=0.0)
    
    class Meta:
        unique_together = ['student', 'date']
    
    def __str__(self):
        return f"{self.student} - {self.date} - {self.status}"

class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    
    def __str__(self):
        return self.name

class SMTPSettings(models.Model):
    email = models.EmailField()
    smtp_server = models.CharField(max_length=100)
    smtp_port = models.IntegerField(default=587)
    password = models.CharField(max_length=100)
    
    def __str__(self):
        return self.email