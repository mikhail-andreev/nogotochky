from django.test import TestCase, Client
from django.urls import reverse

from .models import User
from masters.models import MasterProfile


class UserModelTest(TestCase):
    def test_create_master_user(self):
        user = User.objects.create_user(
            email='master@test.com', username='master', password='pass123',
            role=User.Role.MASTER
        )
        self.assertEqual(user.email, 'master@test.com')
        self.assertTrue(user.is_master)
        self.assertFalse(user.is_admin_user)

    def test_create_admin_user(self):
        user = User.objects.create_user(
            email='admin@test.com', username='admin', password='pass123',
            role=User.Role.ADMIN
        )
        self.assertFalse(user.is_master)
        self.assertTrue(user.is_admin_user)

    def test_default_role_is_master(self):
        user = User.objects.create_user(
            email='default@test.com', username='default', password='pass123'
        )
        self.assertEqual(user.role, User.Role.MASTER)

    def test_email_is_unique(self):
        User.objects.create_user(email='dup@test.com', username='u1', password='pass123')
        with self.assertRaises(Exception):
            User.objects.create_user(email='dup@test.com', username='u2', password='pass123')

    def test_str(self):
        user = User.objects.create_user(email='str@test.com', username='str', password='pass123')
        self.assertEqual(str(user), 'str@test.com')


class MasterProfileSignalTest(TestCase):
    def test_master_profile_created_on_master_user(self):
        user = User.objects.create_user(
            email='m@test.com', username='masteruser', password='pass123',
            role=User.Role.MASTER
        )
        self.assertTrue(MasterProfile.objects.filter(user=user).exists())
        self.assertEqual(user.master_profile.display_name, 'masteruser')

    def test_no_profile_for_admin(self):
        user = User.objects.create_user(
            email='a@test.com', username='adminuser', password='pass123',
            role=User.Role.ADMIN
        )
        self.assertFalse(MasterProfile.objects.filter(user=user).exists())


class RegisterViewTest(TestCase):
    def test_register_page_loads(self):
        resp = self.client.get(reverse('register'))
        self.assertEqual(resp.status_code, 200)

    def test_register_creates_user_and_logs_in(self):
        resp = self.client.post(reverse('register'), {
            'email': 'new@test.com',
            'username': 'newuser',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(email='new@test.com')
        self.assertTrue(user.is_master)
        self.assertTrue(MasterProfile.objects.filter(user=user).exists())

    def test_register_duplicate_email_fails(self):
        User.objects.create_user(email='dup@test.com', username='u1', password='pass123')
        resp = self.client.post(reverse('register'), {
            'email': 'dup@test.com',
            'username': 'u2',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(resp.status_code, 200)  # form re-rendered
        self.assertContains(resp, 'form')


class LoginViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='login@test.com', username='loginuser', password='pass123'
        )

    def test_login_page_loads(self):
        resp = self.client.get(reverse('login'))
        self.assertEqual(resp.status_code, 200)

    def test_login_with_email(self):
        resp = self.client.post(reverse('login'), {
            'username': 'login@test.com',
            'password': 'pass123',
        })
        self.assertEqual(resp.status_code, 302)

    def test_login_wrong_password(self):
        resp = self.client.post(reverse('login'), {
            'username': 'login@test.com',
            'password': 'wrong',
        })
        self.assertEqual(resp.status_code, 200)


class LogoutViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='logout@test.com', username='logoutuser', password='pass123'
        )

    def test_logout(self):
        self.client.login(username='logout@test.com', password='pass123')
        resp = self.client.post(reverse('logout'))
        self.assertEqual(resp.status_code, 302)
