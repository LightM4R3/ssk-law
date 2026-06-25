from rest_framework import serializers

from bills.models import Bill

from .models import Comment, Post


class PostSerializer(serializers.ModelSerializer):
    billId = serializers.SlugRelatedField(
        source="bill",
        slug_field="bill_id",
        queryset=Bill.objects.all(),
        write_only=True,
    )
    bill = serializers.CharField(source="bill_id", read_only=True)
    billTitle = serializers.CharField(source="bill.title", read_only=True)
    userIdx = serializers.IntegerField(source="user_id", read_only=True)
    nickname = serializers.CharField(source="user.nickname", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)
    viewCount = serializers.IntegerField(source="view_count", read_only=True)
    commentCount = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "idx",
            "title",
            "content",
            "bill",
            "billTitle",
            "billId",
            "userIdx",
            "nickname",
            "createdAt",
            "updatedAt",
            "viewCount",
            "commentCount",
        ]
        read_only_fields = [
            "idx",
            "bill",
            "billTitle",
            "userIdx",
            "nickname",
            "createdAt",
            "updatedAt",
            "viewCount",
            "commentCount",
        ]

    def get_commentCount(self, post):
        if hasattr(post, "comment_count"):
            return post.comment_count
        return post.comments.filter(is_deleted=False).count()

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("제목을 입력해주세요.")
        return value

    def validate_content(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("내용을 입력해주세요.")
        return value


class PostUpdateSerializer(PostSerializer):
    class Meta(PostSerializer.Meta):
        fields = [
            "idx",
            "title",
            "content",
            "bill",
            "userIdx",
            "nickname",
            "createdAt",
            "updatedAt",
            "viewCount",
            "commentCount",
        ]


class CommentSerializer(serializers.ModelSerializer):
    postIdx = serializers.IntegerField(source="post_id", read_only=True)
    postTitle = serializers.CharField(source="post.title", read_only=True)
    postBillId = serializers.CharField(source="post.bill_id", read_only=True)
    billTitle = serializers.CharField(source="post.bill.title", read_only=True)
    parentIdx = serializers.PrimaryKeyRelatedField(
        source="parent",
        queryset=Comment.objects.all(),
        required=False,
        allow_null=True,
        default=None,
        write_only=True,
    )
    parent = serializers.IntegerField(source="parent_id", read_only=True)
    userIdx = serializers.IntegerField(source="user_id", read_only=True)
    nickname = serializers.CharField(source="user.nickname", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)
    viewCount = serializers.IntegerField(source="view_count", read_only=True)
    isDeleted = serializers.BooleanField(source="is_deleted", read_only=True)

    class Meta:
        model = Comment
        fields = [
            "idx",
            "postIdx",
            "postTitle",
            "postBillId",
            "billTitle",
            "parent",
            "parentIdx",
            "userIdx",
            "nickname",
            "content",
            "createdAt",
            "updatedAt",
            "viewCount",
            "isDeleted",
        ]
        read_only_fields = [
            "idx",
            "postIdx",
            "postTitle",
            "postBillId",
            "billTitle",
            "parent",
            "userIdx",
            "nickname",
            "createdAt",
            "updatedAt",
            "viewCount",
            "isDeleted",
        ]

    def validate_content(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("내용을 입력해주세요.")
        return value

    def validate_parentIdx(self, value):
        post = self.context.get("post")
        if value is not None and post is not None and value.post_id != post.idx:
            raise serializers.ValidationError("같은 게시글의 댓글에만 답글을 작성할 수 있습니다.")
        return value


    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:
            data["content"] = "삭제된 댓글입니다."
        return data


class CommentUpdateSerializer(CommentSerializer):
    class Meta(CommentSerializer.Meta):
        fields = [
            "idx",
            "postIdx",
            "postTitle",
            "postBillId",
            "billTitle",
            "parent",
            "userIdx",
            "nickname",
            "content",
            "createdAt",
            "updatedAt",
            "viewCount",
            "isDeleted",
        ]
