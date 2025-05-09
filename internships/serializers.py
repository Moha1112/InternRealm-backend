from rest_framework import serializers
from .models import Internship, Application, Evaluation

class InternshipSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.company_name')
    
    class Meta:
        model = Internship
        fields = ['id', 'title', 'company_name', 'description', 
                 'requirements', 'duration_months', 'is_paid',
                 'salary', 'location', 'remote_option', 
                 'application_deadline']

class ApplicationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name')
    internship_title = serializers.CharField(source='internship.title')
    cv_data = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ['id', 'internship_title', 'student_name',
                'cover_letter', 'cv_data', 'status', 'applied_at']

    def get_cv_data(self, obj):
        if obj.cv:
            return {
                'title': obj.cv.title,
                'education': obj.cv.education,
                'experience': obj.cv.experience,
                'skills': obj.cv.skills
            }
        return None

class EvaluationSerializer(serializers.ModelSerializer):
    evaluator_name = serializers.CharField(source='evaluator.get_full_name', read_only=True)
    interview_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Evaluation
        fields = [
            'id',
            'interview',
            'interview_details',
            'evaluator',
            'evaluator_name',
            'technical_skills',
            'problem_solving',
            'communication',
            'cultural_fit',
            'overall_score',
            'recommendation',
            'strengths',
            'areas_for_improvement',
            'additional_comments',
            'submitted_at'
        ]
        read_only_fields = ['evaluator', 'overall_score', 'submitted_at']
    
    def get_interview_details(self, obj):
        return {
            'type': obj.interview.get_interview_type_display(),
            'date': obj.interview.start_time.date().isoformat(),
            'application_id': obj.interview.application.id,
            'student_name': obj.interview.application.student.get_full_name()
        }
    
    def validate(self, data):
        # Ensure evaluator can only evaluate their own interviews
        if 'evaluator' in self.context and self.context['evaluator'] != self.instance.evaluator:
            raise serializers.ValidationError("You can only evaluate interviews you conducted")
        return data