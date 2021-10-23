from flask_restplus import fields
from ip_app import api
from ip_app.constants import roles, user_statuses, course_statuses, video_statuses, EMAIL_REGEX, PHONE_REGEX


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
    'author': fields.Nested(short_user_model),
})

available_course_model = api.clone('Avalilable course model', course_base_model, {
    'percent_completed': fields.Integer,
    'status': fields.String(enum=course_statuses),
})

q_and_a_model = api.model('Q&A model', {
    'question': fields.String,
    'answer': fields.String,
})

video_model = api.model('Video model', {
    'video_id': fields.Integer(min=1, readonly=True),
    'title': fields.String(required=True),
    'description': fields.String,
    'url': fields.String(required=True),
    'duration': fields.Integer(description='duration in seconds'),
    'q_and_a': fields.List(fields.Nested(q_and_a_model)),
})

patch_video_model = api.clone('Video model with id', video_model, {
    'video_id': fields.Integer(min=1, required=True),
})

video_with_progress_model = api.clone('Video model with progress', video_model, {
    'percent_completed': fields.Integer(readonly=True),
    'status': fields.String(enum=video_statuses, readonly=True),
})

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
    'videos': fields.List(fields.Nested(video_model))
})

course_patch_model = api.model('Course patch model', {
    'title': fields.String,
    'description': fields.String,
    'course_pic_url': fields.String,
    'author_id': fields.Integer(min=1),
    'landing_info': fields.Nested(landing_info_model),
    'videos': fields.List(fields.Nested(patch_video_model), default=[])
})


course_post_model = api.clone('Course post model', {
    'title': fields.String(required=True),
    'description': fields.String,
    'course_pic_url': fields.String,
    'author_id': fields.Integer(min=1, required=True),
    'landing_info': fields.Nested(landing_info_model, required=True),
    'course_products': fields.List(fields.Nested(course_product_model), required=True, min_items=1),
    'service_products': fields.List(fields.Nested(service_product_model), default=[]),
    'videos': fields.List(fields.Nested(video_model), default=[])
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
    'course_id': fields.Integer(required=True),
})
