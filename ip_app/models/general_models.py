from ip_app import db
from ip_app.constants import roles, user_statuses, course_statuses, video_statuses
from sqlalchemy.dialects.mysql import INTEGER, SMALLINT


class CourseApplication(db.Model):
    __tablename__ = 'course_applications'
    application_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    course_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('courses.course_id'), nullable=False)
    email = db.Column(db.String(30), nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(30), nullable=False)
    application_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())


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
    token = db.Column(db.String(36))
    profile_pic_url = db.Column(db.String(150))
    phone = db.Column(db.String(10))
    city = db.Column(db.String(30))
    password_hash = db.Column(db.String(100))


class Course(db.Model):
    __tablename__ = 'courses'
    course_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(250))
    course_pic_url = db.Column(db.String(100))
    author_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('users.user_id'), nullable=False)
    landing_info = db.Column(db.JSON, default={})

    author = db.relationship(User, backref='authored_courses')


class Video(db.Model):
    __tablename__ = 'videos'
    video_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    course_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('courses.course_id'), nullable=False)
    title = db.Column(db.String(50))
    description = db.Column(db.String(250))
    url = db.String(100)
    duration = db.Column(SMALLINT(unsigned=True))
    q_and_a = db.Column(db.JSON)

    course = db.relationship(Course, cascade='delete, merge, save-update', backref='videos')


class CourseProduct(db.Model):
    __tablename__ = 'course_products'
    course_product_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    course_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('courses.course_id'), nullable=False)
    title = db.Column(db.String(50))
    description = db.Column(db.String(250))
    duration = db.Column(SMALLINT(unsigned=True))
    price = db.Column(INTEGER(unsigned=True))

    course = db.relationship(Course, cascade='delete, merge, save-update', backref='course_products')


class ServiceProduct(db.Model):
    __tablename__ = 'service_products'
    course_product_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    course_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('courses.course_id'), nullable=False)
    title = db.Column(db.String(50))
    description = db.Column(db.String(250))
    price = db.Column(INTEGER(unsigned=True))

    course = db.relationship(Course, cascade='delete, merge, save-update', backref='service_products')


class Access(db.Model):
    __tablename__ = 'video_access'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'video_id',
                            name='unique_access_entry'),
        db.Index('access_date_index', 'begin_date', 'end_date'),
    )
    access_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    user_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('users.user_id'), nullable=False)
    video_id = db.Column(INTEGER(unsigned=True), db.ForeignKey('videos.video_id'), nullable=False)
    begin_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
