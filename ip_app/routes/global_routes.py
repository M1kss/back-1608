from functools import wraps

from flask_restplus import Resource, inputs
from ip_app import api
from ip_app.models import User, CourseApplication, Course
from flask import request, g
from ip_app.constants import roles
from ip_app.service import services
from ip_app.serializers.serializers import user_model_with_token, user_model_base, credentials_model, \
    user_model_with_credentials, course_base_model, payment_link_model, cart_model, course_landing_model, \
    available_course_model, available_course_with_video_model, course_full_model, course_post_model, \
    contacts_info_model, legal_info_model, statistics_model, course_application_model
from ip_app.utils import PaginationMixin

aut_nsp = api.namespace('Authentication', path='/auth', description='Operations related to authentication')
usr_nsp = api.namespace('Users', path='/users', description='Operations related to user accounts')
crs_nsp = api.namespace('Courses', path='/courses', description='Operations related to courses')
pmt_nsp = api.namespace('Payments', path='/payments', description='Operations related to payments')
stc_nsp = api.namespace('Statistics', path='/statistics', description='Operations related to sales and users statistics')
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
            services.update_last_seen(user)
            services.update_user_token(user)
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
        return self.paginate(users_parser.parse_args(),
                             extra_filters=services.get_multiple_users_filters_for_current_user(g.current_user))


applications_parser = pagination_parser.copy()


@usr_nsp.route('/application')
class CourseApplicationCollection(Resource, PaginationMixin):
    """
    Course applications
    """
    BaseEntity = CourseApplication

    @api.expect(course_application_model)
    @api.response(409, 'User already exists')
    @api.doc(security=None)
    def post(self):
        """
        Apply to a course
        """
        data = request.get_json()
        if services.email_exists(data['email']):
            return 409, 'User already exists'
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
    @api.expect(user_model_base)
    @api.response(403, 'Access denied')
    @api.response(404, 'User not found')
    @role_required(0)
    def patch(self):
        """
        Edit optional user profile fields of another_user
        """
        return 200, {}

    @api.marshal_with(user_model_base)
    @api.response(403, 'Access denied')
    @api.response(404, 'User not found')
    @role_required(0)
    def delete(self):
        """
        Delete any user
        """
        return 200, {}


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
    @api.doc(security=None)
    def post(self):
        """
        Register new user
        """
        ok, user = services.register_user(request.get_json())
        if not ok:
            api.abort(409, 'User already exists')
        return user

    @api.marshal_with(user_model_base)
    @api.expect(user_model_base)
    @role_required()
    def patch(self):
        """
        Edit optional user profile fields
        """
        return g.current_user

    @role_required()
    def delete(self):
        """
        Delete current user
        """
        return 200, {}


@crs_nsp.route('')
class CourseCollection(Resource, PaginationMixin):
    """
    All courses info
    """
    BaseEntity = Course

    @api.marshal_list_with(course_base_model)
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

    @api.expect(course_post_model)
    @api.marshal_with(course_full_model)
    @api.response(403, 'Access denied')
    @api.response(404, 'Course does not exist')
    @api.response(404, 'Items not found')
    @api.response(400, 'Author can not be a student')
    @api.response(400, 'Incorrect video id for course')
    @role_required(0)
    def put(self, course_id):
        """
        Edit an existing course by id
        """
        course, code, reason = services.patch_course(course_id, request.get_json())
        if course is None:
            api.abort(code, reason)
        return {}

    @api.response(403, 'Access denied')
    @api.response(404, 'Course does not exist')
    @role_required(0)
    def delete(self, course_id):
        """
        Delete an existing course
        """
        services.delete_course(course_id)
        return 200, {}


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
        # TODO: return pagination as query and add percent completed, etc.
        return self.paginate(pagination_parser.parse_args(),
                             extra_filters=services.get_available_courses_filters_for_student(g.current_user))


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
        Create a new payment
        """
        return {}


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