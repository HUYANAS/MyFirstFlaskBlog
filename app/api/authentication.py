from flask_httpauth import HTTPBasicAuth
from flask import g,jsonify
from ..model import User,AnonymousUser
from . import api
from .errors import unauthorized,forbidden

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(email,password):
    if email == '':
        g.current_user = AnonymousUser()
        return True
    user = User.query.filter_by(email=email).first()
    if not user:
        return False
    g.current_user = user
    return user.verify_password(password)

@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')

@api.before_request
@auth.login_required
def before_request():
    if not g.current_user.is_anonymous:
        return forbidden('未认证的用户')

