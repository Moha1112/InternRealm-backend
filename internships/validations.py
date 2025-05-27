from django.core.exceptions import ValidationError
from datetime import datetime, date
from django.utils.dateparse import parse_date

def validate_future_date(value):
    """
    Validate that a date is in the future.
    Accepts either date object or ISO format string (YYYY-MM-DD).
    """
    if isinstance(value, str):
        try:
            value = parse_date(value)
            if value is None:
                raise ValueError("Invalid date format")
        except (ValueError, TypeError):
            raise ValidationError("Invalid date format. Use YYYY-MM-DD")

    if not isinstance(value, date):
        raise ValidationError("Value must be a date")

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