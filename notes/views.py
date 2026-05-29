from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from accounts.permissions import IsDoctor
from .models import MedicalNotes
from accounts.models import User

class MedicalNotesView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request):
        doctor = request.user
        patient_id = request.query_params.get('patient_id')
        severity = request.query_params.get('severity')

        qs = MedicalNotes.objects.filter(doctor=doctor).select_related('patient')
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if severity:
            qs = qs.filter(severity=severity)
        
        return Response([
            {
                "id" : n.id,
                "title" : n.title,
                "content" : n.content,
                "category" : n.category,
                "severity" : n.severity,
                "patient_name" : n.patient.get_full_name(),
                "patient_id" : n.patient_id,
                "appointment_id" : n.appointment_id,
                "created_at" : n.created_at
            } for n in qs
        ])


    def post(self, request):
        doctor = request.user
        patient_id = request.data.get('patient_id')
        title = request.data.get('title', '').strip()
        content = request.data.get('content', '').strip()

        if not patient_id or not title or not content:
            return Response({"error" : "patient_id, title and content are required"}, status=400)
        
        try:
            patient = User.objects.get(id=patient_id, role='patient')
        except User.DoesNotExist:
            return Response({"error" : "Patient not Found"}, status=404)
        
        note = MedicalNotes.objects.create(
            doctor=doctor, 
            patient=patient, 
            title=title, 
            content=content, 
            category=request.data.get('category', ''), 
            severity=request.data.get('severity', 'normal'),
            appointment_id = request.data.get('appointment_id') or None,
            )
        return Response({
            "id" : note.id,
            "title" : note.title,
            "content" : note.content,
            "category" : note.category,
            "severity" : note.severity,
            "patient_name" : note.get_full_name(),
            "created_at" : note.created_at
        }, status=201)


class MedicalNotesDetailView(APIView):
    permission_classes = [IsDoctor]

    def patch(self, request, pk):
        try:
            note = MedicalNotes.objects.get(pk=pk, doctor=request.user)
            note.title = request.data.get('title', note.title)
            note.content = request.data.get('content', note.content)
            note.category = request.data.get('category', note.category)
            note.severity = request.data.get('severity', note.severity)
            note.save()

            return Response({"message" : "Note Updated."})
        except MedicalNotes.DoesNotExist:
            
            return Response({"error" : "Not Found"}, status=404)
    
    def delete(self, request, pk):
        try:
            note = MedicalNotes.objects.get(pk=pk, doctor=request.user)
            note.delete()
            return Response({"message" : "Note deleted"}, status=204)
        except MedicalNotes.DoesNotExist:
            return Response({"error" : "Not Found."}, status=404)