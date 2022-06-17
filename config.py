class Config(object):
    SQLALCHEMY_DATABASE_URI = 'mysql://iproffi:IPROFFI86@localhost:3306/iproffi?charset=utf8'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RESTX_VALIDATE = True
    LOGGER_LEVEL = 'DEBUG'
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    EXECUTOR_MAX_WORKERS = 1

