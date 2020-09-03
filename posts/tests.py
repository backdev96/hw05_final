from io import BytesIO

from django.core.cache import cache
from django.core.files.base import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image, ImageDraw

from .models import Follow, Group, Post, User


class ProfileTest(TestCase):

    def setUp(self):
        self.auth_client = Client()
        self.unauth_client = Client()
        self.user = User.objects.create_user(
                    username='user_user',
                    email='test_user@test.com',
                    password='test_password'
                    )
        self.second_user = User.objects.create_user(
                           username='second_user',
                           email='second_user@test.com',
                           password='second_test_password'
                           )
        self.auth_client.force_login(self.user)
        self.group = Group.objects.create(
                    title='test_group',
                    slug='test',
                    )
        self.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        self.img = SimpleUploadedFile(name='some.gif',
                                      content=self.small_gif,
                                      content_type='image/gif',
                                      )
        self.post = Post.objects.create(
                text='try_text',
                author=self.user,
                group=self.group,
                image=self.img
                )
        self.text = 'text_text'
        self.url_list = (reverse('index'),
                         reverse('profile', kwargs={"username": self.user.username}),
                         reverse('post', kwargs={'username': self.user.username, 'post_id': self.post.id}),
                         reverse('group', kwargs={'slug': self.group.slug}),
                         )

    def search_post(self, url_list, text, user, group):
        for url in url_list:
            response = self.auth_client.get(url)
            paginator = response.context.get('paginator')
            if paginator is not None:
                self.assertEqual(paginator.count, 1)
                post = response.context['page'][0]
            else:
                post = response.context['post']
            count_posts = Post.objects.count()
            post_author = User.objects.get(username="user_user")
            return (self.assertEqual(post_author, self.user),
                    self.assertContains(response, self.post.text),
                    self.assertEqual(post.group, group),
                    self.assertEqual(count_posts, 1)
                    )

    def test_profile(self):
        response = self.auth_client.get(reverse(
                                           'profile',
                                           args=[self.user.username]))
        self.assertEqual(response.status_code, 200)

    def test_newpost(self):
        self.search_post(self.url_list, self.text, self.user, self.group)

    def test_guest(self):
        response = self.unauth_client.post(reverse
                                           ('new_post'),
                                           kwargs={'text': 'text', 'group': self.group.id},
                                           follow=True)
        self.assertEqual(response.status_code, 200)
        login_url = reverse('login')
        new_post_url = reverse('new_post')
        target_url = f'{login_url}?next={new_post_url}'
        self.assertRedirects(response,  f'{target_url}')
        self.assertEqual(Post.objects.count(), 1)

    def test_edit(self):
        response = self.auth_client.post(reverse
                                         ('new_post'),
                                         kwargs={'text': 'text', 'group': self.group.id},
                                         follow=False)
        self.search_post(self.url_list, self.text, self.user, self.group)

    def test_newpost_unauth_user(self):
        response = self.unauth_client.post(reverse
                                           ('new_post'),
                                           kwargs={'text': 'text', 'group': self.group.id},
                                           follow=True)
        login_url = reverse('login')
        new_post_url = reverse('new_post')
        target_url = f'{login_url}?next={new_post_url}'
        self.assertRedirects(response,  f'{target_url}')
        self.assertEqual(Post.objects.count(), 1)

    def test_404(self):
        response = self.auth_client.get('/auth/test404')
        self.assertEqual(response.status_code, 404)

    @staticmethod
    def get_image_file(name, ext='png', size=(50, 50), color=(256, 0, 0)):
        file_obj = BytesIO()
        image = Image.new("RGBA", size=size, color=color)
        image.save(file_obj, ext)
        file_obj.seek(0)
        return File(file_obj, name=name)

    def test_with_picture(self):
        for url in self.url_list:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, '<img')

    def test_without_picture(self):
        not_image = SimpleUploadedFile(
            name='some.txt',
            content=b'abc',
            content_type='text/plain',
        )

        url = reverse('new_post')
        response = self.auth_client.post(
            url, {'text': 'some_text', 'image': not_image}
        )

        self.assertFormError(
            response,
            'form',
            'image',
            errors=(
                'Загрузите правильное изображение. '
                'Файл, который вы загрузили, поврежден '
                'или не является изображением.'
            ),
        )

    def test_user_follow(self):
        follow_second_user = self.auth_client.get(
            reverse("profile_follow", args=[self.second_user.username]))
        response = self.auth_client.get(reverse("follow_index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Follow.objects.count(), 1)

    def test_user_unfollow(self):
        unfollow_second_user = self.auth_client.get(
            reverse("profile_unfollow", args=[self.second_user.username]))
        response = self.auth_client.get(reverse("follow_index"))
        self.assertContains(unfollow_second_user, "Отписаться")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Follow.objects.count(), 0)

    def test_comment(self):
        response = self.auth_client.post(
            reverse('add_comment', args=[self.second_user.username], follow=True))
        login_url = reverse('login')
        add_comment_url = reverse('add_comment')
        target_url = f'{login_url}?next={add_comment_url}'
        self.assertRedirects(response,  f'{target_url}')

    def test_cache(self):
        pass
