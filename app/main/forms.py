from flask_wtf import FlaskForm
from wtforms import StringField,SubmitField,TextAreaField,SelectField,ValidationError
from wtforms.validators import DataRequired,Length,Email,Regexp
from ..model import User,Role
from flask_pagedown.fields import PageDownField


class NameForm(FlaskForm):
    name = StringField('你的名字', validators=[DataRequired()])
    submit = SubmitField('submit')

class EditProfileForm(FlaskForm):
    name = StringField('Real name',validators=[Length(0,64)])
    location = StringField('Location',validators=[Length(0,64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('提交')

class EditProfileAdminForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(),Length(1,64),Email()])
    username = StringField('Username', validators=[DataRequired(), Length(1, 64),
                                                   Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                                          'Username必须是字母数字下划线小数点且以字母开头')])
    role = SelectField('Role',coerce=int)
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('提交')

    def __init__(self,user,*args,**kwargs):
        super().__init__(*args,**kwargs)
        # 各元组都包含两个元素：选项的标识符和显示在控件中的文本字符串。
        self.role.choices = [(role.id,role.name) for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self,field):
        if field.data != self.user.mail and User.query.filter_by(email=field.data).first():
            raise ValidationError('该邮箱已注册')

    def validate_username(self,field):
        if field.data != self.user.username and User.quary.filter_by(username=field.data).first():
            raise ValidationError('该用户名已存在')

# 博客文章表单
class PostForm(FlaskForm):
    body = PageDownField('你的想法是：',validators=[DataRequired()])
    submit = SubmitField('提交')

# 文章评论表单
class CommentForm(FlaskForm):
    body = PageDownField('',validators=[DataRequired()])
    submit = SubmitField('提交')

