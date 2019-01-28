from flask import render_template,session,redirect,url_for,abort,flash
from . import main
from flask_login import login_required,current_user
from .forms import NameForm,EditProfileForm,EditProfileAdminForm,PostForm
from ..model import User,Role,Post
from .. import db
from ..decorators import admin_required,permission_required
from ..model import Permissions


@main.route('/',methods=['GET','POST'])
# @login_required
def index():
    # form = NameForm()
    # if form.validate_on_submit():
    #     user = User.query.filter_by(username=form.name.data).first()
    #     if user is None:
    #         user = User(username=form.name.data)
    #         db.session.add(user)
    #         # db.session.commit()
    #         session['know'] = False
    #     else:
    #         session['know'] = True
    #     session['name'] =form.name.data
    #     return redirect(url_for('main.index'))
    # return render_template('main/index.html', form=form,name=session.get('name'),know=session.get('know',False))
    form = PostForm()
    if current_user.can(Permissions.WRITE_ARTICLES) and form.validate_on_submit():
        post = Post(body=form.body.data,author=current_user._get_current_object())
        db.session.add(post)
        return redirect((url_for('main.index')))
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('main/index.html',form=form,posts=posts)

@main.route('/admin')
@login_required
@admin_required
def for_admins_only():
    return 'for administrators！'

@main.route('/moderator')
@login_required
@permission_required(Permissions.MODERATE_COMMENTS)
def for_moderators_only():
    return('For comment moderators!')

@main.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    return render_template('main/user.html',user=user)

# 用户级别的资料编辑器
@main.route('/edit-profile',methods=['Get','Post'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('个人信息已更新')
        return redirect(url_for('main.user',username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('main/edit_profile.html',form=form)

# 管理员级别的资料编辑器
@main.route('/edit-profile/<int:id>',methods=['GET','POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('用户信息已更新')
        return redirect(url_for('main.user',username = user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.role.data = user.role
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('main/edit_profile.html',form = form)
