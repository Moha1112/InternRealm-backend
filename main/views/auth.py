from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import UserLoginSerializer

class LoginView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = authenticate(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        
        if not user:
            return Response(
                {"error": "Invalid credentials"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role
            }
        })

class SignupView(APIView):
    # Different serializers for student/company signup
    def post(self, request):
        role = request.data.get('role')
        
        if role == User.Role.STUDENT:
            serializer = StudentSignupSerializer(data=request.data)
        elif role == User.Role.COMPANY:
            serializer = CompanySignupSerializer(data=request.data)
        else:
            return Response(
                {"error": "Invalid role"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Send verification email
        send_verification_email(user)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)