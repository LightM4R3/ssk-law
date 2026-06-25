from django.db import models


class Post(models.Model):
    idx = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    user = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        related_name="posts",
        db_column="user_idx",
    )
    bill = models.ForeignKey(
        "bills.Bill",
        to_field="bill_id",
        on_delete=models.CASCADE,
        related_name="posts",
        db_column="bill_id",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "post"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["bill", "-created_at"], name="idx_post_bill_created"),
            models.Index(fields=["user", "-created_at"], name="idx_post_user_created"),
        ]

    def __str__(self):
        return self.title


class Comment(models.Model):
    idx = models.BigAutoField(primary_key=True)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
        db_column="post_idx",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="replies",
        db_column="parent_idx",
        null=True,
        blank=True,
        default=None,
    )
    user = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        related_name="comments",
        db_column="user_idx",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "comment"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["post", "created_at"], name="idx_comment_post_time"),
            models.Index(fields=["parent", "created_at"], name="idx_comment_parent_time"),
        ]

    def __str__(self):
        return f"Comment {self.idx} on post {self.post_id}"

