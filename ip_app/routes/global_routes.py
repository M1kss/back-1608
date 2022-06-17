from functools import wraps

from flask_restx import Resource, inputs
from werkzeug.datastructures import FileStorage

from ip_app import api, check_last_seen, add_progress_percent, get_chat_items_by_chat_id, ImageLoader, FlaskAdapter
from ip_app.models import User, CourseApplication, Course
from flask import request, g
from ip_app.constants import roles
from ip_app.service import services
from ip_app.serializers.serializers import user_model_with_token, user_model_base, credentials_model, \
    user_model_with_credentials, payment_link_model, cart_model, course_landing_model, \
    available_course_model, available_course_with_video_model, course_full_model, course_post_model, \
    contacts_info_model, legal_info_model, statistics_model, course_application_model, first_step_registration_model, \
    user_model_patch, course_patch_model, video_progress_model, chat_line_model, chat_with_teacher_read_model, \
    chat_teacher_model, user_model_with_course, chat_thread_model, teacher_model_with_courses_count, \
    teacher_model_with_courses, notifications_model
from ip_app.utils import PaginationMixin

aut_nsp = api.namespace('Authentication', path='/auth', description='Operations related to authentication')
usr_nsp = api.namespace('Users', path='/users', description='Operations related to user accounts')
crs_nsp = api.namespace('Courses', path='/courses', description='Operations related to courses')
vds_nsp = api.namespace('Videos', path='/videos', description='Operations related to videos')
cht_nsp = api.namespace('Homework', path='/chat', description='Operations related to homework')
pmt_nsp = api.namespace('Payments', path='/payments', description='Operations related to payments')
stc_nsp = api.namespace('Statistics', path='/statistics',
                        description='Operations related to sales and users statistics')
otr_nsp = api.namespace('Other', path='/other', description='Other operations')

pagination_parser = api.parser()
pagination_parser.add_argument('page', type=inputs.positive, help='Page number', default=1, location='args')
pagination_parser.add_argument('size', type=inputs.natural, help='Items per page or 0 for all items', default=0, location='args')
pagination_parser.add_argument('offset', type=inputs.natural, help='Skip first N items', default=0, location='args')


def role_required(role_id=len(roles) - 1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                g.current_user = user = services.get_user(get_token(), 'token')
                if user is None:
                    raise ValueError
                current_role = user.role
                if not check_last_seen(user):
                    api.abort(410, 'token expired')
            except:
                api.abort(401, 'invalid token')

            services.update_last_seen(user)
            current_role_index = roles.index(current_role)
            if current_role_index > role_id:
                api.abort(403, 'Access denied')

            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_token():
    parsed_words = request.headers.get('Authorization', '').split()
    if len(parsed_words) != 2 or parsed_words[0] != 'Bearer':
        return None
    return parsed_words[1]


def build_parser(schema):
    parser = api.parser()
    for prop, conf in schema.__schema__.get('properties', {}).items():
        conf_type = conf.get('type')
        if conf_type == 'string' and conf.get('format') == 'date-time':
            parser.add_argument(prop, type=inputs.datetime_from_iso8601)
        elif conf_type == 'integer':
            parser.add_argument(prop, type=int)
        elif conf_type == 'boolean':
            parser.add_argument(prop, type=bool, default=False)
        elif conf_type == 'array':
            parser.add_argument(prop, default=list, action='append')
        else:
            parser.add_argument(prop)
    return parser


@aut_nsp.route('')
class PwdAuth(Resource):
    """
    Authorization via login and password
    """

    @api.response(403, 'Invalid credentials')
    @api.marshal_with(user_model_with_token)
    @api.expect(credentials_model)
    @api.doc(security=None)
    def post(self):
        """
        Authorization via login and password
        """
        ok, user = services.check_credentials(request.get_json())
        if ok:
            if not check_last_seen(user):
                services.update_user_token(user)
            services.update_last_seen(user)
            return user
        else:
            api.abort(403, 'Invalid credentials')


users_parser = pagination_parser.copy()


# TODO add table type to parser
@usr_nsp.route('')
class UserCollection(Resource, PaginationMixin):
    """
    Multiple users info
    """
    BaseEntity = User

    @api.marshal_list_with(user_model_base)
    @api.expect(users_parser)
    @api.response(403, 'Access denied')
    @role_required(1)
    def get(self):
        """
        Get multiple users
        """
        return self.paginate(users_parser.parse_args(),
                             query=services.get_multiple_users_query_for_current_user(g.current_user))


@usr_nsp.route('/active')
class ActiveUserCollection(Resource, PaginationMixin):
    """
    Multiple active users info
    """
    BaseEntity = User

    @api.marshal_list_with(user_model_with_course)
    @api.expect(users_parser)
    @api.response(403, 'Access denied')
    @role_required(1)
    def get(self):
        """
        Get multiple users with active course
        """
        return services.add_field_to_obj(
            self.paginate(users_parser.parse_args(),
                          query=services.get_multiple_users_with_course_for_current_user()),
            'course')


teachers_parser = pagination_parser.copy()
teachers_parser.add_argument('courses', help='Comma separated course ids', default=None, location='args')


@usr_nsp.route('/teachers')
class TeacherCollection(Resource, PaginationMixin):
    """
    Multiple teachers info
    """
    BaseEntity = User

    @api.marshal_list_with(teacher_model_with_courses_count)
    @api.expect(users_parser)
    @api.response(403, 'Access denied')
    @role_required(1)
    def get(self):
        """
        Get multiple users with active course
        """
        args = teachers_parser.parse_args()
        course_ids = args.pop('courses', None)
        if course_ids is not None:
            course_ids = course_ids.split(',')
        return services.add_field_to_obj(
            self.paginate(args,
                          query=services.get_multiple_teachers_with_courses(
                              course_ids)),
            'courses_count')


@usr_nsp.route('/teachers/<int:teacher_id>')
class TeacherInfoItem(Resource, PaginationMixin):
    """
    Single teacher info
    """
    BaseEntity = User

    @api.marshal_with(teacher_model_with_courses)
    @api.response(403, 'Access denied')
    @api.response(404, 'No teacher found')
    @role_required(1)
    def get(self, teacher_id):
        """
        Get multiple users with active course
        """
        ok, teacher = services.get_teacher_with_courses(teacher_id, g.current_user)
        if not ok:
            code, response = teacher
            api.abort(code, response)
        else:
            return teacher


applications_parser = pagination_parser.copy()


@usr_nsp.route('/application')
class CourseApplicationCollection(Resource, PaginationMixin):
    """
    Course applications
    """
    BaseEntity = CourseApplication

    @api.expect(course_application_model)
    @api.marshal_with(course_application_model)
    @api.doc(security=None)
    def post(self):
        """
        Apply to a course
        """
        data = request.get_json()
        return services.add_course_application(data)

    @api.marshal_list_with(course_application_model)
    @api.expect(applications_parser)
    @api.response(403, 'Access denied')
    @role_required(1)
    def get(self):
        """
        Get course applications
        """
        args = applications_parser.parse_args()
        result = self.paginate(args,
                               default_order_clauses=(CourseApplication.application_date.desc(),),
                               extra_filters=services.get_course_applications_filters(g.current_user))
        return result


@usr_nsp.route('/application/<int:app_id>')
class CourseApplicationItem(Resource):
    """
    Course application
    """

    @api.response(403, 'Access denied')
    @role_required(0)
    def delete(self, app_id):
        """
        Delete a course application
        """
        services.delete_course_application(app_id)
        return 200, {}


@usr_nsp.route('/<int:user_id>')
class UserItem(Resource):
    """
    User
    """

    @api.marshal_with(user_model_base)
    @api.expect(user_model_patch)
    @api.response(403, 'Access denied')
    @api.response(404, 'User not found')
    @role_required(0)
    def patch(self, user_id):
        """
        Edit optional user profile fields of another_user
        """
        return services.patch_user(user_id, request.get_json())

    @api.marshal_with(user_model_base)
    @api.response(403, 'Access denied')
    @api.response(404, 'User not found')
    @role_required(0)
    def delete(self, user_id):
        """
        Delete any user
        """
        services.delete_user(user_id)
        return 200, {}


@usr_nsp.route('/registration_init')
class RegistrationInit(Resource):
    """
    First stage of user registration
    """

    @api.expect(first_step_registration_model)
    @api.response(409, 'Email is used')
    def post(self):
        ok, reg_hash = services.create_registration_hash_and_send_email(request.get_json())
        if not ok:
            api.abort(409, 'Email is used')
        return {
            'hash': reg_hash
        }


registration_user_parser = api.parser()
registration_user_parser.add_argument('hash', help='Unique registration user hash')


# TODO API for sending email with hash


@usr_nsp.route('/check')
class CheckUser(Resource):
    """
    Check user registration hash
    """

    @api.expect(registration_user_parser)
    @api.marshal_with(first_step_registration_model)
    @api.response(404, 'No user found')
    @api.doc(security=None)
    def get(self):
        status, user = services.get_registration_user_by_hash(registration_user_parser.parse_args()['hash'])
        if not status:
            api.abort(404, 'No user found')
        return user


@usr_nsp.route('/current')
class CurrentUser(Resource):
    """
    Current user info
    """

    @api.marshal_with(user_model_base)
    @role_required()
    def get(self):
        """
        Get current user info
        """
        return g.current_user

    @api.marshal_with(user_model_base)
    @api.expect(user_model_with_credentials)
    @api.response(409, 'User already exists')
    @api.response(404, 'No user found')
    @api.doc(security=None)
    def post(self):
        """
        Register new user (second step)
        """
        ok, user = services.register_user(request.get_json())
        if not ok:
            if user == 'Exists':
                api.abort(409, 'User already exists')
            else:
                api.abort(404, 'No user found')
        return user

    @api.marshal_with(user_model_base)
    @api.expect(user_model_base)
    @role_required()
    def patch(self):
        """
        Edit optional user profile fields
        """
        return services.patch_user(g.current_user.user_id, request.get_json())

    @role_required()
    def delete(self):
        """
        Delete current user
        """
        services.delete_user(g.current_user.user_id)
        return 200, {}


course_pic_parser = api.parser()
course_pic_parser.add_argument('course_pic', location='files', type=FileStorage)

@crs_nsp.route('')
class CourseCollection(Resource, PaginationMixin):
    """
    All courses info
    """
    BaseEntity = Course

    @api.marshal_list_with(course_landing_model)
    @api.expect(pagination_parser)
    @api.response(403, 'Access denied')
    @role_required()
    def get(self):
        """
        Get multiple courses
        """
        return self.paginate(pagination_parser.parse_args())

    @api.expect(course_pic_parser, course_post_model)
    @api.marshal_with(course_full_model)
    @api.response(403, 'Access denied')
    @api.response(404, 'Author not found')
    @api.response(400, 'Author can not be a student')
    @role_required(0)
    def post(self):
        """
        Create a new course
        """
        image_path = ImageLoader.upload(FlaskAdapter(request), "/course_avatars/", options={
            'fieldname': 'course_pic'
        })
        data = request.get_json()
        data['course_pic_url'] = image_path
        course, code, reason = services.create_new_course(data)
        if course is None:
            api.abort(code, reason)
        return course


@crs_nsp.route('/<int:course_id>')
class CourseItem(Resource):
    """
    Information about a single course
    """

    @api.marshal_with(course_landing_model)
    @api.response(404, 'Course does not exist')
    @api.doc(security=None)
    def get(self, course_id):
        """
        Get course by id
        """
        return services.get_course_by_id(course_id)

    @api.expect(course_pic_parser, course_patch_model)
    @api.marshal_with(course_full_model)
    @api.response(403, 'Access denied')
    @api.response(404, 'Course does not exist')
    @api.response(400, 'Incorrect video id for course')
    @role_required(0)
    def patch(self, course_id):
        """
        Edit an existing course by id
        """
        course, code, reason = services.patch_course(course_id, request.get_json())
        if course is None:
            api.abort(code, reason)
        return course

    @api.response(403, 'Access denied')
    @api.response(404, 'Course does not exist')
    @role_required(0)
    def delete(self, course_id):
        """
        Delete an existing course
        """
        services.delete_course(course_id)
        return 200, {}


@crs_nsp.route('/full/<int:course_id>')
class FullCourseItem(Resource):
    """
    Complete information about a single course
    """

    @api.marshal_with(course_full_model)
    @api.response(403, 'Access denied')
    @api.response(404, 'Course does not exist')
    @role_required(0)
    def get(self, course_id):
        """
        Get course by id (full info)
        """
        return services.get_course_by_id(course_id)


@crs_nsp.route('/available')
class AvailableCourseCollection(Resource, PaginationMixin):
    """
    Get courses available to the current user
    """
    BaseEntity = Course

    @api.marshal_list_with(available_course_model)
    @api.expect(pagination_parser)
    @role_required()
    def get(self):
        """
        Get courses available to the current user
        """
        # TODO: sorting b
        return add_progress_percent(self.paginate(pagination_parser.parse_args(),
                                                  query=services.get_available_courses_as_query_for_student(
                                                      g.current_user)))


@crs_nsp.route('/available/<int:course_id>')
class AvailableCourseItem(Resource):
    """
    Courses available to the current user
    """

    @api.marshal_with(available_course_with_video_model)
    @api.response(403, 'Access denied')
    @api.response(404, 'Course does not exist')
    @role_required()
    def get(self, course_id):
        """
        Get a course, if available to the current user
        """
        ok, course = services.get_course_by_id_if_available(course_id, g.current_user)
        if not ok:
            api.abort(403, 'Access denied')
        else:
            return course


@cht_nsp.route('')
class ChatsCollection(Resource):
    @role_required()
    @api.marshal_list_with(chat_with_teacher_read_model)
    def get(self):
        """
        Get chats for user
        """
        return services.get_chats_for_student(g.current_user)

    @api.expect(chat_line_model)
    @api.response(404, 'Chat thread not found')
    @api.response(403, 'Access denied')
    @api.marshal_with(chat_thread_model)
    @role_required()
    def post(self):
        """
        Send message
        """
        ok, message = services.add_chat_line(g.current_user,
                                             request.get_json())
        if not ok:
            status, reason = message
            api.abort(status, reason)
        return message


@cht_nsp.route('/<int:chat_id>')
class ChatItem(Resource):
    @role_required()
    @api.marshal_list_with(chat_thread_model)
    @api.response(404, 'Chat not found')
    @api.response(403, 'Access denied')
    def get(self, chat_id):
        """
        Get chat threads by chat_id
        """
        ok, chat_items = get_chat_items_by_chat_id(g.current_user, chat_id, 'STUDENT')
        if not ok:
            status, response = chat_items
            api.abort(status, response)
        return chat_items


@cht_nsp.route('/teacher')
class ChatsTeacherCollection(Resource):
    @role_required(1)
    @api.marshal_list_with(chat_teacher_model)
    def get(self):
        """
        Get chats for teacher
        """
        return services.get_chats_for_teacher(g.current_user)


@cht_nsp.route('/teacher/<int:chat_id>')
class ChatTeacherItem(Resource):
    @role_required(1)
    @api.marshal_list_with(chat_thread_model)
    @api.response(404, 'Chat not found')
    @api.response(403, 'Access denied')
    def get(self, chat_id):
        """
        Get chat threads by chat_id for teacher
        """
        ok, chat_items = get_chat_items_by_chat_id(g.current_user, chat_id, 'TEACHER')
        if not ok:
            status, response = chat_items
            api.abort(status, response)
        return chat_items


@cht_nsp.route('/notifications')
class ChatsNotificationsCollection(Resource):
    @role_required()
    @api.marshal_list_with(notifications_model)
    def get(self):
        """
        Get all notifications
        """
        return services.get_notifications()

    @role_required(0)
    @api.marshal_with(notifications_model)
    @api.expect(notifications_model)
    @api.response(403, 'Access denied')
    def post(self):
        """
        Post new notification
        """
        return services.post_notification(request.get_json())


@cht_nsp.route('/notifications/<int:not_id>')
class ChatsNotificationsCollection(Resource):
    @role_required(0)
    @api.expect(notifications_model)
    @api.marshal_with(notifications_model)
    @api.response(404, 'Notification does not exist')
    @api.response(403, 'Access denied')
    def patch(self, not_id):
        """
        Patch notification
        """
        return services.patch_notification(not_id, request.get_json())

    @role_required(0)
    @api.response(404, 'Notification does not exist')
    @api.response(403, 'Access denied')
    def delete(self, not_id):
        """
        Delete notification
        """
        return services.delete_notification(not_id)


@pmt_nsp.route('')
class CardPayment(Resource):
    @api.expect(cart_model)
    @api.response(404, 'Product(s) not found')
    @api.response(503, 'Payment operational error')
    @api.response(403, 'Access denied')
    @api.response(400, 'Cart is empty')
    @api.marshal_with(payment_link_model)
    @role_required()
    def post(self):
        """
        Create a new payment (order)
        """
        ok, order = services.create_order(g.current_user, request.get_json())
        if not ok:
            status, reason = order
            api.abort(status, reason)
        return order


@pmt_nsp.route('/callback/<int:order_id>')
class PaymentCallback(Resource):
    @api.response(404, 'Order not found')
    @api.doc(security=None)
    def get(self, order_id):
        """
        Payment Callback
        """
        ok, response = services.grant_access_for_payed_order(order_id)
        if not ok:
            status, reason = response
            api.abort(status, reason)
        return response


@vds_nsp.route('/callback')
class PaymentCallback(Resource):
    @api.response(404, 'Video not found')
    @api.marshal_with(video_progress_model)
    @api.expect(video_progress_model)
    @role_required()
    def post(self):
        """
        Post video tracking info
        """
        video_progress = services.update_video_progress(g.current_user, request.get_json())
        return video_progress


class ContactsInfo(Resource):
    """
    Data for contacts info
    """

    @api.marshal_with(contacts_info_model)
    @api.doc(security=None)
    def get(self):
        """
        Get data for contacts info
        """
        return {}

    @api.marshal_with(contacts_info_model)
    @api.expect(contacts_info_model)
    @api.response(403, 'Access denied')
    @role_required(0)
    def patch(self):
        """
        Edit data for contacts info
        """
        return {}


@otr_nsp.route('/legal')
class LegalInfo(Resource):
    """
    Legal info
    """

    @api.marshal_with(legal_info_model)
    @api.doc(security=None)
    def get(self):
        """
        Get legal info
        """
        return {}

    @api.marshal_with(legal_info_model)
    @api.expect(legal_info_model)
    @api.response(403, 'Access denied')
    @role_required(0)
    def patch(self):
        """
        Edit legal info
        """
        return {}


@stc_nsp.route('')
class Statistics(Resource):
    """
    Sales and users statistics
    """

    @api.marshal_with(statistics_model)
    @api.response(403, 'Access denied')
    @role_required(0)
    def get(self):
        """
        Get sales statistics
        """
        return services.get_statistics()
