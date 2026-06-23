from datetime import datetime
import math

from django.conf import settings
from django.db.models import Count, F, Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import generics, permissions
from rest_framework.response import Response

from .models import Comment, Post
from .serializers import (
    CommentSerializer,
    CommentUpdateSerializer,
    PostSerializer,
    PostUpdateSerializer,
)


POST_VIEW_SESSION_KEY = "post_viewed_at"
POST_VIEW_COOLDOWN_SECONDS = getattr(
    settings,
    "POST_VIEW_COUNT_SESSION_COOLDOWN_SECONDS",
    30 * 60,
)
POST_LIST_DEFAULT_PAGE_SIZE = 10
POST_LIST_MAX_PAGE_SIZE = 50
POST_SORT_FIELDS = {
    "latest": ("-created_at", "-idx"),
    "popular": ("-view_count", "-created_at", "-idx"),
}


def _positive_int(value, default):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


class IsPostOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and obj.user_id == request.user.idx)


class IsCommentOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and obj.user_id == request.user.idx)


@method_decorator(csrf_protect, name="dispatch")
class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = Post.objects.select_related("user", "bill").annotate(
            comment_count=Count(
                "comments",
                filter=Q(comments__is_deleted=False),
            )
        )
        bill_id = self.request.query_params.get("billId") or self.request.query_params.get("bill")
        if bill_id:
            queryset = queryset.filter(bill_id=bill_id)
        user_id = self.request.query_params.get("userId") or self.request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        sort = self.request.query_params.get("sort", "latest")
        queryset = queryset.order_by(*POST_SORT_FIELDS.get(sort, POST_SORT_FIELDS["latest"]))
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = _positive_int(request.query_params.get("page"), 1)
        page_size = min(
            _positive_int(
                request.query_params.get("page_size"),
                POST_LIST_DEFAULT_PAGE_SIZE,
            ),
            POST_LIST_MAX_PAGE_SIZE,
        )
        total_count = queryset.count()
        total_pages = max(1, math.ceil(total_count / page_size))
        offset = (page - 1) * page_size
        posts = queryset[offset : offset + page_size]

        serializer = self.get_serializer(posts, many=True)
        return Response(
            {
                "posts": serializer.data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                },
            }
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@method_decorator(csrf_protect, name="dispatch")
class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.select_related("user", "bill").annotate(
        comment_count=Count(
            "comments",
            filter=Q(comments__is_deleted=False),
        )
    )
    lookup_field = "idx"
    lookup_url_kwarg = "idx"

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny(), IsPostOwnerOrReadOnly()]
        return [permissions.IsAuthenticated(), IsPostOwnerOrReadOnly()]

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return PostSerializer
        return PostUpdateSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self._increase_view_count_once_per_session(request, instance)
        instance.refresh_from_db(fields=["view_count"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def _increase_view_count_once_per_session(self, request, post):
        now = timezone.now()
        viewed_at = request.session.get(POST_VIEW_SESSION_KEY, {})
        post_key = str(post.idx)
        last_seen = viewed_at.get(post_key)

        if last_seen:
            try:
                last_seen_at = datetime.fromisoformat(last_seen)
                if timezone.is_naive(last_seen_at):
                    last_seen_at = timezone.make_aware(last_seen_at, timezone.get_current_timezone())
                if (now - last_seen_at).total_seconds() < POST_VIEW_COOLDOWN_SECONDS:
                    return
            except ValueError:
                pass

        Post.objects.filter(idx=post.idx).update(view_count=F("view_count") + 1)
        viewed_at[post_key] = now.isoformat()
        request.session[POST_VIEW_SESSION_KEY] = viewed_at
        request.session.modified = True


@method_decorator(csrf_protect, name="dispatch")
class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return Comment.objects.select_related("user", "post", "parent").filter(
            post_id=self.kwargs["post_idx"]
        )

    def list(self, request, *args, **kwargs):
        post = generics.get_object_or_404(Post, idx=self.kwargs["post_idx"])
        comments = list(self.get_queryset())
        serializer = self.get_serializer(comments, many=True)
        flat_comments = list(serializer.data)

        by_idx = {comment["idx"]: {**comment, "replies": []} for comment in flat_comments}
        roots = []
        for comment in by_idx.values():
            parent_idx = comment["parent"]
            if parent_idx and parent_idx in by_idx:
                by_idx[parent_idx]["replies"].append(comment)
            else:
                roots.append(comment)

        return Response(
            {
                "postIdx": post.idx,
                "comments": roots,
                "flatComments": flat_comments,
                "count": len(flat_comments),
            }
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method not in permissions.SAFE_METHODS:
            context["post"] = generics.get_object_or_404(Post, idx=self.kwargs["post_idx"])
        return context

    def perform_create(self, serializer):
        post = serializer.context["post"]
        serializer.save(user=self.request.user, post=post)


@method_decorator(csrf_protect, name="dispatch")
class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.select_related("user", "post", "parent")
    lookup_field = "idx"
    lookup_url_kwarg = "idx"

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny(), IsCommentOwnerOrReadOnly()]
        return [permissions.IsAuthenticated(), IsCommentOwnerOrReadOnly()]

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return CommentSerializer
        return CommentUpdateSerializer

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted", "updated_at"])


class UserCommentListView(generics.ListAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Comment.objects.select_related("user", "post", "post__bill", "parent").filter(
            user_id=self.kwargs["user_idx"]
        ).order_by("-created_at", "-idx")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = _positive_int(request.query_params.get("page"), 1)
        page_size = min(
            _positive_int(
                request.query_params.get("page_size"),
                POST_LIST_DEFAULT_PAGE_SIZE,
            ),
            POST_LIST_MAX_PAGE_SIZE,
        )
        total_count = queryset.count()
        total_pages = max(1, math.ceil(total_count / page_size))
        offset = (page - 1) * page_size
        comments = queryset[offset : offset + page_size]

        serializer = self.get_serializer(comments, many=True)
        return Response(
            {
                "comments": serializer.data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                },
            }
        )
