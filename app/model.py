'''
数据库引擎 URL
MySQL mysql://username:password@hostname/database
Postgres postgresql://username:password@hostname/database
SQLite（Unix） sqlite:////absolute/path/to/database
SQLite（Windows） sqlite:///c:/absolute/path/to/database
'''
import hashlib
from . import db
from werkzeug.security import generate_password_hash,check_password_hash
from itsdangerous import Serializer
from flask import current_app,request
from flask_login import UserMixin,AnonymousUserMixin
from datetime import datetime
from . import login_manager
from markdown import markdown
import bleach

class Role(db.Model):
    __tablename__ = 'roles' #定义在数据库中使用的表名
    id = db.Column(db.Integer,primary_key = True)
    name = db.Column(db.String(64),unique = True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User',backref = 'role',lazy = 'dynamic') #禁止自动执行查询

    # 返回一个可读性的字符串表示模型，可在调试和测试时使用，否则使用
    # 默认表名，默认表名没有遵守使用复数形式进行命名的约定
    def __repr__(self):
        return '<Role %r>' % self.name

    @staticmethod
    def insert_roles():
        roles = {
            'User' : (Permissions.FOLLOW|Permissions.COMMENT|Permissions.WRITE_ARTICLES,True),
            'Moderator' : (Permissions.FOLLOW|Permissions.COMMENT|Permissions.WRITE_ARTICLES|Permissions.MODERATE_COMMENTS,False),
            'Admin' : (0xff,False)
        }
        for i in roles:
            role = Role.query.filter_by(name=i).first()
            if role is None:
                role = Role(name = i)
            role.permissions = roles[i][0]
            role.default = roles[i][1]
            db.session.add(role)

'''
操　　作    位　　值           说　　明
关注用户  0b00000001（0x01） 关注其他用户
在他人的文章中发表评论  0b00000010（0x02） 在他人撰写的文章中发布评论
写文章  0b00000100（0x04） 写原创文章
管理他人发表的评论  0b00001000（0x08） 查处他人发表的不当评论
管理员权限  0b10000000（0x80） 管理网站

用户角色   权　　限        说　　明
匿名 0b00000000（0x00） 未登录的用户。在程序中只有阅读权限
用户 0b00000111（0x07） 具有发布文章、发表评论和关注其他用户的权限。这是新用户的默认角色
协管员 0b00001111（0x0f） 增加审查不当评论的权限
管理员 0b11111111（0xff） 具有所有权限，包括修改其他用户所属角色的权限
'''
class Permissions:
    FOLLOW = 1
    COMMENT = 2
    WRITE_ARTICLES = 4
    MODERATE_COMMENTS = 8
    ADMINISTER = 16

# 关注关系辅助表
class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer,db.ForeignKey('users.id'),primary_key=True)
    followed_id = db.Column(db.Integer,db.ForeignKey('users.id'),primary_key=True)
    timestamp = db.Column(db.DateTime,default=datetime.utcnow)

class User(UserMixin,db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64),unique=True)
    role_id = db.Column(db.Integer,db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(64))  #用户真实姓名
    location = db.Column(db.String(64))  #用户所在地
    about_me = db.Column(db.Text())  #自我介绍
    member_since = db.Column(db.DateTime(),default=datetime.utcnow)  #注册日期
    last_seen = db.Column(db.DateTime(),default=datetime.utcnow)  #最后访问时间
    # 数据库持久化avztar hash值
    avatar_hash = db.Column(db.String(32))
    posts = db.relationship('Post',backref='author',lazy='dynamic')
    # 自关联
    followed = db.relationship('Follow',foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower',lazy='joined'),
                               lazy='dynamic',
                               cascade='all,delete-orphan')
    followers = db.relationship('Follow',foreign_keys=[Follow.followed_id],
                               backref=db.backref('followed',lazy='joined'),
                               lazy='dynamic',
                               cascade='all,delete-orphan')
    comments = db.relationship('Comment',backref='author',lazy='dynamic')

    def __init__(self,**kwargs):
        super(User,self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASK_ADMIN']:
                self.role = Role.query.filter_by(name='Admin').first()
            if self.role is None:
                self.role = Role.query.filter_by(default = True).first()
            if self.email is not None and self.avatar_hash is None:
                self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
            self.follow(self)

    # 把现有的用户设为自己的关注着
    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)

    def can(self,permissions):
        return self.role is not None and (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permissions.ADMINISTER)

    def gravatar(self,size=100,default='identicon',rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(url=url,hash=hash,size=size,default=default,rating=rating)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def follow(self,user):
        if not self.is_following(user):
            f = Follow(follower=self,followed=user)
            db.session.add(f)

    def unfollowed(self,user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.remove(f)

    def is_following(self,user):
        if user.id is None:
            return False
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self,user):
        if user.id is None:
            return False
        return self.followed.filter_by(follower_id=user.id).first() is not None

    # 注意， followed_posts() 方法定义为属性，因此调用时无需加 () 。如此一来，所有关系的句法都一样了
    @property
    def followed_posts(self):
        return Post.query.join(Follow,Follow.followed_id==Post.author_id).filter(Follow.follower_id==self.id)

    # 生成认证令牌
    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],expires_in=expiration)
        return s.dumps({'id':self.id})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self,password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self,password):
        return check_password_hash(self.password_hash,password)

    def __repr__(self):
        return '<User %s>' % self.username

# 定义用户未登录时的权限
class AnonymousUser(AnonymousUserMixin):
    def can(self,permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser

# 加载用户回调函数
# 加载用户的回调函数接收以 Unicode 字符串形式表示的用户标识符。如果能找到用户，这
# 个函数必须返回用户对象；否则应该返回 None。
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# 支持博客文章
class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer,primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime,index=True,default=datetime.utcnow)
    author_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    body_html = db.Column(db.Text)
    comments = db.relationship('Comment',backref='post',lazy='dynamic')

    @staticmethod
    def on_changed_body(target,value,oldvalue,initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value,output_format='html'),tags=allowed_tags,strip=True
        ))

db.event.listen(Post.body,'set',Post.on_changed_body)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer,primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime,index=True,default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer,db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target,value,oldvalue,initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i','strong']
        target.body_html = bleach.linkify(bleach.clean(markdown(value,output_format='html'),tags=allowed_tags,strip=True))

# 定义了一个事件，在修改 body 字段内容时触发，自动把 Markdown 文本转换成 HTML
db.event.listen(Comment.body,'set',Comment.on_changed_body)


