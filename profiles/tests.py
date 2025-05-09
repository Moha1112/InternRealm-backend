from datetime import timezone
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from users.models import User
from .models import StudentProfile, CompanyProfile
from .views import serialize_company_profile, serialize_student_profile
import json

class ProfileTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create test users
        self.student_user = User.objects.create(
            email='student@test.com',
            role='student',
            is_verified=True
        )
        self.student_user.set_password('testpass123')
        self.student_user.save()
        
        self.company_user = User.objects.create(
            email='company@test.com',
            role='company',
            is_verified=True
        )
        self.company_user.set_password('testpass123')
        self.company_user.save()
        
        self.admin_user = User.objects.create(
            email='admin@test.com',
            role='admin',
            is_verified=True
        )
        self.admin_user.set_password('testpass123')
        self.admin_user.save()
        
        # Create profiles
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            bio="Computer science student",
            university="Tech University"
        )
        
        self.company_profile = CompanyProfile.objects.create(
            user=self.company_user,
            company_name="Test Corp",
            description="Test company description"
        )
        
        # Get auth tokens
        self.student_token = self._get_auth_token('student@test.com', 'testpass123')
        self.company_token = self._get_auth_token('company@test.com', 'testpass123')
        self.admin_token = self._get_auth_token('admin@test.com', 'testpass123')
    
    def _get_auth_token(self, email, password):
        response = self.client.post(
            reverse('login'),
            data=json.dumps({'email': email, 'password': password}),
            content_type='application/json'
        )
        return response.json()['token']
    
    def _auth_headers(self, token):
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}
    
    # --- Profile Access Tests ---
    
    def test_student_can_view_own_profile(self):
        response = self.client.get(
            reverse('profile_by_id', args=[self.student_user.id]),
            **self._auth_headers(self.student_token)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()['is_own_profile'])
        self.assertEqual(response.json()['profile']['basics']['bio'], "Computer science student")
    
    def test_company_cannot_view_student_gpa(self):
        response = self.client.get(
            reverse('profile_by_id', args=[self.student_user.id]),
            **self._auth_headers(self.company_token)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('gpa', response.json()['profile']['education'])
    
    def test_admin_can_view_all_fields(self):
        response = self.client.get(
            reverse('profile_by_id', args=[self.company_user.id]),
            **self._auth_headers(self.admin_token)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tax_id', response.json()['profile']['legal'])
    
    def test_unauthorized_access_blocked(self):
        # Student trying to view company profile
        response = self.client.get(
            reverse('profile_by_id', args=[self.company_user.id]),
            **self._auth_headers(self.student_token)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    # --- Profile Update Tests ---
    
    def test_student_can_update_own_profile(self):
        update_data = {
            'bio': 'Updated bio text',
            'university': 'New University'
        }
        response = self.client.patch(
            reverse('update_profile'),
            data=json.dumps(update_data),
            content_type='application/json',
            **self._auth_headers(self.student_token)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.bio, 'Updated bio text')
    
    def test_cannot_update_restricted_fields(self):
        update_data = {
            'gpa': 4.0,  # Should be ignored
            'bio': 'Should still update'
        }
        response = self.client.patch(
            reverse('update_profile'),
            data=json.dumps(update_data),
            content_type='application/json',
            **self._auth_headers(self.student_token)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_profile.refresh_from_db()
        self.assertNotEqual(self.student_profile.gpa, 4.0)
        self.assertEqual(self.student_profile.bio, 'Should still update')
    
    # --- Edge Cases ---
    
    def test_nonexistent_profile_returns_404(self):
        new_user = User.objects.create(email='new@test.com', role='student')
        response = self.client.get(
            reverse('profile_by_id', args=[new_user.id]),
            **self._auth_headers(self.admin_token)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_deleted_user_not_accessible(self):
        self.student_user.deleted_at = timezone.now()
        self.student_user.save()
        response = self.client.get(
            reverse('profile_by_id', args=[self.student_user.id]),
            **self._auth_headers(self.admin_token)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    # --- Serializer Tests ---
    
    def test_student_serializer_contains_expected_fields(self):
        data = serialize_student_profile(self.student_profile)
        self.assertIn('education', data)
        self.assertIn('preferences', data)
        self.assertEqual(data['basics']['bio'], self.student_profile.bio)
    
    def test_company_serializer_admin_vs_non_admin(self):
        admin_data = serialize_company_profile(self.company_profile, is_admin=True)
        non_admin_data = serialize_company_profile(self.company_profile, is_admin=False)
        
        self.assertIn('tax_id', admin_data['legal'])
        self.assertNotIn('tax_id', non_admin_data['legal'])

# class ProfileIntegrationTests(TestCase):
    
#     def _auth_headers(self, token):
#         return {'HTTP_AUTHORIZATION': f'Bearer {token}'}
    
    def test_full_profile_flow(self):
        # 1. Register
        register_data = {
            'email': 'new@test.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'student'
        }
        self.client.post(reverse('register'), data=register_data)
        
        # 2. Login
        login_res = self.client.post(reverse('login'), data={
            'email': 'new@test.com',
            'password': 'testpass123'
        })
        token = login_res.json()['token']
        
        # 3. Update profile
        update_res = self.client.patch(
            reverse('update_profile'),
            data={'bio': 'New bio'},
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        self.assertEqual(update_res.status_code, 200)
        
        # 4. Verify update
        profile_res = self.client.get(
            reverse('profile_by_id', args=[User.objects.last().id]),
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        self.assertEqual(profile_res.json()['profile']['basics']['bio'], 'New bio')

# class ProfilePerformanceTests(TestCase):
    
    # def _auth_headers(self, token):
    #     return {'HTTP_AUTHORIZATION': f'Bearer {token}'}
    
    @classmethod
    def setUpTestData(cls):
        # Create 100 test profiles
        for i in range(100):
            user = User.objects.create(email=f'test{i}@example.com', role='student')
            StudentProfile.objects.create(user=user, bio=f"Bio {i}")
    
    def test_multiple_profile_retrieval(self):
        with self.assertNumQueries(4):  # 1 for user, 1 for profile
            response = self.client.get(
                reverse('profile_by_id', args=[1]),
                **self._auth_headers(self.admin_token)
            )
            self.assertEqual(response.status_code, 200)