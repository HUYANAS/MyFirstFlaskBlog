from flask import render_template,session,redirect,url_for,abort,flash,request,current_app,make_response
from . import main
from flask_login import login_required,current_user
from .forms import NameForm,EditProfileForm,EditProfileAdminForm,PostForm,CommentForm
from ..model import User,Role,Post,Comment
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
    page = request.args.get('page',1,type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed',''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page,per_page=current_app.config['FLASK_POSTS_PER_PAGE'],error_out=False)
    # posts = Post.query.order_by(Post.timestamp.desc()).all()
    posts = pagination.items
    return render_template('main/index.html',form=form,posts=posts,show_followed=show_followed,pagination=pagination)

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
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASK_POSTS_PER_PAGE'],
        error_out=False)
    # if user is None:
    #     abort(404)
    # posts = user.posts.order_by(Post.timestamp.desc()).all()
    posts = pagination.items
    return render_template('main/user.html',user=user,posts=posts,pagination=pagination)

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

@main.route('/post/<int:id>')
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        # 评论的 author字段也不能直接设为 current_user ，
        # 因为这个变量是上下文代理对象。
        # 真正的 User 对象要使用表达式 current_user._get_current_object() 获取
        comment = Comment(body=form.body.data,post=post,author=current_user._get_current_object())
        db.session.add(comment)
        flash('你的评论已发布')
        return redirect(url_for('.post',id=post.id,page=-1))
    page = request.args.get('page','1',type=int)
    if page == -1:
        page = (post.comments.count() - 1) // current_app.config['FLASK_COMMENTS_PER_PAGE'] + 1
    if not isinstance(page,int):
        page = int(page)
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(page, per_page=current_app.config['FLASK_COMMENTS_PER_PAGE'],error_out=False)
    comments = pagination.items
    return render_template('main/post.html',posts=[post],form=form,comments=comments,pagination=pagination)

@main.route('/edit/<int:id>',methods=['GET','POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permissions.ADMINISTER):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        flash('博客已更新')
        return redirect(url_for('.post',id=post.id))
    form.body.data = post.body
    return render_template('main/edit_post.html',form=form)

@main.route('/follow/<username>')
@login_required
@permission_required(Permissions.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('你已经关注过该用户')
        return redirect(url_for('.user',username=username))
    current_user.follow(user)
    flash('关注成功：%s' %username)
    return redirect(url_for('.user',username=username))

@main.route('/unfollow/<username>')
@login_required
@permission_required(Permissions.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('用户不存在')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('你还没关注过该用户')
        return redirect(url_for('.user',username=username))
    current_user.unfollow(user)
    flash('你已经取消关注用户：%s' % username)
    return redirect(url_for('.user',username=username))

@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('用户不存在')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(page, per_page=current_app.config['FLASK_FOLLOWERS_PER_PAGE'],error_out=False)
    follows = [{'user':item.follower,'timestamp':item.timestamp} for item in pagination.items]
    return render_template('main/followers.html',user=user,title='Followers of ',
                           endpoint='.followers',pagination=pagination,follows=follows)

@main.route('/followed-by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('用户不存在')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(page,per_page=current_app.config['FLASK_POSTS_PER_PAGE'],error_out=False)
    follows = [{'user':item.follower,'timestamp':item.timestamp} for item in pagination.items]
    return render_template('main/followers.html', user=user, title='Followed by ',
                           endpoint='.followed_by', pagination=pagination, follows=follows)

@main.route('/all')
@login_required
def show_all():
    response = make_response(redirect(url_for('.index')))
    response.set_cookie('show_followed','',max_age=30*24*60*60)
    return response

@main.route('/followed')
@login_required
def show_followed():
    response = make_response(redirect(url_for('.index')))
    response.set_cookie('show_followed','1',max_age=30*24*60*60)
    return response

@main.route('/moderate')
@login_required
@permission_required(Permissions.MODERATE_COMMENTS)
def moderate():
    page = request.args.get('page',1,type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page,per_page=current_app.config['FLASK_COMMENTS_PER_PAGE'],error_out=False
    )
    comments = pagination.items
    return render_template('main/moderate.html',comments=comments,pagination=pagination,page=page)

@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permissions.MODERATE_COMMENTS)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    return redirect(url_for('.moderate',page=request.args.get('page',1,type=int)))

@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permissions.MODERATE_COMMENTS)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    return redirect(url_for('.moderate',page=request.args.get('page',1,type=int)))

