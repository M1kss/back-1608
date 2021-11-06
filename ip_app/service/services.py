from uuid import uuid4

from sqlalchemy import or_

from ip_app import session, db
from ip_app.models import User, CourseApplication, Course, Access, Video, CourseProduct, ServiceProduct, \
    UserRegistration, OrderCourseProductItem, OrderServiceProductItem, Order


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
    return cls(
        **{k: v for k, v in data.items() if k not in exclude and (k in include if include is not None else True)})


def register_user(data):
    ok, user_reg = get_registration_user_by_hash(data['hash'])
    if not ok:
        return False, 'No hash'
    for attr in ('name', 'last_name', 'phone', 'email'):
        if attr not in data or data[attr] is None:
            data[attr] = getattr(user_reg, attr)
    user = create_database_item(User, data, exclude=('password', 'hash'))
    user.password_hash = get_hash(data['password'])
    session.add(user)
    session.commit()

    session.delete(user_reg)
    session.commit()
    return True, user


def patch_user(user_id, data):
    user = get_user(user_id)
    for attr, value in data.items():
        setattr(user, attr, value)
    session.commit()
    return user


def delete_user(user_id):
    user = get_user(user_id)
    session.delete(user)
    session.commit()


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
    data['is_registered'] = email_exists(data['email'])
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
                    or_(Access.end_date >= db.func.now(),
                        Access.end_date.is_(None))
                    ).all()
    ))


def get_available_courses_filters_for_student(user):
    return (Course.course_id.in_(get_course_ids_available_for_student(user)),)


def get_available_videos_by_student_and_course(user, course_id):
    return Video.query\
            .filter(Video.course_id == course_id)\
            .join(Access, Access.video_id == Video.video_id)\
            .filter(Access.user_id == user.user_id,
                    Access.begin_date <= db.func.now(),
                    or_(Access.end_date >= db.func.now(),
                        Access.end_date.is_(None))
                    ).all()


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

    course = Course(**data,
                    course_products=[CourseProduct(**course_product_data) for course_product_data in course_products],
                    service_products=[ServiceProduct(**service_product_data) for service_product_data in
                                      service_products],
                    videos=[Video(**video_data) for video_data in videos])
    session.add(course)
    session.commit()

    return course, 200, None


def patch_course(course_id, data):
    course = get_course_by_id(course_id)
    videos = data.pop('videos', [])
    new_landing_info = data.pop('landing_info', None)
    if new_landing_info is not None:
        land_info = {}
        if course.landing_info:
            land_info = dict(course.landing_info)
        land_info.update(new_landing_info)
        course.landing_info = land_info
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
    if UserRegistration.query.get(data['email']) or get_user(data['email'], by='email'):
        return False, ''
    user_reg = create_database_item(UserRegistration, data)
    user_reg.hash = generate_token()
    session.add(user_reg)
    session.commit()
    # TODO: send email
    return True, user_reg.hash


def create_payment_link(order_id):
    # TODO: acquiring
    return 'http://79.98.29.212/api/v1/payments/callback/{}'.format(order_id)


def get_order(order_id):
    return Order.query.get_or_404(order_id)


def get_user_product_ids(user, for_what):
    assert for_what in ('course', 'service')
    product_id = '{}_product_id'.format(for_what)
    product_items = '{}_product_items'.format(for_what)
    return set(
        getattr(product_item, product_id)
        for order in user.orders
        for product_item in getattr(order, product_items)
    )


def check_purchased_course_product_ids(user, course_product_ids):
    return set(course_product_ids) & get_user_product_ids(user, 'course')


def check_purchased_service_product_ids(user, service_product_ids):
    return set(service_product_ids) & get_user_product_ids(user, 'service')


def create_order(user, data):
    course_product_ids = data.pop('course_product_ids', [])
    service_product_ids = data.pop('service_product_ids', [])

    if len(course_product_ids) + len(service_product_ids) == 0:
        return False, (400, 'Cart is empty')

    course_products = [CourseProduct.query.get_or_404(p_id) for p_id in course_product_ids]
    service_products = [ServiceProduct.query.get_or_404(p_id) for p_id in service_product_ids]

    purchased_course_product_ids = check_purchased_course_product_ids(user, course_product_ids)
    purchased_service_product_ids = check_purchased_service_product_ids(user, course_product_ids)
    if len(purchased_course_product_ids) + len(purchased_service_product_ids) != 0:
        return False, (403, 'One or more products already purchased,'
                            'course: {}, service: {}'.format(purchased_course_product_ids,
                                                             purchased_service_product_ids))

    data['course_product_items'] = [OrderCourseProductItem(
        price=pr.price,
        course_product_id=pr.course_product_id
    ) for pr in course_products]
    data['service_product_items'] = [OrderServiceProductItem(
        price=pr.price,
        service_product_id=pr.service_product_id
    ) for pr in service_products]

    data['price'] = sum(pr.price for pr in course_products + service_products)
    data['user_id'] = user.user_id

    order = create_database_item(Order, data)
    session.add(order)
    session.commit()

    try:
        link = create_payment_link(order_id=order.order_id)
    except Exception:
        order.status = 'FAILED'
        session.commit()
        return False, (503, 'Payment operational error')

    order.payment_link = link
    session.commit()
    return True, order


def get_access_items(course_product, user_id): \
        # TODO: begin_date
    course_videos = course_product.course.videos
    return [Access(video_id=video.video_id,
                   user_id=user_id,
                   begin_date=db.func.now()) for video in course_videos
            if not Access.query.filter_by(
                video_id=video.video_id,
                user_id=user_id,
            ).one_or_none()]


def grant_access_for_payed_order(order_id):
    order = get_order(order_id)
    access_items = []
    for course_product_item in order.course_product_items:
        access_items += get_access_items(course_product_item.course_product, order.user_id)

    session.add_all(access_items)
    order.status = 'PAYED'
    session.commit()
