from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_moment import Moment
from flask_bootstrap import Bootstrap
from config import config
from flask_login import LoginManager


login_manager = LoginManager()
# 可以设为 None、'basic' 或 'strong'
# 设为 'strong' 时，Flask-Login 会记录客户端 IP
# 地址和浏览器的用户代理信息，如果发现异动就登出用户
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login' # 设置登录页面的端点。

bootstrap = Bootstrap()
moment = Moment()
db = SQLAlchemy()

def create_app(config_name):
    app = Flask(__name__)

    # 读取配置文件
    app.config.from_object(config[config_name])
    config[config_name].init__app(app)

    bootstrap.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)

    from .main import main as main_blueprint
    from .auth import auth as auth_blueprint

    app.register_blueprint(main_blueprint,url_profix = '/main')
    app.register_blueprint(auth_blueprint,url_profix = '/auth')

    return app

'''
问题一：个人信息日期显示不出来（已解决）
问题二：增加修改邮箱功能
'''