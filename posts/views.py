from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PostForm, CommentForm
from .models import Group, Post, User, Comment, Follow
from django.views.decorators.cache import cache_page

@cache_page(20, key_prefix="index_page")
def index(request):
    post_list = Post.objects.order_by('-pub_date').all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'index.html',
        {'page': page, 'paginator': paginator}
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.order_by('-pub_date').all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'group.html',
        {'group': group, 'page': page, 'paginator': paginator}
    )


@login_required
def post_new(request):
    form = PostForm(request.POST, files=request.FILES or None)
    if request.method != 'POST':
        return render(request, 'post_new.html', {'form': form})
    if form.is_valid():
        post_new = form.save(commit=False)
        post_new.author = request.user
        post_new.save()
        return redirect('index')
    return render(request, 'post_new.html', {'form': form})


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts_count = Post.objects.filter(author=author).count()
    post = Post.objects.filter(author=author)
    paginator = Paginator(post, 10)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'profile.html', {
        'page': page,
        'paginator': paginator,
        'posts_count': posts_count,
        'author': author
    })


@login_required
def post_edit(request, username, post_id):
    author = User.objects.get(username=username)
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect('post', username=author, post_id=post_id)
    return render(request, 'post_new.html', {'form': form, 'author': author, 'post': post}) 


def post_view(request, username, post_id):
    author = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, author=author.id, id=post_id)
    posts_count = Post.objects.filter(author=post.author).count()
    comments = post.comments.all()
    follower = Follow.objects.filter(author=author).count()
    user = request.user
    return render(request, 'post.html', {
        'posts_count': posts_count,
        'post': post,
        'author': author,
        'items': comments,
        'form': CommentForm(),
    })

def page_not_found(request, exception):
    # Переменная exception содержит отладочную информацию, 
    # выводить её в шаблон пользователской страницы 404 мы не станем
    return render(
        request, 
        "misc/404.html", 
        {"path": request.path}, 
        status=404
    )

@login_required
def add_comment(request, username, post_id):
    form = CommentForm(request.POST or None)
    post = get_object_or_404(Post, author__username=username, id=post_id)
    items = post.comments.all()
    author = get_object_or_404(User, username=username)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        return redirect('post', username = username, post_id=post_id)
    context = {
        'post': post,
        'form': form,
        'items': items,
        'author': author
    }
    return render(request, 'post.html', context)

@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    context = {
        'page':page,
        'paginator':paginator,
        'page_number':page_number
    }
    return render(request, "follow.html", context)

@login_required
def profile_follow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    if user != author:
        follow = Follow.objects.get_or_create(user=user, author=author)   
    return redirect('profile', username=username)


@login_required
def profile_unfollow(request, username):
    user = request.user
    author = User.objects.get(username=username)
    follow = Follow.objects.filter(user=user, author=author)
    follow.delete()
    return redirect('profile', username=username)

def server_error(request):
    return render(request, "misc/500.html", status=500)