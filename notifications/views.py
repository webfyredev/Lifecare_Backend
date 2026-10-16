from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializers


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user)
        unread_count = notifications.filter(is_read=False).count()
        serializers = NotificationSerializers(notifications[:20], many=True)
        return Response({
            "notifications" : serializers.data,
            "unread_count" : unread_count
        })


class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        Notification.objects.filter(recipient = request.user, is_read=False).update(is_read=True)
        return Response({"message" : "All marked as read."})

class MarkOneReadView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            notif = Notification.objects.get(pk=pk, recipient=request.user)
            notif.is_read = True
            notif.save()
            return Response({"message" : "Marked as read"})
        except Notification.DoesNotExist:
            return Response({"error" : "Not Found."}, status=404)