from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Account


class AccountApiTests(APITestCase):
    def setUp(self):
        self.list_url = reverse("account-list-create")
        self.login_url = reverse("auth-login")
        self.logout_url = reverse("auth-logout")
        self.me_url = reverse("auth-me")

    def create_account(self, account_id="tester", nickname="테스터"):
        return self.client.post(
            self.list_url,
            {
                "id": account_id,
                "password": "Password123",
                "nickname": nickname,
            },
            format="json",
        )

    def login(self, account_id="tester", password="Password123"):
        return self.client.post(
            self.login_url,
            {"id": account_id, "password": password},
            format="json",
        )

    def test_create_account_hashes_password_and_hides_it(self):
        response = self.create_account()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)
        account = Account.objects.get(idx=response.data["idx"])
        self.assertNotEqual(account.password, "Password123")
        self.assertTrue(account.check_password("Password123"))

    def test_list_and_retrieve_accounts(self):
        created = self.create_account().data
        self.login()

        list_response = self.client.get(self.list_url)
        detail_response = self.client.get(
            reverse("account-detail", kwargs={"idx": created["idx"]})
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertNotIn("password", list_response.data[0])
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["id"], "tester")

    def test_patch_account_updates_nickname_and_password(self):
        created = self.create_account().data
        self.login()
        detail_url = reverse("account-detail", kwargs={"idx": created["idx"]})

        response = self.client.patch(
            detail_url,
            {"nickname": "수정된닉네임", "password": "Newpassword123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("password", response.data)
        account = Account.objects.get(idx=created["idx"])
        self.assertEqual(account.nickname, "수정된닉네임")
        self.assertTrue(account.check_password("Newpassword123"))

    def test_delete_account(self):
        created = self.create_account().data
        self.login()

        response = self.client.delete(
            reverse("account-detail", kwargs={"idx": created["idx"]})
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Account.objects.filter(idx=created["idx"]).exists())

    def test_duplicate_id_and_nickname_are_rejected(self):
        self.create_account()

        duplicate_id = self.create_account(account_id="tester", nickname="다른닉네임")
        duplicate_nickname = self.create_account(account_id="another", nickname="테스터")

        self.assertEqual(duplicate_id.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(duplicate_nickname.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Account.objects.count(), 1)

    def test_password_must_be_at_least_eight_characters(self):
        response = self.client.post(
            self.list_url,
            {"id": "tester", "password": "short", "nickname": "테스터"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Account.objects.count(), 0)

    def test_password_requires_uppercase_lowercase_and_number(self):
        invalid_passwords = ["lowercase123", "UPPERCASE123", "NoNumbersHere"]

        for index, password in enumerate(invalid_passwords):
            response = self.client.post(
                self.list_url,
                {
                    "id": f"tester-{index}",
                    "password": password,
                    "nickname": f"테스터-{index}",
                },
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(Account.objects.count(), 0)

    def test_protected_account_endpoints_require_login(self):
        created = self.create_account().data

        list_response = self.client.get(self.list_url)
        detail_response = self.client.get(
            reverse("account-detail", kwargs={"idx": created["idx"]})
        )

        self.assertEqual(list_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(detail_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_account_can_only_access_itself(self):
        first = self.create_account().data
        second = self.create_account(account_id="other", nickname="다른사용자").data
        self.login()

        list_response = self.client.get(self.list_url)
        other_response = self.client.patch(
            reverse("account-detail", kwargs={"idx": second["idx"]}),
            {"nickname": "침범시도"},
            format="json",
        )

        self.assertEqual([item["idx"] for item in list_response.data], [first["idx"]])
        self.assertEqual(other_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_login_me_and_logout_session_flow(self):
        created = self.create_account().data

        login_response = self.login()
        me_response = self.client.get(self.me_url)
        logout_response = self.client.post(self.logout_url, format="json")
        after_logout = self.client.get(self.me_url)

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertEqual(login_response.data["account"]["idx"], created["idx"])
        self.assertNotIn("password", login_response.data["account"])
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["account"]["id"], "tester")
        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(after_logout.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_identifies_invalid_password(self):
        self.create_account()

        response = self.login(password="wrong-password")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["error"]["code"], "INVALID_PASSWORD")
        self.assertEqual(
            response.data["error"]["message"],
            "비밀번호가 올바르지 않습니다.",
        )

    def test_login_identifies_unknown_account(self):
        response = self.login(account_id="unknown")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["error"]["code"], "ACCOUNT_NOT_FOUND")
        self.assertEqual(
            response.data["error"]["message"],
            "존재하지 않는 아이디입니다.",
        )

    def test_login_and_signup_require_csrf_token(self):
        account = Account(id="tester", nickname="테스터")
        account.set_password("Password123")
        account.save()
        csrf_client = APIClient(enforce_csrf_checks=True)

        login_without_token = csrf_client.post(
            self.login_url,
            {"id": "tester", "password": "Password123"},
            format="json",
        )
        signup_without_token = csrf_client.post(
            self.list_url,
            {"id": "new-user", "password": "Password123", "nickname": "신규"},
            format="json",
        )

        csrf_client.get(reverse("auth-csrf"))
        csrf_token = csrf_client.cookies["csrftoken"].value
        login_with_token = csrf_client.post(
            self.login_url,
            {"id": "tester", "password": "Password123"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(login_without_token.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(signup_without_token.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(login_with_token.status_code, status.HTTP_200_OK)
