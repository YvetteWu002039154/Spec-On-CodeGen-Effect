from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django.contrib.auth import get_user_model

from .models import (
    StudentProfile,
    Enrollment,
    JobPlacement,
    Volunteer,
    WaitlistEntry,
)
from .serializers import (
    LoginSerializer,
    StudentProfileSerializer,
    EnrollmentSerializer,
    JobPlacementSerializer,
    VolunteerSerializer,
    WaitlistEntrySerializer,
)
from .permissions import IsOwnerOrOrganizer, IsOrganizer

User = get_user_model()

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'role': user.role,
        })

class StudentProfileDetail(generics.RetrieveUpdateAPIView):
    """
    Get/Update the authenticated student's own profile.
    """
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrOrganizer]

    def get_object(self):
        # Return the profile of the authenticated user (if student)
        try:
            return StudentProfile.objects.get(user=self.request.user)
        except StudentProfile.DoesNotExist:
            return None

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance is None:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance is None:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class StudentList(generics.ListAPIView):
    """
    List all student profiles. Organizers only.
    """
    serializer_class = StudentProfileSerializer
    permission_classes = [IsOrganizer]
    queryset = StudentProfile.objects.all()

class StudentDetail(generics.RetrieveAPIView):
    """
    Retrieve any student profile. Organizers only.
    """
    serializer_class = StudentProfileSerializer
    permission_classes = [IsOrganizer]
    queryset = StudentProfile.objects.all()

class StudentEnrollmentListCreate(generics.ListCreateAPIView):
    """
    List/create enrollments for a student profile. Organizers can manage any;
    students see only their own.
    """
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrOrganizer]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'organizer' or user.is_staff:
            return Enrollment.objects.all()
        # student: only own enrollments
        return Enrollment.objects.filter(student_profile__user=user)

    def perform_create(self, serializer):
        # If student creating, ensure student_profile is theirs
        if self.request.user.role == 'student' and not self.request.user.is_staff:
            # Might need to enforce; but serializer has student_profile field anyway.
            # For safety, set the student_profile automatically based on request.user
            profile = StudentProfile.objects.get(user=self.request.user)
            serializer.save(student_profile=profile)
        else:
            serializer.save()

class StudentJobPlacementListCreate(generics.ListCreateAPIView):
    serializer_class = JobPlacementSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrOrganizer]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'organizer' or user.is_staff:
            return JobPlacement.objects.all()
        return JobPlacement.objects.filter(student_profile__user=user)

    def perform_create(self, serializer):
        if self.request.user.role == 'student' and not self.request.user.is_staff:
            profile = StudentProfile.objects.get(user=self.request.user)
            serializer.save(student_profile=profile)
        else:
            serializer.save()

class VolunteerListCreate(generics.ListCreateAPIView):
    queryset = Volunteer.objects.all()
    serializer_class = VolunteerSerializer
    permission_classes = [IsOrganizer]

class VolunteerDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Volunteer.objects.all()
    serializer_class = VolunteerSerializer
    permission_classes = [IsOrganizer]

class WaitlistListCreate(generics.ListCreateAPIView):
    queryset = WaitlistEntry.objects.all()
    serializer_class = WaitlistEntrySerializer
    permission_classes = [IsOrganizer]

class WaitlistDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = WaitlistEntry.objects.all()
    serializer_class = WaitlistEntrySerializer
    permission_classes = [IsOrganizer]

