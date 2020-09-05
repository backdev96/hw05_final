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
        self.post = Post.objects.create(
                text='try_text',
                author=self.user,
                group=self.group,
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
        response = self.unauth_client.post(reverse('new_post'),
                                           kwargs={'text': 'text', 'group': self.group.id},
                                           follow=True)
        self.assertEqual(response.status_code, 200)
        login_url = reverse('login')
        new_post_url = reverse('new_post')
        target_url = f'{login_url}?next={new_post_url}'
        self.assertRedirects(response,  f'{target_url}')
        self.assertEqual(Post.objects.count(), 1)

    def test_edit(self):
        response = self.auth_client.post(reverse('new_post'),
                                           kwargs={'text': 'text', 'group': self.group.id},
                                           follow=False)
        self.search_post(self.url_list, self.text, self.user, self.group)

    def test_newpost_unauth_user(self):
        response = self.unauth_client.post(reverse('new_post'),
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

    def test_with_picture(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        img = SimpleUploadedFile(
            name='some.gif',
            content=small_gif,
            content_type='image/gif',
        )
        post_with_img = Post.objects.create(
            author=self.user,
            text='text',
            group=self.group,
            image=img,
        )
        for url in self.url_list:
            with self.subTest(url=url):
                response = self.auth_client.get(url)
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
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Follow.objects.count(), 0)

    def test_comment(self):
        response = self.auth_client.post(
            reverse('add_comment', args=[self.second_user.username]), follow=True)
        login_url = reverse('login')
        add_comment_url = reverse('add_comment')
        target_url = f'{login_url}?next={add_comment_url}'
        self.assertRedirects(response,  f'{target_url}')

    def test_cache(self):
        cache_test_post_1 = Post.objects.create(
           text='cache test text',
           author=self.user,
           group=self.group
           )
        response = self.auth_client.get(reverse('index'))
        Post.objects.all().delete()
        self.assertContains(response, cache_test_post_1.text)
        cache.clear()
        response = self.auth_client.get(reverse('index'))
        self.assertNotContains(response, cache_test_post_1.text)

    def test_new_post_in_feed(self):
        self.user3 = User.objects.create_user(
                    username='user_user_user',
                    email='test_user_user@test.com',
                    password='test_password'
                    )
        follow_user2 = self.auth_client.get(
            reverse("profile_follow", args=[self.second_user.username]
            ))
        post2 = Post.objects.create(
                text='test_new_post_in_feed text',
                author=self.second_user,
                group=self.group,
                )
        self.assertEqual(len(Follow.objects.all()), 1)
        response = self.auth_client.get(reverse("follow_index"))
        self.assertContains(response, post2.text)
        self.auth_client.force_login(self.user3)
        response = self.auth_client.get(reverse("follow_index"))
        self.assertNotContains(response, post2.text)