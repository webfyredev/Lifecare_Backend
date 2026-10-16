from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, UserSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logged out successfully."}, status=205)
        except Exception:
            return Response({"error": "Invalid token."}, status=400)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({"error" : "Email is required."}, status=400)

        try:    
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            reset_url = f"https://life-care-websites.vercel.app/reset-password/{uid}/{token}"

            send_mail(
                subject="Reset your LifeCare password",
                message=f"""Hi {user.first_name},
You requested a password reset for your LifeCare account.

Click the link below to set a new password:

{reset_url}

This link expires in 24 hours.

If you did not request for this, you can safely ignore this email.

-The LifeCare Team""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list= [user.email],
                fail_silently= False
            )
        except User.DoesNotExist:
            pass

        return Response({"message" : "If an account with that email exists, a reset link has been sent."})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    
    def post (self, request):
        uid = request.data.get('uid', '')
        token = request.data.get('token', '')
        new_password = request.data.get('password', '')
        confirm_password = request.data.get('confirm_password', '')

        if not all([uid, token, new_password, confirm_password]):
            return Response({"error" : "All fields are required"}, status=400)
        
        if new_password != confirm_password:
            return Response({"error" : "Password do not match"}, status=400)
        
        if len(new_password) < 8:
            return Response({"error" : "Password must be atleast 8 characters"}, status=400)
        
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"error" : "Invalid reset link."}, status=400)
        
        if not default_token_generator.check_token(user, token):
            return Response({"error" : "The reset link has expired or already been used"}, status=400)

        user.set_password(new_password)
        user.save()

        return Response({"message" : "Password reset successfully. You can now login"})


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        credential = request.data.get('credential')
        role = request.data.get('role', 'patient')
        if not credential:
            return Response({"error" : "Google credentials is required."}, status=400)
        if role not in ['patient', 'doctor']:
            return Response({"error" : "Role must be a patient or doctor"}, status=400)
        try:
            idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
            email = idinfo.get('email', '').lower()
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')

            if not email:
                return Response({"error" : "Could not get email from Google."}, status=400)
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                user = existing_user
                created = False
            else:
                base_username = email.split("@")[0]
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter +=1
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name = first_name,
                    last_name = last_name,
                    role=role,
                    is_active = True
                )
                created = True
                if role == 'patient':
                    from patients.models import PatientProfile
                    PatientProfile.objects.get_or_create(user=user)
                    try:
                        from notifications.emails import send_welcome_email
                        hospital_number = getattr(getattr(user, 'patient_profile', None), 'hospital_number', None)
                        send_welcome_email(user, hospital_number=hospital_number)
                    except Exception as e:
                        print(f"Welcome email failed: {e}")
                elif role == 'doctor':
                    from doctors.models import DoctorProfile
                    DoctorProfile.objects.get_or_create(user=user, defaults={"specialization" : "", "license_number" : f"PENDING-{user.id}", "is_available" : True, 'max_patient_per_day' : 20,})
                    try:
                        from notifications.emails import send_welcome_email
                        send_welcome_email(user)
                    except Exception as e:
                        print(f"Welcome email failed: {e}")            
            refresh = RefreshToken.for_user(user)
            return Response({
                "access" : str(refresh.access_token),
                "refresh" : str(refresh),
                "role" : user.role,
                "email": user.email,
                "message" : "Account created." if created else "Logged in successfully."

            })
        
        except ValueError as e:
            return Response({"error" : f"Invalid Google token: {e}"}, status=400)
        except Exception as e:
            return Response({"error" : str(e)}, status=500)