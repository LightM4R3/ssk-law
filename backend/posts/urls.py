from django.urls import path

from .views import (
    CommentDetailView,
    CommentListCreateView,
    PostDetailView,
    PostListCreateView,
    UserCommentListView,
)


urlpatterns = [
    path("posts", PostListCreateView.as_view(), name="post-list-create"),
    path("posts/<int:idx>", PostDetailView.as_view(), name="post-detail"),
    path(
        "posts/<int:post_idx>/comments",
        CommentListCreateView.as_view(),
        name="comment-list-create",
    ),
    path("comments/<int:idx>", CommentDetailView.as_view(), name="comment-detail"),
    path("users/<int:user_idx>/comments", UserCommentListView.as_view(), name="user-comment-list"),
]
