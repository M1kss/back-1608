import re


# def represent(self):
#     return 'Not a valid EMAIL'

roles = ('ADMIN', 'TEACHER', 'STUDENT')
user_statuses = ('REGISTERED', 'ACTIVE', 'ARCHIVED')
course_statuses = ('PURCHASED', 'IN_PROGRESS', 'COMPLETED')
video_statuses = ('AVAILABLE', 'IN_PROGRESS', 'COMPLETED')
EMAIL_REGEX = r'\S+@\S+\.\S+'
PHONE_REGEX = r'^[0-9]{10}$'
