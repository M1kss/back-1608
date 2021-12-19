from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import or_, and_

from ip_app import session, db, ChatLine, Chat, hw_statuses
from ip_app.models import User, CourseApplication, Course, Access, Video, CourseProduct, ServiceProduct, \
    UserRegistration, OrderCourseProductItem, OrderServiceProductItem, Order, VideoProgressTracking, \
    CourseProgressTracking, ChatThread


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
    update_last_seen(user)
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


def check_last_seen(user):
    if user.token is None:
        return False
    time_since_last_seen = datetime.now() - user.last_seen
    if time_since_last_seen.days > 0 or time_since_last_seen.seconds >= 48 * 3600:
        return False
    else:
        return True


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


def get_multiple_users_with_course_for_current_user(user):
    return session.query(User, Course).join(
        Access,
        Access.user_id == User.user_id
    ).filter(
        *get_current_active_filters()
    ).join(
        Video,
        Video.video_id == Access.video_id
    ).join(
        Course,
        Course.course_id == Video.course_id
    ).order_by(User.registration_date.desc(),
               Access.end_date.desc())


def email_exists(email):
    return User.query.filter_by(email=email).one_or_none()


def get_course_applications_by_id(app_id):
    return CourseApplication.query.get_or_404(app_id)


def add_course_application(data):
    data['is_registered'] = True if email_exists(data['email']) else False
    get_course_by_id(data['course_id'])
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


def get_current_active_filters():
    return (Access.begin_date <= db.func.now(),
            or_(
                Access.end_date >= db.func.now(),
                Access.end_date.is_(None)
            ))


def get_course_ids_available_for_student(user):
    return list(*zip(
        *session.query(
            Course.course_id.distinct()
        ).join(
            Video,
            Course.videos
        ).join(
            Access,
            Access.video_id == Video.video_id
        ).filter(
            Access.user_id == user.user_id,
            *get_current_active_filters()
        ).all()
    ))


def get_available_courses_as_query_for_student(user):
    available_course_ids = get_course_ids_available_for_student(user)
    course_track_items = session.query(
        Course, CourseProgressTracking
    ).filter(
        Course.course_id.in_(available_course_ids)
    ).join(
        CourseProgressTracking,
        and_(CourseProgressTracking.course_id == Course.course_id,
             CourseProgressTracking.user_id == user.user_id),
        isouter=True
    )
    return course_track_items


def get_available_videos_by_student_and_course_with_progress(user, course_id):
    return session.query(Video, VideoProgressTracking).filter(
        Video.course_id == course_id
    ).join(
        Access,
        Access.video_id == Video.video_id
    ).filter(
        Access.user_id == user.user_id,
        *get_current_active_filters()
    ).join(
        VideoProgressTracking,
        and_(VideoProgressTracking.video_id == Video.video_id,
             VideoProgressTracking.user_id == user.user_id),
        isouter=True
    ).all()


def get_video_by_id(video_id):
    return Video.query.get_or_404(video_id)


def add_progress_percent(progress_list):
    return [setattr(obj, 'progress_percent', None if obj_progress is None else obj_progress.progress_percent
                    ) or obj
            for obj, obj_progress in progress_list]


def get_course_by_id_if_available(course_id, user):
    course = get_course_by_id(course_id)
    course.available_videos = add_progress_percent(
        get_available_videos_by_student_and_course_with_progress(user, course_id))

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
    teachers = [get_user(user_id) for user_id
                in data.pop('teacher_ids')]
    course = Course(**data,
                    teachers=teachers,
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
    course.teachers = [get_user(user_id) for user_id
                       in data.pop('teacher_ids', [])]
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
    return '/api/v1/payments/callback/{}'.format(order_id)


def get_order(order_id):
    return Order.query.get_or_404(order_id)


def get_user_product_ids(user, for_what):
    assert for_what in ('course', 'service')
    product_id = '{}_product_id'.format(for_what)
    product_items = '{}_product_items'.format(for_what)
    return set(
        getattr(product_item, product_id)
        for order in user.orders if order.status == 'PAYED'
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


def create_access_items(course_product, user_id):
    course_videos = course_product.course.videos
    interval = 2
    begin_date_list, end_date = get_timing(course_videos, interval)
    return [Access(video_id=video.video_id,
                   user_id=user_id,
                   begin_date=b_date,
                   end_date=end_date)
            for b_date, video in zip(begin_date_list, course_videos)
            if not Access.query.filter_by(
            video_id=video.video_id,
            user_id=user_id,
        ).one_or_none()]


def get_timing(items, interval):
    begin_dates = [datetime.now() + timedelta(minutes=interval * i) for i in range(len(items))]
    return begin_dates, begin_dates[-1] + timedelta(days=90)


def grant_access_for_payed_order(order_id):
    order = get_order(order_id)
    access_items = []
    purchased_course_product_ids = check_purchased_course_product_ids(order.user,
                                                                      [x.course_product_id
                                                                       for x in order.course_product_items])
    purchased_service_product_ids = check_purchased_service_product_ids(order.user,
                                                                        [x.service_product_id
                                                                         for x in order.service_product_items])
    if len(purchased_course_product_ids) + len(purchased_service_product_ids) != 0:
        return False, (403, 'One or more products already purchased,'
                            'course: {}, service: {}'.format(purchased_course_product_ids,
                                                             purchased_service_product_ids))

    for course_product_item in order.course_product_items:
        access_items += create_access_items(course_product_item.course_product,
                                            order.user_id)
    # TODO deactivate link + remove existing orders for the same course product/service product
    session.add_all(access_items)
    order.status = 'PAYED'
    session.commit()

    for course_product_item in order.course_product_items:
        course_progress = get_course_progress(order.user_id, course_product_item.course_product.course_id)
        if course_progress is not None:
            update_course_progress_video_count(course_progress)
    session.commit()
    return True, {}


def get_course_progress(user_id, course_id):
    return CourseProgressTracking.query.filter(
        CourseProgressTracking.course_id == course_id,
        CourseProgressTracking.user_id == user_id
    ).one_or_none()


def update_video_progress(user, data):
    video = get_video_by_id(data['video_id'])
    video_progress = VideoProgressTracking.query.filter(
        VideoProgressTracking.video_id == video.video_id,
        VideoProgressTracking.user_id == user.user_id
    ).one_or_none()
    if video_progress is None:
        course_progress = get_course_progress(user.user_id,
                                              video.course_id)
        if course_progress is None:
            course_progress = CourseProgressTracking(
                course_id=video.course_id,
                user_id=user.user_id
            )
            update_course_progress_video_count(course_progress)
            session.add(course_progress)
        video_progress = VideoProgressTracking(
            video_id=video.video_id,
            user_id=user.user_id,
            course_progress=course_progress
        )
        session.add(video_progress)
    new_progress = round_progress_percent(data['progress_percent'])
    old_progress = video_progress.progress_percent
    if old_progress is not None and new_progress > old_progress:
        video_progress.progress_percent = new_progress
        update_course_progress(video_progress.course_progress)
        if video_progress.progress_percent == 100:
            send_hw(user.user_id,
                    course_id=video.course_id,
                    video_id=video.video_id,
                    homework=video.homework
                    )
    session.commit()
    return video_progress


def update_course_progress_video_count(course_progress):
    course_progress.video_count = Access.query.filter(
        Access.user_id == course_progress.user_id,
    ).join(
        Video,
        Access.video
    ).filter(
        Video.course_id == course_progress.course_id
    ).count()


def update_course_progress(course_progress):
    course_progress.progress_percent = round(sum(
        video_progress.progress_percent
        for video_progress in course_progress.video_progress_items
    ) / course_progress.video_count)


def round_progress_percent(progress):
    return 100 if progress >= 95 else progress


def get_chat_thread(chat_thread_id):
    return ChatThread.query.get_or_404(chat_thread_id)


def get_chats_for_student(current_user):
    return Chat.query.filter(
        Chat.student_id == current_user.user_id
    ).all()


def get_chats_for_teacher(current_user):
    chats = Chat.query.join(
        Course,
        Chat.course
    ).join(
        User,
        Course.teachers
    ).filter(
        User.user_id == current_user.user_id
    ).distinct().all()
    result = []
    for course_id in set(chat.course_id for chat in chats):
        course_chats = [x for x in chats if x.course_id == course_id]
        result.append({
            'course': course_chats[0].course,
            'chats': course_chats,
        })
    return result


def update_chat_and_thread_read_status(chat_thread, sender, is_new_message=False):
    update_read_status(chat_thread, sender, is_new_message)
    update_read_status(chat_thread.chat, sender, is_new_message)


def update_read_status(obj, sender, is_new_message=False):
    if sender == 'TEACHER':
        obj.teacher_read = True
        if is_new_message:
            obj.student_read = False
    if sender == 'STUDENT':
        obj.student_read = True
        if is_new_message:
            obj.teacher_read = False


def get_chat_items_by_chat_id(current_user, chat_id, sender):
    chat = Chat.query.get_or_404(chat_id)
    if check_sender(current_user=current_user,
                    chat=chat,
                    sender=sender):
        return False, (403, 'Access denied')
    # Don't update read status if admin is watching...
    if sender != 'TEACHER' or current_user.role != 'ADMIN':
        update_read_status(chat, sender, False)
        for chat_thread in chat.chat_threads:
            update_read_status(chat_thread, sender, False)
            if chat_thread.chat_lines[-1].sender != sender:
                chat_thread.chat_lines[-1].is_read = True
        session.commit()
    return chat.chat_threads


def check_teacher_able_to_send(current_user, chat):
    if current_user.role == 'ADMIN':
        return True
    return current_user.user_id in {x.user_id for x in chat.course.teachers}


def check_sender(current_user, chat, sender):
    if sender == 'TEACHER':
        result = check_teacher_able_to_send(current_user, chat)
    elif sender == 'STUDENT':
        result = current_user.user_id == chat.student_id
    else:
        result = False
    return result


def add_chat_line(current_user, body):
    chat_thread = get_chat_thread(body.pop('chat_thread_id'))
    sender = body['sender']
    if chat_thread.chat_lines[-1].sender == sender or \
            not check_sender(current_user=current_user,
                             chat=chat_thread.chat,
                             sender=sender
                             ):
        return False, (403, 'Access denied')
    message = body['message']
    chat_line = create_chat_line(chat_thread, sender, message)
    chat_thread.chat.last_message_date = datetime.now()
    update_chat_and_thread_read_status(chat_thread, sender, True)
    session.commit()
    return True, chat_line


def create_chat_line(chat_thread, sender, message):
    chat_line = ChatLine(
        chat_thread=chat_thread,
        sender=sender,
        message=message
    )
    session.add(chat_line)
    return chat_line


def send_hw(user_id, course_id, video_id, homework):
    result = session.query(Chat, ChatThread).filter(
        Chat.student_id == user_id,
        Chat.course_id == course_id
    ).join(ChatThread, Chat.chat_threads).filter(
        ChatThread.video_id == video_id
    ).one_or_none()
    if result is None:
        chat = Chat(
            student_id=user_id,
            course_id=course_id
        )
        session.add(chat)
        chat_thread = None
    else:
        chat, chat_thread = result
        return
    if chat_thread is None:
        chat_thread = ChatThread(
            chat=chat,
            video_id=video_id,
            hw_status=hw_statuses[0]
        )
        session.add(chat_thread)
    if homework is None:
        homework = 'TEST: No homework found!'
    chat_line = create_chat_line(chat_thread, 'TEACHER', homework)
    session.commit()
    return chat_line


def add_field_to_obj(obj_list, key):
    return [setattr(user, key, course) or user for user, course in obj_list]


def add_courses_to_user(user_list):
    return user_list


def add_course_to_user(user_course_list):
    return add_field_to_obj(user_course_list, 'course')
