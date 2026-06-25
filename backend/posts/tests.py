import datetime

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Account
from bills.models import Bill

from .models import Comment, Post


class PostModelTests(APITestCase):
    def setUp(self):
        self.account = Account.objects.create(id="writer", nickname="Writer", password="unused")
        self.bill = Bill.objects.create(
            bill_id="POST-TEST-BILL",
            bill_no="2200001",
            title="Post test bill",
            proposer="Tester",
            committee="Test committee",
            proposed_at=datetime.date(2026, 6, 23),
        )
        self.post = Post.objects.create(
            title="Post title",
            content="Post content",
            user=self.account,
            bill=self.bill,
        )

    def test_post_references_account_idx_and_bill_id(self):
        self.assertEqual(self.post.user_id, self.account.idx)
        self.assertEqual(self.post.bill_id, self.bill.bill_id)
        self.assertEqual(self.post.view_count, 0)

    def test_comment_supports_nullable_parent_and_replies(self):
        root = Comment.objects.create(
            post=self.post,
            user=self.account,
            content="Root comment",
        )
        reply = Comment.objects.create(
            post=self.post,
            parent=root,
            user=self.account,
            content="Reply comment",
        )

        self.assertIsNone(root.parent_id)
        self.assertEqual(reply.parent_id, root.idx)
        self.assertEqual(list(root.replies.values_list("idx", flat=True)), [reply.idx])
        self.assertFalse(reply.is_deleted)
        self.assertEqual(reply.view_count, 0)

    def test_hard_deleted_parent_does_not_delete_reply(self):
        root = Comment.objects.create(post=self.post, user=self.account, content="Parent")
        reply = Comment.objects.create(
            post=self.post,
            parent=root,
            user=self.account,
            content="Reply survives",
        )

        root.delete()

        reply.refresh_from_db()
        self.assertIsNone(reply.parent_id)


class PostApiTests(APITestCase):
    def setUp(self):
        self.writer = Account.objects.create(id="writer", nickname="Writer", password="unused")
        self.writer.set_password("Password123")
        self.writer.save()
        self.other = Account.objects.create(id="other", nickname="Other", password="unused")
        self.other.set_password("Password123")
        self.other.save()
        self.bill = Bill.objects.create(
            bill_id="API-POST-BILL",
            bill_no="2200002",
            title="API post bill",
            proposer="Tester",
            committee="Test committee",
            proposed_at=datetime.date(2026, 6, 23),
        )
        self.post = Post.objects.create(
            title="Original title",
            content="Original content",
            user=self.writer,
            bill=self.bill,
        )

    def login_as(self, account):
        return self.client.post(
            reverse("auth-login"),
            {"id": account.id, "password": "Password123"},
            format="json",
        )

    def test_create_post_requires_login_session(self):
        response = self.client.post(
            reverse("post-list-create"),
            {"title": "New post", "content": "Body", "billId": self.bill.bill_id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logged_in_account_can_create_post(self):
        self.login_as(self.writer)

        response = self.client.post(
            reverse("post-list-create"),
            {"title": "New post", "content": "Body", "billId": self.bill.bill_id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["userIdx"], self.writer.idx)
        self.assertEqual(response.data["bill"], self.bill.bill_id)
        self.assertTrue(Post.objects.filter(title="New post", user=self.writer).exists())

    def test_only_author_can_update_or_delete_post(self):
        self.login_as(self.other)
        detail_url = reverse("post-detail", kwargs={"idx": self.post.idx})

        forbidden_update = self.client.patch(detail_url, {"title": "Blocked"}, format="json")
        forbidden_delete = self.client.delete(detail_url)

        self.assertEqual(forbidden_update.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(forbidden_delete.status_code, status.HTTP_403_FORBIDDEN)

        self.login_as(self.writer)
        update_response = self.client.patch(detail_url, {"title": "Updated"}, format="json")
        delete_response = self.client.delete(detail_url)

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["title"], "Updated")
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(idx=self.post.idx).exists())

    def test_read_increments_view_count_once_per_session_cooldown(self):
        detail_url = reverse("post-detail", kwargs={"idx": self.post.idx})

        first = self.client.get(detail_url)
        second = self.client.get(detail_url)

        self.post.refresh_from_db()
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["viewCount"], 1)
        self.assertEqual(second.data["viewCount"], 1)
        self.assertEqual(self.post.view_count, 1)

    def test_list_can_filter_by_bill_id_without_incrementing_view_count(self):
        response = self.client.get(reverse("post-list-create"), {"billId": self.bill.bill_id})

        self.post.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["posts"]), 1)
        self.assertEqual(response.data["posts"][0]["idx"], self.post.idx)
        self.assertEqual(response.data["pagination"]["page_size"], 10)
        self.assertEqual(self.post.view_count, 0)

    def test_list_can_filter_by_user_id(self):
        other_post = Post.objects.create(
            title="Other writer post",
            content="Body",
            user=self.other,
            bill=self.bill,
        )

        response = self.client.get(reverse("post-list-create"), {"userId": self.other.idx})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["pagination"]["total_count"], 1)
        self.assertEqual(response.data["posts"][0]["idx"], other_post.idx)
        self.assertEqual(response.data["posts"][0]["userIdx"], self.other.idx)

    def test_post_list_is_paginated_by_ten_items_by_default(self):
        for index in range(15):
            Post.objects.create(
                title=f"Extra post {index}",
                content="Body",
                user=self.writer,
                bill=self.bill,
            )

        first_page = self.client.get(reverse("post-list-create"), {"page": 1})
        second_page = self.client.get(reverse("post-list-create"), {"page": 2})

        self.assertEqual(first_page.status_code, status.HTTP_200_OK)
        self.assertEqual(second_page.status_code, status.HTTP_200_OK)
        self.assertEqual(len(first_page.data["posts"]), 10)
        self.assertEqual(len(second_page.data["posts"]), 6)
        self.assertEqual(first_page.data["pagination"]["total_count"], 16)
        self.assertEqual(first_page.data["pagination"]["total_pages"], 2)

    def test_post_list_can_sort_by_popular_view_count(self):
        low = Post.objects.create(
            title="Low views",
            content="Body",
            user=self.writer,
            bill=self.bill,
            view_count=2,
        )
        high = Post.objects.create(
            title="High views",
            content="Body",
            user=self.writer,
            bill=self.bill,
            view_count=9,
        )

        response = self.client.get(reverse("post-list-create"), {"sort": "popular"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["posts"][0]["idx"], high.idx)
        self.assertLess(
            response.data["posts"].index(next(item for item in response.data["posts"] if item["idx"] == high.idx)),
            response.data["posts"].index(next(item for item in response.data["posts"] if item["idx"] == low.idx)),
        )


class CommentApiTests(APITestCase):
    def setUp(self):
        self.writer = Account.objects.create(id="writer", nickname="Writer", password="unused")
        self.writer.set_password("Password123")
        self.writer.save()
        self.other = Account.objects.create(id="other", nickname="Other", password="unused")
        self.other.set_password("Password123")
        self.other.save()
        self.bill = Bill.objects.create(
            bill_id="API-COMMENT-BILL",
            bill_no="2200003",
            title="API comment bill",
            proposer="Tester",
            committee="Test committee",
            proposed_at=datetime.date(2026, 6, 23),
        )
        self.post = Post.objects.create(
            title="Post for comments",
            content="Post body",
            user=self.writer,
            bill=self.bill,
        )
        self.comment = Comment.objects.create(
            post=self.post,
            user=self.writer,
            content="Original comment",
        )

    def login_as(self, account):
        return self.client.post(
            reverse("auth-login"),
            {"id": account.id, "password": "Password123"},
            format="json",
        )

    def test_read_comments_does_not_require_login(self):
        list_response = self.client.get(
            reverse("comment-list-create", kwargs={"post_idx": self.post.idx})
        )
        detail_response = self.client.get(
            reverse("comment-detail", kwargs={"idx": self.comment.idx})
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["comments"][0]["idx"], self.comment.idx)
        self.assertEqual(list_response.data["flatComments"][0]["idx"], self.comment.idx)
        self.assertEqual(detail_response.data["content"], "Original comment")

    def test_comment_list_loads_comments_and_replies_for_post(self):
        reply = Comment.objects.create(
            post=self.post,
            parent=self.comment,
            user=self.other,
            content="Reply comment",
        )

        response = self.client.get(
            reverse("comment-list-create", kwargs={"post_idx": self.post.idx})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["postIdx"], self.post.idx)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["comments"]), 1)
        self.assertEqual(response.data["comments"][0]["idx"], self.comment.idx)
        self.assertEqual(response.data["comments"][0]["replies"][0]["idx"], reply.idx)
        self.assertEqual(response.data["flatComments"][1]["parent"], self.comment.idx)

    def test_user_comment_list_returns_comments_with_post_context(self):
        response = self.client.get(
            reverse("user-comment-list", kwargs={"user_idx": self.writer.idx})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["pagination"]["total_count"], 1)
        self.assertEqual(response.data["comments"][0]["idx"], self.comment.idx)
        self.assertEqual(response.data["comments"][0]["postIdx"], self.post.idx)
        self.assertEqual(response.data["comments"][0]["postTitle"], self.post.title)
        self.assertEqual(response.data["comments"][0]["billTitle"], self.bill.title)

    def test_create_comment_requires_login_session(self):
        response = self.client.post(
            reverse("comment-list-create", kwargs={"post_idx": self.post.idx}),
            {"content": "New comment"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logged_in_account_can_create_comment_and_reply(self):
        self.login_as(self.other)

        comment_response = self.client.post(
            reverse("comment-list-create", kwargs={"post_idx": self.post.idx}),
            {"content": "New comment"},
            format="json",
        )
        reply_response = self.client.post(
            reverse("comment-list-create", kwargs={"post_idx": self.post.idx}),
            {"content": "Reply comment", "parentIdx": self.comment.idx},
            format="json",
        )

        self.assertEqual(comment_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(reply_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(comment_response.data["userIdx"], self.other.idx)
        self.assertEqual(reply_response.data["parent"], self.comment.idx)

    def test_only_comment_author_can_update_or_delete_comment(self):
        self.login_as(self.other)
        detail_url = reverse("comment-detail", kwargs={"idx": self.comment.idx})

        forbidden_update = self.client.patch(
            detail_url,
            {"content": "Blocked update"},
            format="json",
        )
        forbidden_delete = self.client.delete(detail_url)

        self.assertEqual(forbidden_update.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(forbidden_delete.status_code, status.HTTP_403_FORBIDDEN)

        self.login_as(self.writer)
        update_response = self.client.patch(
            detail_url,
            {"content": "Updated comment"},
            format="json",
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["content"], "Updated comment")

    def test_delete_comment_marks_is_deleted_without_removing_row(self):
        self.login_as(self.writer)
        detail_url = reverse("comment-detail", kwargs={"idx": self.comment.idx})

        response = self.client.delete(detail_url)

        self.comment.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(self.comment.is_deleted)
        self.assertEqual(self.comment.content, "삭제된 댓글입니다.")
        self.assertTrue(Comment.objects.filter(idx=self.comment.idx).exists())

        detail_response = self.client.get(detail_url)
        list_response = self.client.get(
            reverse("comment-list-create", kwargs={"post_idx": self.post.idx})
        )
        update_response = self.client.patch(
            detail_url,
            {"content": "Deleted comment should not be editable"},
            format="json",
        )

        self.assertEqual(detail_response.data["content"], "삭제된 댓글입니다.")
        self.assertEqual(list_response.data["comments"][0]["content"], "삭제된 댓글입니다.")
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
