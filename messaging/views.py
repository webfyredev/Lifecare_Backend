from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer



class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role == 'patient':
            convs = Conversation.objects.filter(patient=request.user).prefetch_related('messages', 'doctor__doctor_profile')
        else:
            convs = Conversation.objects.filter(doctor=request.user).prefetch_related('messages', 'patient')
        
        serializer = ConversationSerializer(convs, many=True, context={'request' : request})
        return Response(serializer.data)

class MessageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conv_id):
        try:
            if request.user.role == 'patient':
                conv = Conversation.objects.get(id=conv_id, patient=request.user)
            else:
                conv = Conversation.objects.get(id=conv_id, doctor=request.user)
            
            conv.messages.exclude(sender=request.user).update(is_read=True)

            messages = conv.messages.select_related('sender')

            serializer = MessageSerializer(messages, many=True, context={'request' : request})
            return Response(serializer.data)
        except Conversation.DoesNotExist:
            return Response({"error" : "Not Found"}, status=404)
    
    def post (self, request, conv_id):
        try:
            if request.user.role == 'patient':
                conv = Conversation.objects.get(id=conv_id, patient=request.user)
            else:
                conv = Conversation.objects.get(id=conv_id, doctor=request.user)
            
            message = Message.objects.create(conversation=conv, sender=request.user, body=request.data.get('body', '').strip())

            conv.save()

            serializer = MessageSerializer(message, context={'request' : request})
            return Response(serializer.data, status=201)
        except Conversation.DoesNotExist:
            return Response({"error" : "Not Found"}, status=404)


