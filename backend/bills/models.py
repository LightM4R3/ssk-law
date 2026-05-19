"""Bills app models – matches DATABASE_SPEC.md exactly."""

from django.db import models


class Category(models.Model):
    """법안 분야 (노동, 복지, 주거 등)."""

    slug = models.CharField(max_length=30, unique=True)
    label = models.CharField(max_length=30)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "category"
        ordering = ["sort_order"]

    def __str__(self):
        return self.label


class Bill(models.Model):
    """국회 열린국회정보 API에서 수집한 법률 발의안."""

    STAGE_CHOICES = [
        ("proposed", "발의"),
        ("committee", "위원회 심사"),
        ("plenary", "본회의 상정"),
        ("passed", "통과 · 공포"),
    ]

    bill_id = models.CharField(max_length=50, unique=True, help_text="국회 API BILL_ID")
    bill_no = models.CharField(max_length=20, help_text="의안번호")
    title = models.CharField(max_length=500)
    proposer = models.CharField(max_length=200)
    committee = models.CharField(max_length=100, blank=True, default="")
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default="proposed")
    proposed_at = models.DateField()
    detail_link = models.URLField(max_length=500, blank=True, default="")
    age = models.IntegerField(default=22, help_text="국회 대수")
    view_count = models.IntegerField(default=0)
    synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # M:N through table
    categories = models.ManyToManyField(Category, through="BillCategory", related_name="bills")

    class Meta:
        db_table = "bill"
        ordering = ["-proposed_at"]
        indexes = [
            models.Index(fields=["-proposed_at"], name="idx_bill_proposed_at"),
            models.Index(fields=["stage"], name="idx_bill_stage"),
            models.Index(fields=["age"], name="idx_bill_age"),
        ]

    def __str__(self):
        return self.title


class BillCategory(models.Model):
    """법안-분야 M:N 매핑."""

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="bill_categories")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="bill_categories")
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "bill_category"
        unique_together = [("bill", "category")]

    def __str__(self):
        return f"{self.bill.title} – {self.category.label}"


class BillSummary(models.Model):
    """AI 생성 3줄 요약 (1:1)."""

    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name="summary")
    summary_1 = models.TextField()
    summary_2 = models.TextField(blank=True, default="")
    summary_3 = models.TextField(blank=True, default="")
    impact = models.TextField(blank=True, default="")
    sentiment = models.IntegerField(default=0, help_text="0-100")
    model_name = models.CharField(max_length=100, blank=True, default="")
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bill_summary"

    def __str__(self):
        return f"Summary: {self.bill.title[:40]}"


class SimilarBill(models.Model):
    """유사 법안 (기준 법안에 연결)."""

    source_bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="similar_bills")
    title = models.CharField(max_length=500)
    date = models.CharField(max_length=20, blank=True, default="")
    stage_label = models.CharField(max_length=30, blank=True, default="")

    class Meta:
        db_table = "similar_bill"
        indexes = [
            models.Index(fields=["source_bill"], name="idx_sb_source"),
        ]

    def __str__(self):
        return self.title
