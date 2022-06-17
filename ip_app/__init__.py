from flask import Flask, Blueprint
from flask_migrate import Migrate
from flask_restx import Api

from flask_sqlalchemy import SQLAlchemy
from jsonschema import FormatChecker
from sqlalchemy import MetaData
from flask_apscheduler import APScheduler
from flask_executor import Executor
from flask_cors import CORS

from config import Config

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
logger = app.logger
logger.setLevel(app.config['LOGGER_LEVEL'])

naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

blueprint = Blueprint('api', __name__, url_prefix='/api/v1')
api = Api(blueprint,
          version='1',
          title='i-Proffi - API',
          description='i-Proffi API',
          authorizations={
              'apikey': {
                  'type': 'apiKey',
                  'in': 'header',
                  'name': 'Authorization',
                  'description': "Type in the *'Value'* input box below: **'Bearer &lt;TOKEN&gt;'**"
              },
          },
          security='apikey',
          format_checker=FormatChecker()
          )
app.register_blueprint(blueprint)
db = SQLAlchemy(app, metadata=MetaData(naming_convention=naming_convention))
session = db.session
migrate = Migrate(app, db)

scheduler = APScheduler(app=app)
executor = Executor(app)

from .models import *
from .service import *
from .routes import *
