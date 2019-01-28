from flask import render_template,request,url_for,redirect,flash
from . import auth
from flask_login import login_required,login_user,logout_user,current_user
from .forms import LoginForm,RegisteForm,ChangePasswordForm
from ..model import User
from .. import db

@auth.route('/login',methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email = form.email.data).first()
        # if user is not None and user.verify_password(form.password.data):
        if user is not None and user.verify_password(form.password.data):
            login_user(user,form.remember_me.data)
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('Invalid username or password')
    return render_template('auth/login.html',form = form)

@auth.route('/secret')
@login_required
def secret():
    return 'Only authenticated users are allowed!'

@auth.route('/register',methods=['GET','POST'])
def register():
    form = RegisteForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,username=form.username.data,
                    password=form.password.data)
        db.session.add(user)
        flash('You can now login！')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html',form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out!')
    return redirect(url_for('main.index'))

@auth.route('/change-password')
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            flash('Your password has been changed！')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid password')
    return render_template('auth/change_password.html',form=form)

#  auth 蓝本中的 before_app_request 处理程序会在每次请求前运行
@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()

