from django.test import TestCase, Client
from django.urls import reverse
from django.utils.timezone import now, timedelta
from .models import User, Session, EmailVerificationToken, PasswordResetToken
import json
from uuid import uuid4
from profiles.models import StudentProfile, CompanyProfile

class UserModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            role='student',
            last_login=now()
        )
        self.user.set_password('testpass123')
        self.user.save()

    def test_password_hashing(self):
        """Test that passwords are properly hashed"""
        self.assertTrue(self.user.check_password('testpass123'))
        self.assertFalse(self.user.check_password('wrongpass'))

    def test_user_creation(self):
        """Test user creation and string representation"""
        self.assertEqual(str(self.user), 'test@example.com')
        self.assertEqual(self.user.role, 'student')

    def test_student_profile_creation(self):
        """Test student profile creation"""
        profile = StudentProfile.objects.create(
            user=self.user,
            bio='Test bio',
            university='Test University',
            major='Computer Science'
        )
        self.assertEqual(profile.user.email, 'test@example.com')
        self.assertEqual(profile.bio, 'Test bio')

    def test_company_profile_creation(self):
        """Test company profile creation"""
        company_user = User.objects.create(
            username='companyuser',
            email='company@example.com',
            role='company'
        )
        profile = CompanyProfile.objects.create(
            user=company_user,
            company_name='Test Company'
        )
        self.assertEqual(profile.company_name, 'Test Company')


class SessionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email='test@example.com',
            username='testuser',
            role='student'
        )

    def test_session_creation(self):
        """Test session creation and expiration"""
        session = Session.create_session(self.user)
        self.assertIsNotNone(session.token)
        self.assertFalse(session.is_expired)
        
        # Test expiration
        session.expire()
        self.assertTrue(session.is_expired)

    def test_session_expiration_check(self):
        """Test automatic session expiration"""
        session = Session.objects.create(
            user=self.user,
            expires_at=now() - timedelta(hours=1))
        
        # Should be considered expired
        self.assertTrue(session.expires_at < now())


class AuthViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            role='student',
            last_login=now()
        )
        self.user.set_password('testpass123')
        self.user.save()
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.me_url = reverse('me')
        self.refresh_url = reverse('refresh_token')

    def test_successful_login(self):
        """Test successful login returns token"""
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': 'test@example.com',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('token', data)
        
        # Verify session was created
        token = data['token']
        self.assertTrue(Session.objects.filter(token=token).exists())

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': 'test@example.com',
                'password': 'wrongpass'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['errno'], 0x11)

    def test_login_missing_fields(self):
        """Test login with missing fields"""
        response = self.client.post(
            self.login_url,
            data=json.dumps({'email': 'test@example.com'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['errno'], 0x10)

    def test_authenticated_me_endpoint(self):
        """Test accessing protected endpoint with valid token"""
        # First login to get token
        login_response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': 'test@example.com',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        token = login_response.json()['token']
        
        # Access protected endpoint
        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['user']['email'], 'test@example.com')

    def test_unauthenticated_me_endpoint(self):
        """Test accessing protected endpoint without token"""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, 401)

    def test_logout(self):
        """Test logout functionality"""
        # First login to get token
        login_response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': 'test@example.com',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        token = login_response.json()['token']
        
        # Logout
        response = self.client.post(
            self.logout_url,
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify session is expired
        session = Session.objects.get(token=token)
        self.assertTrue(session.is_expired)

    def test_token_refresh(self):
        """Test token refresh functionality"""
        # First login to get token
        login_response = self.client.post(
            self.login_url,
            data=json.dumps({
                'email': 'test@example.com',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        token = login_response.json()['token']
        
        # Refresh token
        response = self.client.post(
            self.refresh_url,
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    def test_expired_token_refresh(self):
        """Test refreshing an expired token"""
        # Create an expired session
        session = Session.objects.create(
            user=self.user,
            expires_at=now() - timedelta(hours=1))
        
        # Try to refresh
        response = self.client.post(
            self.refresh_url,
            HTTP_AUTHORIZATION=f'Bearer {session.token}'
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['errno'], 0x21)


class AuthDecoratorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email='test@example.com',
            username='testuser',
            role='student'
        )
        self.valid_session = Session.create_session(self.user)
        self.expired_session = Session.create_session(self.user)
        self.expired_session.expires_at = now() - timedelta(hours=1)
        self.expired_session.save()

    def test_valid_token(self):
        """Test decorator with valid token"""
        client = Client()
        response = client.get(
            reverse('me'),
            HTTP_AUTHORIZATION=f'Bearer {self.valid_session.token}'
        )
        self.assertEqual(response.status_code, 200)

    def test_missing_token(self):
        """Test decorator with missing token"""
        client = Client()
        response = client.get(reverse('me'))
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['errno'], 0x20)

    def test_expired_token(self):
        """Test decorator with expired token"""
        client = Client()
        response = client.get(
            reverse('me'),
            HTTP_AUTHORIZATION=f'Bearer {self.expired_session.token}'
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['errno'], 0x21)
        
        # Verify session was marked as expired
        self.expired_session.refresh_from_db()
        self.assertTrue(self.expired_session.is_expired)

class RegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.valid_data = {
            'email': 'new@example.com',
            'password': 'testpass123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'student'
        }

    def test_successful_student_registration(self):
        """Test successful student registration"""
        response = self.client.post(
            self.register_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['email'], 'new@example.com')
        
        # Verify user and profile were created
        user = User.objects.get(email='new@example.com')
        self.assertTrue(hasattr(user, 'student_profile'))
        self.assertFalse(hasattr(user, 'company_profile'))

    def test_successful_company_registration(self):
        """Test successful company registration"""
        data = self.valid_data.copy()
        data.update({
            'role': 'company',
            'company_name': 'Test Company'
        })
        
        response = self.client.post(
            self.register_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        # Verify company profile was created
        user = User.objects.get(email='new@example.com')
        self.assertTrue(hasattr(user, 'company_profile'))
        self.assertEqual(user.company_profile.company_name, 'Test Company')

    def test_missing_fields(self):
        """Test registration with missing fields"""
        data = self.valid_data.copy()
        del data['first_name']
        
        response = self.client.post(
            self.register_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['errno'], 0x30)

    def test_duplicate_email(self):
        """Test registration with duplicate email"""
        # First registration
        self.client.post(
            self.register_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        
        # Second registration with same email
        response = self.client.post(
            self.register_url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['errno'], 0x32)

    def test_invalid_role(self):
        """Test registration with invalid role"""
        data = self.valid_data.copy()
        data['role'] = 'invalid_role'
        
        response = self.client.post(
            self.register_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['errno'], 0x31)

class EmailVerificationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            email='test@example.com',
            is_verified=False
        )
        self.valid_token = EmailVerificationToken.create_token(self.user).token
        self.expired_token = EmailVerificationToken.objects.create(
            user=self.user,
            token=uuid4(),
            expires_at=now() - timedelta(hours=1)
        ).token

    def test_send_verification_email(self):
        response = self.client.post(
            reverse('send_verification_email'),
            data=json.dumps({'email': 'test@example.com'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
    def test_verify_email_success(self):
        response = self.client.post(
            reverse('verify_email'),
            data=json.dumps({'token': str(self.valid_token)}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

    def test_verify_email_expired_token(self):
        response = self.client.post(
            reverse('verify_email'),
            data=json.dumps({'token': str(self.expired_token)}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)


class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            email='test@example.com',
        )
        self.user.set_password('oldpassword')
        self.user.save()
        self.valid_token = PasswordResetToken.create_token(self.user).token
        self.expired_token = PasswordResetToken.objects.create(
            user=self.user,
            token=uuid4(),
            expires_at=now() - timedelta(hours=1)
        ).token

    def test_request_password_reset(self):
        response = self.client.post(
            reverse('request_password_reset'),
            data=json.dumps({'email': 'test@example.com'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

    def test_reset_password_success(self):
        response = self.client.post(
            reverse('reset_password'),
            data=json.dumps({
                'token': str(self.valid_token),
                'new_password': 'newpassword123'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))

    def test_reset_password_expired_token(self):
        response = self.client.post(
            reverse('reset_password'),
            data=json.dumps({
                'token': str(self.expired_token),
                'new_password': 'newpassword123'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)