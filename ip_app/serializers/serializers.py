from flask_restplus import fields
from ip_app import api
from ip_app.constants import roles, user_statuses, course_statuses, video_statuses, EMAIL_REGEX, PHONE_REGEX, \
    sex_choices, hw_statuses, sender_choices


class Email(fields.String):
    """
    Email string
    """
    __schema_type__ = 'string'
    __schema_format__ = 'email'
    __schema_example__ = 'email@domain.com'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pattern = EMAIL_REGEX


class PhoneNumber(fields.String):
    """
    Phone number string
    """
    __schema_type__ = 'string'
    __schema_format__ = 'phone'
    __schema_example__ = '9998887766'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pattern = PHONE_REGEX


credentials_template = {
    'email': Email(reqired=True),
    'password': fields.String(required=True, min_length=6),
}

credentials_model = api.model('User credentials', credentials_template)

short_user_model = api.model('User minimal model', {
    'user_id': fields.Integer(min=1, readonly=True),
    'name': fields.String(min_length=1),
    'last_name': fields.String(min_length=1),
    'profile_pic_url': fields.String,
})

first_step_registration_model = api.model('Check user model', {
    'hash': fields.String(readonly=True),
    'email': Email(required=True),
    'phone': PhoneNumber,
    'name': fields.String(min_length=1),
    'last_name': fields.String(min_length=1),
})

user_model_base = api.clone('User model base', short_user_model, {
    'email': Email(readonly=True),
    'phone': PhoneNumber,
    'city': fields.String,
    'role': fields.String(enum=roles, readonly=True),
    'status': fields.String(enum=user_statuses, readonly=True),
    'registration_date': fields.DateTime(readonly=True),
    'last_seen': fields.DateTime(readonly=True),
    'birth_date': fields.Date,
    'sex': fields.String(enum=sex_choices)
})


user_model_patch = api.clone('User model for patch', short_user_model, {
    'phone': PhoneNumber,
    'city': fields.String,
    'role': fields.String(enum=roles),
})


user_model_with_token = api.clone('User model with token', user_model_base, {
    'token': fields.String,
})

user_model_with_credentials = api.clone('Registration model', user_model_base, {
    'password': fields.String(required=True, min_length=6),
    'hash': fields.String(required=True)
    })

course_base_model = api.model('Course base model', {
    'course_id': fields.Integer(min=1, readonly=True),
    'title': fields.String,
    'description': fields.String,
    'course_pic_url': fields.String,
    'author_name': fields.String,

})

user_model_with_course = api.clone('User model with course', user_model_base, {
    'course': fields.Nested(course_base_model)
})

teacher_model_with_courses_count = api.clone('Teacher model with courses', user_model_base, {
    'courses_count': fields.Integer
})

teacher_model_with_courses = api.clone('Teacher model with courses', user_model_base, {
    'courses': fields.List(fields.Nested(course_base_model), attribute='taught_courses')
})

progress_percent_dict = {'progress_percent': fields.Integer(readonly=True)}

available_course_model = api.clone('Avalilable course model', course_base_model, progress_percent_dict)

q_and_a_model = api.model('Q&A model', {
    'question': fields.String,
    'answer': fields.String,
})

video_base_model = api.model('Base video model', {
    'title': fields.String,
    'description': fields.String,
    'duration': fields.Integer(description='duration in seconds'),
    'q_and_a': fields.List(fields.Nested(q_and_a_model)),
})

video_model = api.clone('Video model', video_base_model, {
    'video_id': fields.Integer(min=1, readonly=True),
    'title': fields.String(required=True),
    'url': fields.String(required=True),
})


homework_model = api.model('HW model', {
    'video_homework_id': fields.Integer(readonly=True),
    'video_id': fields.Integer(readonly=True),
    'homework_message': fields.String
})


video_admin_model = api.clone('Video admin model', video_model, {
    'homework': fields.Nested(homework_model)
})

patch_video_model = api.clone('Video model with id', video_admin_model, {
    'video_id': fields.Integer(min=1, required=True),
    'url': fields.String,
    'title': fields.String,
})

course_progress_model = api.model(
    'Course progress', progress_percent_dict
)
video_progress_model = api.model('Video progress', {
    'video_progress_id': fields.Integer(readonly=True),
    'video_id': fields.Integer(required=True),
    'progress_percent': fields.Integer(required=True),
    'course_progress': fields.Nested(course_progress_model,
                                     readonly=True)
})

video_with_progress_model = api.clone('Video model with progress', video_model, progress_percent_dict)

available_course_with_video_model = api.clone('Course model with videos', course_base_model, {
    'available_videos': fields.List(fields.Nested(video_with_progress_model)),
    'video_count': fields.Integer,
})

discount_model = api.model('Discount model', {
    'discount': fields.Float,
    'discount_type': fields.String(enum=('P', 'R'), default='P'),
})

course_product_model = api.clone('Course product model', discount_model, {
    'course_product_id': fields.Integer(min=1, readonly=True),
    'title': fields.String(required=True),
    'description': fields.String,
    'duration': fields.String,
    'price': fields.Integer(required=True),
})

service_product_model = api.clone('Service product model', discount_model, {
    'service_product_id': fields.Integer(min=1, readonly=True),
    'title': fields.String(required=True),
    'description': fields.String,
    'price': fields.Integer(required=True),
})

course_for_model = api.model('Course for (landing) model', {
    'img_src': fields.String,
    'title': fields.String,
    'subtitle': fields.String,
})

text_model = api.model('Custom text field (landing) model', {
    'text': fields.String,
})

program_model = api.model('Course program model (landing)', {
    'title': fields.String,
    'subtitles_list': fields.List(fields.Nested(text_model))
})

landing_info_model = api.model('Landing info model', {
    'main_img_src': fields.String,
    'title': fields.String,
    'name_of_teacher': fields.String,
    'subtitle': fields.String,
    'duration': fields.String,
    'online': fields.String,
    'education': fields.String,
    'efficiency': fields.String,
    'count_company': fields.String,
    'subtitle_company': fields.String,
    'count_rubles': fields.String,
    'subtitle_rubles': fields.String,
    'course_for': fields.List(fields.Nested(course_for_model), min_items=3, max_items=3),
    'what_you_learn': fields.List(fields.Nested(text_model)),
    'program': fields.Nested(program_model),
    'cv_position': fields.String,
    'cv_payment': fields.String,
    'skills_list': fields.List(fields.Nested(text_model)),
})

course_landing_model = api.clone('Course landing model', course_base_model, {
    'landing_info': fields.Nested(landing_info_model),
    'course_products': fields.List(fields.Nested(course_product_model)),
    'service_products': fields.List(fields.Nested(service_product_model)),
})

course_full_model = api.clone('Course admin model', course_landing_model, {
    'videos': fields.List(fields.Nested(video_admin_model)),
    'teacher_ids': fields.List(fields.Integer, min_items=1,
                               attribute='teachers.user_id')
})
course_post_model = api.model('Course post model', {
    'title': fields.String(required=True),
    'description': fields.String,
    'course_pic_url': fields.String,
    'author_name': fields.String(required=True),
    'teacher_ids': fields.List(fields.Integer, required=True, min_items=1),
    'landing_info': fields.Nested(landing_info_model, required=True),
    'course_products': fields.List(fields.Nested(course_product_model), required=True, min_items=1),
    'service_products': fields.List(fields.Nested(service_product_model), default=[]),
    'videos': fields.List(fields.Nested(video_admin_model), default=[])
})


course_patch_model = api.clone('Course patch model', course_post_model, {
    'title': fields.String,
    'teacher_ids': fields.List(fields.Integer, min_items=1),
    'author_name': fields.String,
    'landing_info': fields.Nested(landing_info_model),
    'videos': fields.List(fields.Nested(patch_video_model), default=[]),
    'course_products': fields.List(fields.Nested(course_product_model), min_items=1),
})

payment_link_model = api.model('Payment link model', {
    'order_id': fields.Integer(min=1, readonly=True),
    'payment_link': fields.String,
})

cart_model = api.model('Order cart', {
    'promocode': fields.String,
    'course_product_ids': fields.List(fields.Integer(min=1), default=[]),
    'service_product_ids': fields.List(fields.Integer(min=1), default=[]),
})

contacts_info_model = api.model('Contacts info', {
    'phone_number': PhoneNumber,
    'whatsapp': fields.String,
    'telegram': fields.String,
    'email_general': Email,
    'email_sales': Email,
})

legal_info_model = api.model('Legal info', {
    'terms_of_service': fields.String,
    'confidentiality': fields.String,
    'copyright': fields.String,
    'all_rights_reserved': fields.String,
    'data_processing_consent': fields.String,
})

statistics_model = api.model('Statistics', {
    'registered_students': fields.Integer,
    'pending_applications': fields.Integer,
    'studying': fields.Integer,
    'teachers': fields.Integer,
})

course_application_model = api.model('Course application', {
    'application_id': fields.Integer(min=1, readonly=True),
    'name': fields.String(min_length=1, required=True),
    'email': Email(required=True),
    'phone': PhoneNumber(required=True),
    'application_date': fields.DateTime(readonly=True),
    'course_id': fields.Integer(required=True),
    'is_registered': fields.Boolean(readonly=True),
    'course': fields.Nested(course_base_model, readonly=True)
})


chat_line_model = api.model('Chat line', {
    'chat_line_id': fields.Integer(readonly=True),
    'message': fields.String,
    'message_date': fields.DateTime(readonly=True),
    'sender': fields.String(enum=sender_choices, required=True),
    'chat_thread_id': fields.Integer(required=True),
    'is_read': fields.Boolean(readonly=True),
})


chat_line_sent_model = api.clone('Chat sent line', chat_line_model, {
    'hw_status': fields.String(enum=hw_statuses[2:])
})


chat_base_model = api.model('Chat base model', {
    'chat_id': fields.Integer,
    'last_message_date': fields.DateTime,
})


chat_with_teacher_read_model = api.clone('Chat model with teacher', chat_base_model, {
    'course': fields.Nested(course_base_model),
    'student_read': fields.Boolean,
})

chat_with_student_model = api.clone('Chat model with student', chat_base_model, {
    'student': fields.Nested(short_user_model),
    'teacher_read': fields.Boolean
})
chat_teacher_model = api.model('Chat teacher model', {
    'course': fields.Nested(course_base_model),
    'chats': fields.List(fields.Nested(chat_with_student_model))
})

chat_thread_model = api.model('Chat thread model', {
    'chat_thread_id': fields.Integer,
    'chat_lines': fields.List(fields.Nested(chat_line_model)),
    'hw_status': fields.String(enum=hw_statuses),
    'video': fields.Nested(video_base_model)
})
