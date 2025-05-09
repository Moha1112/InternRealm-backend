from datetime import datetime, timedelta
from django.core.exceptions import ValidationError

def validate_future_date(value):
    if value < datetime.now().date():
        raise ValidationError("Date must be in the future")

def validate_salary(data):
    if data.get('is_paid') and not data.get('salary'):
        raise ValidationError("Salary must be provided for paid internships")
    if data.get('salary') and data.get('salary') < 0:
        raise ValidationError("Salary cannot be negative")

def validate_application_status(current_status, new_status):
    valid_transitions = {
        'submitted': ['under_review', 'rejected'],
        'under_review': ['rejected', 'hired'],
        'rejected': [],
        'hired': []
    }
    if new_status not in valid_transitions.get(current_status, []):
        raise ValidationError(f"Invalid status transition from {current_status} to {new_status}")