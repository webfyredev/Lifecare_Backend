from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password', 'password2', 'role', 'phone_number')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower() 
    
    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')

        email = validated_data['email']
        base_username = email.split('@')[0] 
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        validated_data['username'] = username
        user = User.objects.create_user(**validated_data)
        if user.role == 'patient':
            from patients.models import PatientProfile
            PatientProfile.objects.create(user=user)
        elif user.role == 'doctor':
            from doctors.models import DoctorProfile
            DoctorProfile.objects.create(user=user)
        
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'profile_picture', 'date_of_birth', 'gender', 'address')
        read_only_fields = ('role',)


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        email = attrs.get('email', '').lower()
        password = attrs.get('password', '')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "No account found with this email."})

        if not user.check_password(password):
            raise serializers.ValidationError({"password": "Incorrect password."})

        if not user.is_active:
            raise serializers.ValidationError("This account has been disabled.")

        # Use parent to generate the tokens
        data = super().validate({
            'email': email,
            'password': password,
        })
        return data

class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer