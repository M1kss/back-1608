from uuid import uuid4

from ip_app import session, db
from ip_app.models import User, CourseApplication, Course, Access, Video, CourseProduct, ServiceProduct, UserRegistration


def get_user(value, by='id'):
    if by == 'id':
        return User.query.get_or_404(value)
    elif by == 'email':
        return User.query.filter_by(email=value).one_or_none()
    elif by == 'token':
        return User.query.filter_by(token=value).one_or_none()
    else:
        raise ValueError


def get_hash(password):
    # FIXME
    return password


def get_registration_user_by_hash(user_hash):
    user_reg = UserRegistration.query.filter_by(hash=user_hash).one_or_none()
    return (True, user_reg) if user_reg else (False, {})


def check_credentials(data):
    user = get_user(data['email'], by='email')
    if user is None:
        return False, {}
    if user.password_hash == get_hash(data['password']):
        return True, user
    else:
        return False, {}


def create_database_item(cls, data, include=None, exclude=tuple()):
    return cls(**{k: v for k, v in data.items() if k not in exclude and (k in include if include is not None else True)})


def register_user(data):
    ok, user_reg = get_registration_user_by_hash(data['hash'])
    if not ok:
        return False, 'No hash'
    if get_user(data['email'], by='email'):
        return False, 'Exists'
    for attr in ('name', 'last_name', 'phone', 'email'):
        if attr not in data or data[attr] is None:
            data[attr] = getattr(user_reg, attr)
    user = create_database_item(User, data, exclude=('password', ))
    user.password_hash = get_hash(data['password'])
    session.add(user)
    session.commit()

    session.delete(user_reg)
    session.commit()
    return True, user


def get_course_applications_filters(args):
    return ()


def generate_token():
    return str(uuid4())


def update_last_seen(user):
    user.last_seen = db.func.now()
    session.commit()


def update_user_token(user):
    user.token = generate_token()
    session.commit()


def get_users_filters_by_teacher(user):
    # FIXME
    return ()


def get_multiple_users_filters_for_current_user(user):
    if user.role == 'ADMIN':
        return ()
    elif user.role == 'TEACHER':
        return get_users_filters_by_teacher(user)
    else:
        raise AssertionError


def email_exists(email):
    return User.query.filter_by(email=email).one_or_none()


def get_course_applications_by_id(app_id):
    return CourseApplication.query.get_or_404(app_id)


def add_course_application(data):
    application = CourseApplication(**data)
    session.add(application)
    session.commit()
    return application


def delete_course_application(app_id):
    application = get_course_applications_by_id(app_id)
    session.delete(application)
    session.commit()


def get_course_by_id(course_id):
    return Course.query.get_or_404(course_id)


def get_course_ids_available_for_student(user):
    return list(*zip(
        *session.query(Course.course_id.distinct())
            .join(Video, Course.videos)
            .join(Access, Access.video_id == Video.video_id)
            .filter(Access.user_id == user.user_id,
                    Access.begin_date <= db.func.now(),
                    Access.end_date >= db.func.now()).all()
    ))


def get_available_courses_filters_for_student(user):
    return (Course.course_id.in_(get_course_ids_available_for_student(user)), )


def get_available_videos_by_student_and_course(user, course_id):
    return list(*zip(
        *session.query(Video)
            .filter(Video.course_id == course_id)
            .join(Access, Access.video_id == Video.video_id)
            .filter(Access.user_id == user.user_id,
                    Access.begin_date <= db.func.now(),
                    Access.end_date >= db.func.now()).all()
    ))


def get_video_by_id(video_id):
    return Video.query.get_or_404(video_id)


def get_course_by_id_if_available(course_id, user):
    course = get_course_by_id(course_id)
    course.available_videos = get_available_videos_by_student_and_course(user, course_id)
    course.video_count = len(course.videos)
    if course.available_videos:
        return True, course
    else:
        return False, {}


def delete_course(course_id):
    course = get_course_by_id(course_id)
    session.delete(course)
    session.commit()


def create_new_course(data):
    videos = data.pop('videos')
    course_products = data.pop('course_products')
    service_products = data.pop('service_products')

    author = get_user(data['author_id'])
    if author.role == 'STUDENT':
        return None, 400, 'Author can not be a student'

    course = Course(**data,
                    course_products=[CourseProduct(**course_product_data) for course_product_data in course_products],
                    service_products=[ServiceProduct(**service_product_data) for service_product_data in service_products],
                    videos=[Video(**video_data) for video_data in videos])
    session.add(course)
    session.commit()

    return course, 200, None


def patch_course(course_id, data):
    course = get_course_by_id(course_id)
    videos = data.pop('videos')
    if 'author_id' in data:
        author = get_user(data['author_id'])
        if author.role == 'STUDENT':
            return None, 400, 'Author can not be a student'
    for field, value in data.items():
        setattr(course, field, value)

    for video_data in videos:
        video = get_video_by_id(video_data.pop('video_id'))
        if video.course_id != course.course_id:
            return None, 400, 'Incorrect video id for course'
        for field, value in video_data.items():
            setattr(video, field, value)

    session.commit()

    return course, 200, None


def create_registration_hash_and_send_email(data):
    if UserRegistration.query.get(data['email']):
        return False, ''
    user_reg = create_database_item(UserRegistration, data)
    user_reg.hash = generate_token()
    session.add(user_reg)
    session.commit()
    # TODO: send email
    return True, user_reg.hash
