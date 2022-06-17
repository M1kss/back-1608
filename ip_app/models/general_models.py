from ip_app import db
from ip_app.constants import roles, user_statuses, order_statuses, discount_types, \
    sex_choices, sender_choices, hw_statuses
from sqlalchemy.dialects.mysql import INTEGER, SMALLINT


class UserRegistration(db.Model):
    __tablename__ = 'users_registration'
    email = db.Column(db.String(30), primary_key=True)
    hash = db.Column(db.String(36), nullable=False, unique=True)
    date = db.Column(db.DateTime, server_default=db.func.now())
    name = db.Column(db.String(30))
    last_name = db.Column(db.String(30))
    phone = db.Column(db.String(10))


class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    email = db.Column(db.String(30), nullable=False, unique=True)
    role = db.Column(db.Enum(*roles), nullable=False, server_default=roles[-1])
    status = db.Column(db.Enum(*user_statuses), nullable=False, server_default=user_statuses[0])
    registration_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    last_seen = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    name = db.Column(db.String(30))
    last_name = db.Column(db.String(30))
    token = db.Column(db.String(36), unique=True)
    profile_pic_url = db.Column(db.String(150))
    phone = db.Column(db.String(10))
    city = db.Column(db.String(30))
    sex = db.Column(db.Enum(*sex_choices))
    birth_date = db.Column(db.Date)
    password_hash = db.Column(db.String(100))


class Course(db.Model):
    __tablename__ = 'courses'
    course_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(250))
    course_pic_url = db.Column(db.String(100))
    author_name = db.Column(db.String(30), nullable=True)
    landing_info = db.Column(db.JSON, default={})

    teachers = db.relationship(
        User.__table__,
        secondary='course_teachers',
        backref='taught_courses',
    )


class CourseTeacherCorrespondence(db.Model):
    __tablename__ = 'course_teachers'
    __table_args__ = (
        db.UniqueConstraint('course_id', 'teacher_id',
                            name='unique_course_teacher_entry'),
    )
    course_teacher_id = db.Column(INTEGER(unsigned=True),
                                  primary_key=True)
    course_id = db.Column(INTEGER(unsigned=True),
                          db.ForeignKey('courses.course_id',
                                        ondelete="CASCADE"),
                          nullable=False)
    teacher_id = db.Column(INTEGER(unsigned=True),
                           db.ForeignKey('users.user_id',
                                         ondelete="CASCADE"),
                           nullable=False)

    teacher = db.relationship(User, backref=db.backref('course_teachers',
                                                       cascade="all, delete"))
    course = db.relationship(Course, backref=db.backref('course_teachers',
                                                        cascade="all, delete"))


class Order(db.Model):
    __tablename__ = 'orders'
    order_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    user_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    payment_link = db.Column(db.String(150))
    price = db.Column(INTEGER(unsigned=True))
    promocode = db.Column(db.String(20))
    status = db.Column(db.Enum(*order_statuses), default=order_statuses[0])

    user = db.relationship(User, backref='orders')


class CourseProduct(db.Model):
    __tablename__ = 'course_products'
    course_product_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    course_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('courses.course_id', ondelete="CASCADE"),
                          nullable=False)
    title = db.Column(db.String(50))
    description = db.Column(db.String(250))
    duration = db.Column(db.String(25))
    price = db.Column(INTEGER(unsigned=True))
    discount = db.Column(INTEGER(unsigned=True))
    discount_type = db.Column(db.Enum(*discount_types))

    course = db.relationship(Course, backref=db.backref('course_products', cascade="all, delete"))


class ServiceProduct(db.Model):
    __tablename__ = 'service_products'
    service_product_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    course_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('courses.course_id', ondelete="CASCADE"),
                          nullable=False)
    title = db.Column(db.String(50))
    description = db.Column(db.String(250))
    price = db.Column(INTEGER(unsigned=True))
    discount = db.Column(INTEGER(unsigned=True))
    discount_type = db.Column(db.Enum(*discount_types))

    course = db.relationship(Course, backref=db.backref('service_products', cascade="all, delete"))


class OrderCourseProductItem(db.Model):
    __tablename__ = 'course_pr_items'
    item_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    price = db.Column(INTEGER(unsigned=True))
    course_product_id = db.Column(INTEGER(unsigned=True),
                                  db.ForeignKey('course_products.course_product_id', ondelete="CASCADE"),
                                  nullable=False)
    order_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('orders.order_id', ondelete="CASCADE"), nullable=False)

    order = db.relationship(Order, backref=db.backref('course_product_items', cascade="all, delete"))
    course_product = db.relationship(CourseProduct, backref=db.backref('order_items', cascade="all, delete"))


class OrderServiceProductItem(db.Model):
    __tablename__ = 'service_pr_items'
    item_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    price = db.Column(INTEGER(unsigned=True))
    service_product_id = db.Column(INTEGER(unsigned=True),
                                   db.ForeignKey('service_products.service_product_id', ondelete="CASCADE"),
                                   nullable=False)
    order_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('orders.order_id', ondelete="CASCADE"), nullable=False)

    order = db.relationship(Order, backref=db.backref('service_product_items', cascade="all, delete"))
    service_product = db.relationship(ServiceProduct)


class Video(db.Model):
    __tablename__ = 'videos'
    video_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    course_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('courses.course_id', ondelete="CASCADE"),
                          nullable=False)
    title = db.Column(db.String(50))
    description = db.Column(db.String(250))
    url = db.Column(db.String(150))
    duration = db.Column(SMALLINT(unsigned=True))
    q_and_a = db.Column(db.JSON)

    course = db.relationship(Course, backref=db.backref('videos', cascade="all, delete"))


class CourseApplication(db.Model):
    __tablename__ = 'course_applications'
    application_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    course_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('courses.course_id', ondelete="SET NULL"))
    email = db.Column(db.String(30), nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(30), nullable=False)
    is_registered = db.Column(db.Boolean)
    application_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    course = db.relationship(Course, backref='courses')


class Access(db.Model):
    __tablename__ = 'video_access'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'video_id',
                            name='unique_access_entry'),
        db.Index('access_date_index', 'begin_date', 'end_date'),
    )
    access_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    user_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('users.user_id', ondelete="CASCADE"), nullable=False)
    video_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('videos.video_id', ondelete="CASCADE"), nullable=False)
    begin_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)

    video = db.relationship(Video, backref=db.backref('access_entries', cascade="all, delete"))
    user = db.relationship(User, backref=db.backref('access_entries', cascade="all, delete"))


class CourseProgressTracking(db.Model):
    __tablename__ = 'course_progress'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'course_id',
                            name='unique_course_progress_entry'),
    )
    course_progress_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    course_id = db.Column(INTEGER(unsigned=True),
                          db.ForeignKey('courses.course_id',
                                        ondelete="CASCADE"),
                          nullable=False)
    user_id = db.Column(INTEGER(unsigned=True),
                        db.ForeignKey('users.user_id',
                                      ondelete="CASCADE"),
                        nullable=False)
    progress_percent = db.Column(db.Integer, server_default='0')
    video_count = db.Column(db.Integer, server_default='0')


class VideoProgressTracking(db.Model):
    __tablename__ = 'video_progress'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'video_id',
                            name='unique_video_progress_entry'),
    )
    video_progress_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    video_id = db.Column(INTEGER(unsigned=True),
                         db.ForeignKey('videos.video_id', ondelete="CASCADE"),
                         nullable=False)
    user_id = db.Column(INTEGER(unsigned=True),
                        db.ForeignKey('users.user_id', ondelete="CASCADE"),
                        nullable=False)
    # last_timestamp = db.Column(db.Integer)
    progress_percent = db.Column(db.Integer, server_default='0')
    course_progress_id = db.Column(INTEGER(unsigned=True),
                                   db.ForeignKey('course_progress.course_progress_id',
                                                 ondelete="CASCADE"), nullable=False)
    course_progress = db.relationship(CourseProgressTracking,
                                      backref=db.backref('video_progress_items',
                                                         cascade="all, delete"))


class HomeWork(db.Model):
    __tablename__ = 'video_homework'
    video_homework_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    video_id = db.Column(INTEGER(unsigned=True),
                         db.ForeignKey('videos.video_id', ondelete="CASCADE"), nullable=False)
    homework_message = db.Column(db.String(300))

    video = db.relationship(Video, backref=db.backref('homework',
                                                      cascade="all, delete", uselist=False),
                            )


class Chat(db.Model):
    __tablename__ = 'hw_chats'
    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_id',
                            name='unique_chat_entry'),
    )
    chat_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    student_id = db.Column(INTEGER(unsigned=True),
                           db.ForeignKey('users.user_id', ondelete="CASCADE"),
                           nullable=False)
    course_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('courses.course_id', ondelete="CASCADE"),
                          nullable=False)
    teacher_read = db.Column(db.Boolean, server_default='1')
    student_read = db.Column(db.Boolean, server_default='0')
    last_message_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    course = db.relationship(Course)
    student = db.relationship(User)


class ChatThread(db.Model):
    __tablename__ = 'hw_chat_threads'
    __table_args__ = (
        db.UniqueConstraint('chat_id', 'video_id',
                            name='unique_chat_thread_entry'),
    )
    chat_thread_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    chat_id = db.Column(INTEGER(unsigned=True),
                        db.ForeignKey('hw_chats.chat_id', ondelete="CASCADE"), nullable=False)
    hw_status = db.Column(db.Enum(*hw_statuses), server_default=hw_statuses[0])
    video_id = db.Column(INTEGER(unsigned=True),
                         db.ForeignKey('videos.video_id', ondelete="SET NULL"),
                         )
    teacher_read = db.Column(db.Boolean, server_default='1')
    student_read = db.Column(db.Boolean, server_default='0')
    chat = db.relationship(Chat, backref=db.backref('chat_threads',
                                                    cascade="all, delete"))

    video = db.relationship(Video)


class ChatLine(db.Model):
    __tablename__ = 'hw_chat_lines'
    chat_line_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    message = db.Column(db.String(300))
    message_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    chat_thread_id = db.Column(INTEGER(unsigned=True),
                               db.ForeignKey('hw_chat_threads.chat_thread_id', ondelete="CASCADE"), nullable=False)
    sender = db.Column(db.Enum(*sender_choices), nullable=False)
    is_read = db.Column(db.Boolean, server_default='0')
    chat_thread = db.relationship(ChatThread,
                                  backref=db.backref('chat_lines',
                                                     cascade="all, delete"))


class Notifications(db.Model):
    __tablename__ = 'notifications'
    notification_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    message = db.Column(db.String(300), nullable=False)
    message_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())



class Statistics(db.Model):
    __tablename__ = 'statistics'
    statistics_name = db.Column(db.String(30), primary_key=True)
    value = db.Column(INTEGER(unsigned=True))
