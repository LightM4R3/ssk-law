from django.contrib.auth.hashers import check_password as verify_password
from django.contrib.auth.hashers import make_password
from django.db import models


class Account(models.Model):
    idx = models.BigAutoField(primary_key=True)
    id = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)
    nickname = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "account"
        ordering = ["idx"]

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return verify_password(raw_password, self.password)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __str__(self):
        return self.id
