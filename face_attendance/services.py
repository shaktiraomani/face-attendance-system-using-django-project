import cv2
import numpy as np
from deepface import DeepFace
from datetime import datetime
import os
import tempfile
from .models import Student, Attendance

class FaceRecognitionService:
    def __init__(self):
        self.known_face_embeddings = []
        self.known_face_student_ids = []
        self.student_data = {}
        self.model_name = "VGG-Face"  # Default model in DeepFace
        self.detector_backend = "opencv"  # Faster than MTCNN but still accurate
        self.distance_metric = "cosine"
        self.recognition_threshold = 0.4  # Threshold for face recognition (lower is stricter)
        self.load_student_data()
    
    def load_student_data(self):
        """Load student data from the database"""
        self.known_face_embeddings = []
        self.known_face_student_ids = []
        self.student_data = {}
        
        students = Student.objects.all()
        for student in students:
            try:
                embeddings = student.get_face_embeddings()
                for embedding in embeddings:
                    self.known_face_embeddings.append(embedding)
                    self.known_face_student_ids.append(student.id)
                
                self.student_data[student.id] = {
                    'name': student.name,
                    'surname': student.surname,
                    'faculty': student.faculty,
                    'group': student.group
                }
            except Exception as e:
                print(f"Error loading student {student.id}: {e}")
    
    def extract_faces(self, img):
        """Extract faces from an image using DeepFace"""
        try:
            # Use DeepFace.extract_faces instead of functions.extract_faces
            faces = DeepFace.extract_faces(
                img_path=img,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )
            return faces
        except Exception as e:
            print(f"Error extracting faces: {e}")
            return []
    
    def get_embedding(self, face_img):
        """Get face embedding using DeepFace"""
        try:
            embedding = DeepFace.represent(
                img_path=face_img,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )
            return embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None
    
    def find_closest_match(self, embedding):
        """Find the closest match for a face embedding"""
        if not self.known_face_embeddings:
            return None, 0.0
        
        # Calculate distances to all known embeddings
        distances = []
        for known_embedding in self.known_face_embeddings:
            if self.distance_metric == "cosine":
                # Use numpy's cosine distance
                similarity = np.dot(embedding, known_embedding) / (np.linalg.norm(embedding) * np.linalg.norm(known_embedding))
                distance = 1 - similarity
            elif self.distance_metric == "euclidean":
                # Use numpy's euclidean distance
                distance = np.linalg.norm(embedding - known_embedding)
            else:
                # Default to euclidean
                distance = np.linalg.norm(embedding - known_embedding)
            distances.append(distance)
        
        # Find the closest match
        min_distance_idx = np.argmin(distances)
        min_distance = distances[min_distance_idx]
        
        # Check if the distance is below the threshold
        if min_distance < self.recognition_threshold:
            student_id = self.known_face_student_ids[min_distance_idx]
            # Convert distance to similarity (1 - distance)
            similarity = 1 - min_distance
            return student_id, similarity
        
        return None, 0.0
    
    def process_frame(self, frame):
        """Process a video frame and recognize faces"""
        # Extract faces from the frame
        faces = self.extract_faces(frame)
        
        for face in faces:
            # In newer versions, the structure might be different
            # Check if face is a dictionary with 'face' and 'facial_area' keys
            if isinstance(face, dict) and 'face' in face and 'facial_area' in face:
                face_img = face["face"]
                facial_area = face["facial_area"]
                
                # Get coordinates
                if isinstance(facial_area, dict):
                    x = facial_area.get("x", 0)
                    y = facial_area.get("y", 0)
                    w = facial_area.get("w", 0)
                    h = facial_area.get("h", 0)
                else:
                    # If facial_area is not a dict, it might be a list or tuple [x, y, w, h]
                    try:
                        x, y, w, h = facial_area
                    except:
                        # Fallback
                        x, y, w, h = 0, 0, 0, 0
            else:
                # If the structure is different, try to adapt
                try:
                    # It might be a tuple of (face_img, [x, y, w, h])
                    if isinstance(face, tuple) and len(face) == 2:
                        face_img, facial_area = face
                        x, y, w, h = facial_area
                    else:
                        # Just use the face as is
                        face_img = face
                        x, y, w, h = 0, 0, 100, 100  # Default values
                except:
                    # Skip this face if we can't process it
                    continue
            
            # Get embedding for the face
            embedding = self.get_embedding(face_img)
            
            if embedding:
                # Find the closest match
                student_id, similarity = self.find_closest_match(embedding)
                
                # Draw rectangle and name
                if student_id:
                    student_data = self.student_data[student_id]
                    name = f"{student_data['name']} {student_data['surname']}"
                    color = (0, 255, 0)  # Green for recognized
                    
                    # Record attendance
                    self.record_attendance(student_id, similarity)
                else:
                    name = "Unknown"
                    color = (0, 0, 255)  # Red for unknown
                    similarity = 0.0
                
                # Draw rectangle around face
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                
                # Draw label with name
                label = f"{name} ({similarity:.2%})"
                cv2.rectangle(frame, (x, y+h), (x+w, y+h+30), color, cv2.FILLED)
                cv2.putText(frame, label, (x+6, y+h+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def record_attendance(self, student_id, probability):
        """Record attendance for a recognized student"""
        today = datetime.now().date()
        current_time = datetime.now().time()
        
        try:
            # Check if attendance already recorded for today
            attendance, created = Attendance.objects.get_or_create(
                student_id=student_id,
                date=today,
                defaults={
                    'status': 'Present',
                    'arrival_time': current_time,
                    'recognition_probability': probability * 100  # Convert to percentage
                }
            )
            
            # If attendance was already recorded, update probability if higher
            if not created and attendance.recognition_probability < probability * 100:
                attendance.recognition_probability = probability * 100
                attendance.save()
        except Exception as e:
            print(f"Error recording attendance: {e}")