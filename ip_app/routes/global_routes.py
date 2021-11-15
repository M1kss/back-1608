from datetime import datetime
from functools import wraps

from flask_restplus import Resource, inputs
from ip_app import api, check_last_seen, add_progress_percent
from ip_app.models import User, CourseApplication, Course
from flask import request, g
from ip_app.constants import roles
from ip_app.service import services
from ip_app.serializers.serializers import user_model_with_token, user_model_base, credentials_model, \
    user_model_with_credentials, course_base_model, payment_link_model, cart_model, course_landing_model, \
    available_course_model, available_course_with_video_model, course_full_model, course_post_model, \
    contacts_info_model, legal_info_model, statistics_model, course_application_model, first_step_registration_model, \
    user_model_patch, course_patch_model, video_progress_model
from ip_app.utils import PaginationMixin

aut_nsp = api.namespace('Authentication', path='/auth', description='Operations related to authentication')
usr_nsp = api.namespace('Users', path='/users', description='Operations related to user accounts')
crs_nsp = api.namespace('Courses', path='/courses', description='Operations related to courses')
vds_nsp = api.namespace('Videos', path='/videos', description='Operations related to videos')
pmt_nsp = api.namespace('Payments', path='/payments', description='Operations related to payments')
stc_nsp = api.namespace('Statistics', path='/statistics',
                        description='Operations related to sales and users statistics')
otr_nsp = api.namespace('Other', path='/other', description='Other operations')

pagination_parser = api.parser()
pagination_parser.add_argument('page', type=inputs.positive, help='Page number', default=1)
pagination_parser.add_argument('size', type=inputs.natural, help='Items per page or 0 for all items', default=0)
pagination_parser.add_argument('offset', type=inputs.natural, help='Skip first N items', default=0)


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
        # TODO Sort users
        return self.paginate(users_parser.parse_args(),
                             default_order_clauses=(User.registration_date.desc(),),
                             extra_filters=services.get_multiple_users_filters_for_current_user(g.current_user))


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
    @role_required(0)
    def get(self):
        """
        Get course applications
        """
        args = applications_parser.parse_args()
        result = self.paginate(args,
                               default_order_clauses=(CourseApplication.application_date.desc(),),
                               extra_filters=services.get_course_applications_filters(args))
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

    @api.expect(course_post_model)
    @api.marshal_with(course_full_model)
    @api.response(403, 'Access denied')
    @api.response(404, 'Author not found')
    @api.response(400, 'Author can not be a student')
    @role_required(0)
    def post(self):
        """
        Create a new course
        """
        course, code, reason = services.create_new_course(request.get_json())
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

    @api.expect(course_patch_model)
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
        # TODO: sorting
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
            return 403, 'Access denied'
        else:
            return course


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
        services.grant_access_for_payed_order(order_id)
        return 200, {}


@vds_nsp.route('/callback')
class PaymentCallback(Resource):
    @api.response(404, 'Video not found')
    @api.marshal_with(video_progress_model)
    @role_required()
    def post(self):
        """
        Post video tracking info
        """
        video_progress = services.update_video_progress(g.curent_user, request.get_json())
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
        return {}
