import re

roles = ('ADMIN', 'TEACHER', 'STUDENT')
user_statuses = ('REGISTERED', 'ACTIVE', 'ARCHIVED')
course_statuses = ('PURCHASED', 'IN_PROGRESS', 'COMPLETED')
video_statuses = ('AVAILABLE', 'IN_PROGRESS', 'COMPLETED')
EMAIL_REGEX = re.compile(r'\S+@\S+\.\S+')
PHONE_REGEX = re.compile(r'^[0-9]{10}$')