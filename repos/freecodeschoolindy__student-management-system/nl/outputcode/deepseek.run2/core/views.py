from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from .models import StudentProfile, Course, Enrollment, Waitlist, Volunteer, User
from .serializers import (
    StudentProfileSerializer, CourseSerializer, EnrollmentSerializer,
    WaitlistSerializer, VolunteerSerializer, UserSerializer, LoginSerializer
)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, 'user': UserSerializer(user).data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileView(APIView):
    def get(self, request):
        if request.user.user_type == 'student':
            profile, created = StudentProfile.objects.get_or_create(user=request.user)
            serializer = StudentProfileSerializer(profile)
            return Response(serializer.data)
        return Response({'detail': 'Not a student'}, status=403)

    def put(self, request):
        if request.user.user_type == 'student':
            profile, created = StudentProfile.objects.get_or_create(user=request.user)
            serializer = StudentProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        return Response({'detail': 'Not a student'}, status=403)

class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Course.objects.filter(is_active=True)
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

class EnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['organizer', 'admin']:
            return Enrollment.objects.all()
        return Enrollment.objects.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

class WaitlistViewSet(viewsets.ModelViewSet):
    serializer_class = WaitlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['organizer', 'admin']:
            return Waitlist.objects.all()
        return Waitlist.objects.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

class VolunteerViewSet(viewsets.ModelViewSet):
    serializer_class = VolunteerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['organizer', 'admin']:
            return Volunteer.objects.all()
        return Volunteer.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
