from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField()

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(verbose_name='Текст', help_text='Введите текст')
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts', null=True)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, blank=True, null=True,
                              related_name='posts', verbose_name='Группа', help_text='Выберите группу')
    image = models.ImageField(upload_to='posts/', blank=True, null=True) 

    class Meta:
        ordering = ('-pub_date',)

    def __str__(self):
        short_text = self.text[:10]
        return f'{self.author} - {self.pub_date:%d %b-%Y} - {short_text}'


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.SET_NULL, related_name='comments', blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField(verbose_name='Текст', help_text='Введите текст')
    created = models.DateTimeField('date published', auto_now_add=True)

    class Meta:
        ordering = ('-created',)

class Follow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="follower")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following")