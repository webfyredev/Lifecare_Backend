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
        except Conversation.DoesNotExist:
            return Response({"error" : "Not Found"}, status=404)
        
        body = request.data.get('body', '').strip()
        file = request.FILES.get('file')

        file_type = ''
        if file:
            if file.content_type.startswith('image'):
                file_type = 'image'
            elif file.content_type in ['application/pdf']:
                file_type = 'pdf'
            elif 'document' in file.content_type or 'word' in file.content_type:
                file_type = 'document'
            else:
                file_type = 'file'
        
        if not body and not file:
            return Response({"error" : "Message cannot be empty."}, status=400)


        message = Message.objects.create(conversation=conv, sender=request.user, body=body, file=file or None, file_type=file_type)
        conv.save()
        serializer = MessageSerializer(message, context={'request' : request})
        return Response(serializer.data, status=201)


class MessageDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, conv_id, message_id):
        try:
            message = Message.objects.get(id=message_id, conversation_id=conv_id, sender=request.user)
            new_body = request.data.get('body', '').strip()
            if not new_body:
                return Response({"error" : "Message cannot be empty."}, status=400)
            message.body = new_body
            message.is_edited = True
            message.save()

            serializer = MessageSerializer(message, context={'request' : request})
            return Response(serializer.data)
        except Message.DoesNotExist:
            return Response({"error" : "Not found"}, status=404)
    
    def delete(self, request, conv_id, message_id):
        try:
            message = Message.objects.get(id=message_id, conversation_id=conv_id, sender=request.user)
            message.delete()
            return Response({"message" : "Deleted"}, status=204)
        except Message.DoesNotExist:
            return Response({"error" : "Not found."}, status=404)



