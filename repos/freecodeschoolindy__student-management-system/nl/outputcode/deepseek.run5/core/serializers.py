from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    StudentProfile,
    Course,
    Enrollment,
    JobPlacement,
    Volunteer,
    WaitlistEntry,
)
from django.contrib.auth import authenticate

User = get_user_model()

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid credentials")

class StudentProfileSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = StudentProfile
        fields = '__all__'
        read_only_fields = ('user',)

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'

class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(), source='course', write_only=True
    )

    class Meta:
        model = Enrollment
        fields = ('id', 'student_profile', 'course', 'course_id', 'status', 'enrolled_date')
        read_only_fields = ('student_profile', 'enrolled_date')

class JobPlacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPlacement
        fields = '__all__'
        read_only_fields = ('student_profile',)

class VolunteerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volunteer
        fields = '__all__'

class WaitlistEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitlistEntry
        fields = '__all__'
        read_only_fields = ('date_applied',)

