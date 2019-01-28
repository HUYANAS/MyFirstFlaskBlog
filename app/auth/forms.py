from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,BooleanField,SubmitField,TextField
from wtforms import ValidationError
from wtforms.validators import DataRequired,Length,Email,Regexp,EqualTo
from ..model import User

class LoginForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(),Length(1,64),Email()])
    password = PasswordField('Password',validators=[DataRequired()])
    remember_me = BooleanField('记住我') # BooleanField 类表示复选框。
    submit = SubmitField('登录')

class RegisteForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(),Length(1,64),Email()])
    username = StringField('Username',validators=[DataRequired(),Length(1,64),
                                                  Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,
                                                         'Username必须是字母数字下划线小数点且以字母开头')])
    # name = StringField('真实姓名',validators=[DataRequired])
    # location = StringField('所在地')
    # about_me = StringField('个人信息')
    password = PasswordField('密码',validators=[DataRequired(),EqualTo('password02',message='密码必须一致')])
    password02 = PasswordField('确认密码',validators=[DataRequired()])
    submit = SubmitField('注册')

    # 如果表单类中定义了以validate_开头且后面跟着字段名的方法，这个方法就和常规的验证函数一起调用
    # 自定义的验证函数要想表示验证失败，可以抛出ValidationError异常，其参数就是错误消息。
    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered！')

    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old password',validators=[DataRequired()])
    password = PasswordField('New password',validators=[
        DataRequired(),EqualTo('password02',message='密码必须一致')])
    password02 = PasswordField('Confirm new password',validators=[DataRequired()])
    submit = SubmitField('提交更新')

