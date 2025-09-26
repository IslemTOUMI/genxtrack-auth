from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
# les limites & le storage (redis/memory) seront fournis dans app.__init__.py via limiter.init_app(...)
limiter = Limiter(key_func=get_remote_address)
