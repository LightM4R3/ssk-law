import re

from rest_framework import serializers

from .models import Account


class AccountSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=128,
        trim_whitespace=False,
    )

    class Meta:
        model = Account
        fields = ["idx", "id", "password", "nickname", "created_at", "updated_at"]
        read_only_fields = ["idx", "created_at", "updated_at"]

    def validate_id(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("아이디를 입력해 주세요.")
        return value

    def validate_nickname(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("닉네임을 입력해 주세요.")
        return value

    def validate_password(self, value):
        if not re.search(r"[a-z]", value):
            raise serializers.ValidationError("비밀번호에 영문 소문자가 포함되어야 합니다.")
        if not re.search(r"[A-Z]", value):
            raise serializers.ValidationError("비밀번호에 영문 대문자가 포함되어야 합니다.")
        if not re.search(r"\d", value):
            raise serializers.ValidationError("비밀번호에 숫자가 포함되어야 합니다.")
        return value

    def create(self, validated_data):
        raw_password = validated_data.pop("password")
        account = Account(**validated_data)
        account.set_password(raw_password)
        account.save()
        return account

    def update(self, instance, validated_data):
        raw_password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if raw_password is not None:
            instance.set_password(raw_password)
        instance.save()
        return instance


class PublicAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["idx", "nickname"]
