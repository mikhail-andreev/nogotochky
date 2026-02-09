from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import MasterProfile, Salon, Service


class MasterProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='m@test.com', username='master', password='pass123',
            role=User.Role.MASTER
        )
        self.profile = self.user.master_profile

    def test_auto_slug_generation(self):
        self.assertEqual(self.profile.slug, 'master')

    def test_unique_slug_on_conflict(self):
        user2 = User.objects.create_user(
            email='m2@test.com', username='master2', password='pass123',
            role=User.Role.MASTER
        )
        # Set same display_name to trigger slug conflict
        user2.master_profile.display_name = 'master'
        user2.master_profile.slug = ''
        user2.master_profile.save()
        self.assertNotEqual(user2.master_profile.slug, self.profile.slug)

    def test_str(self):
        self.assertEqual(str(self.profile), 'master')

    def test_slug_preserved_on_save(self):
        self.profile.bio = 'Updated'
        self.profile.save()
        self.assertEqual(self.profile.slug, 'master')


class SalonModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='s@test.com', username='salonmaster', password='pass123',
            role=User.Role.MASTER
        )

    def test_create_salon(self):
        salon = Salon.objects.create(owner=self.user, name='Салон Анна')
        self.assertEqual(str(salon), 'Салон Анна')
        self.assertEqual(salon.owner, self.user)


class ServiceModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='sv@test.com', username='svcmaster', password='pass123',
            role=User.Role.MASTER
        )
        self.salon = Salon.objects.create(owner=self.user, name='Салон')

    def test_create_service(self):
        svc = Service.objects.create(
            owner=self.user, salon=self.salon,
            name='Маникюр', duration_min=60, price=2000
        )
        self.assertTrue(svc.is_active)
        self.assertIn('Маникюр', str(svc))


class MasterRequiredMixinTest(TestCase):
    def setUp(self):
        self.master = User.objects.create_user(
            email='mr@test.com', username='mr', password='pass123',
            role=User.Role.MASTER
        )
        self.admin = User.objects.create_user(
            email='ar@test.com', username='ar', password='pass123',
            role=User.Role.ADMIN
        )

    def test_anonymous_redirected(self):
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp.url)

    def test_admin_redirected(self):
        self.client.login(username='ar@test.com', password='pass123')
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 302)

    def test_master_can_access(self):
        self.client.login(username='mr@test.com', password='pass123')
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 200)


class ProfileViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='pv@test.com', username='pv', password='pass123',
            role=User.Role.MASTER
        )
        self.client.login(username='pv@test.com', password='pass123')

    def test_profile_view(self):
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('profile', resp.context)

    def test_profile_edit(self):
        resp = self.client.post(reverse('profile_edit'), {
            'display_name': 'Новое имя',
            'slug': 'novoe-imya',
            'phone': '+7 999',
            'bio': 'Тест',
        })
        self.assertEqual(resp.status_code, 302)
        self.user.master_profile.refresh_from_db()
        self.assertEqual(self.user.master_profile.display_name, 'Новое имя')


class SalonViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='sv2@test.com', username='sv2', password='pass123',
            role=User.Role.MASTER
        )
        self.client.login(username='sv2@test.com', password='pass123')

    def test_salon_view_empty(self):
        resp = self.client.get(reverse('salon'))
        self.assertEqual(resp.status_code, 200)

    def test_salon_create_and_edit(self):
        resp = self.client.post(reverse('salon_edit'), {
            'name': 'Мой салон',
            'address': 'ул. Тестовая',
            'description': '',
            'phone': '',
        })
        self.assertEqual(resp.status_code, 302)
        salon = Salon.objects.get(owner=self.user)
        self.assertEqual(salon.name, 'Мой салон')


class ServiceViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='svc@test.com', username='svc', password='pass123',
            role=User.Role.MASTER
        )
        self.salon = Salon.objects.create(owner=self.user, name='Салон')
        self.client.login(username='svc@test.com', password='pass123')

    def test_service_list_empty(self):
        resp = self.client.get(reverse('service_list'))
        self.assertEqual(resp.status_code, 200)

    def test_service_create(self):
        resp = self.client.post(reverse('service_create'), {
            'name': 'Маникюр',
            'duration_min': 60,
            'price': '2000.00',
            'description': '',
            'is_active': True,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Service.objects.filter(owner=self.user, name='Маникюр').exists())

    def test_service_edit(self):
        svc = Service.objects.create(
            owner=self.user, salon=self.salon,
            name='Старое', duration_min=30, price=1000
        )
        resp = self.client.post(reverse('service_edit', args=[svc.pk]), {
            'name': 'Новое',
            'duration_min': 45,
            'price': '1500.00',
            'description': '',
            'is_active': True,
        })
        self.assertEqual(resp.status_code, 302)
        svc.refresh_from_db()
        self.assertEqual(svc.name, 'Новое')

    def test_service_delete(self):
        svc = Service.objects.create(
            owner=self.user, salon=self.salon,
            name='Удалить', duration_min=30, price=1000
        )
        resp = self.client.post(reverse('service_delete', args=[svc.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Service.objects.filter(pk=svc.pk).exists())

    def test_cannot_edit_other_master_service(self):
        other = User.objects.create_user(
            email='other@test.com', username='other', password='pass123',
            role=User.Role.MASTER
        )
        other_salon = Salon.objects.create(owner=other, name='Другой')
        other_svc = Service.objects.create(
            owner=other, salon=other_salon,
            name='Чужая', duration_min=30, price=500
        )
        resp = self.client.post(reverse('service_edit', args=[other_svc.pk]), {
            'name': 'Взлом', 'duration_min': 30, 'price': '0',
            'description': '', 'is_active': True,
        })
        self.assertEqual(resp.status_code, 404)
