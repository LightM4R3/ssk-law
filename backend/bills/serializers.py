"""DRF serializers for the bills app – matches API_SPEC.md response shapes."""

from rest_framework import serializers
from .models import Bill, BillCategory, BillSummary, Category, SimilarBill
from .services.similarity import SIMILARITY_METHOD


class CategorySerializer(serializers.Serializer):
    """GET /api/categories 응답 아이템."""

    id = serializers.CharField(source="slug")
    label = serializers.CharField()
    count = serializers.IntegerField()


class CategoryNestedSerializer(serializers.Serializer):
    """법안 내 categories 배열 아이템."""

    id = serializers.CharField(source="category.slug")
    label = serializers.CharField(source="category.label")


class SimilarBillSerializer(serializers.ModelSerializer):
    targetId = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    stage = serializers.SerializerMethodField()

    class Meta:
        model = SimilarBill
        fields = ["targetId", "title", "date", "stage", "score", "rank", "method"]

    def get_targetId(self, similar):
        return similar.target_bill.bill_id if similar.target_bill else ""

    def get_title(self, similar):
        return similar.target_bill.title if similar.target_bill else similar.title

    def get_date(self, similar):
        if similar.target_bill and similar.target_bill.proposed_at:
            return similar.target_bill.proposed_at.strftime("%Y.%m.%d")
        return similar.date

    def get_stage(self, similar):
        return similar.target_bill.get_stage_display() if similar.target_bill else similar.stage_label


class BillListSerializer(serializers.Serializer):
    """GET /api/bills, GET /api/home/picks 응답 아이템."""

    id = serializers.CharField(source="bill_id")
    title = serializers.CharField()
    categories = serializers.SerializerMethodField()
    proposedAt = serializers.SerializerMethodField()
    proposer = serializers.CharField()
    stage = serializers.CharField()
    resultStatus = serializers.CharField(source="result_status")
    resultText = serializers.CharField(source="result_text")
    summary = serializers.SerializerMethodField()
    sentiment = serializers.SerializerMethodField()
    comments = serializers.IntegerField(source="view_count")  # view_count doubles as comments for MVP
    impact = serializers.SerializerMethodField()
    similar = serializers.SerializerMethodField()
    summaryStatus = serializers.SerializerMethodField()

    def get_categories(self, bill):
        bcs = bill.bill_categories.select_related("category").order_by("-is_primary")
        return [
            {"id": bc.category.slug, "label": bc.category.label}
            for bc in bcs
        ]

    def get_proposedAt(self, bill):
        return bill.proposed_at.strftime("%Y.%m.%d") if bill.proposed_at else ""

    def get_summary(self, bill):
        try:
            s = bill.summary
        except BillSummary.DoesNotExist:
            return []
        parts = [s.summary_1, s.summary_2, s.summary_3]
        return [p for p in parts if p]

    def get_sentiment(self, bill):
        try:
            return bill.summary.sentiment
        except BillSummary.DoesNotExist:
            return 0

    def get_impact(self, bill):
        try:
            return bill.summary.impact
        except BillSummary.DoesNotExist:
            return ""

    def get_similar(self, bill):
        if not self.context.get("include_similar", False):
            return []
        sims = (
            SimilarBill.objects
            .filter(source_bill=bill)
            .filter(method=SIMILARITY_METHOD)
            .select_related("target_bill")
            .order_by("rank", "-score")
        )
        return SimilarBillSerializer(sims, many=True).data

    def get_summaryStatus(self, bill):
        try:
            bill.summary
            return "ready"
        except BillSummary.DoesNotExist:
            pass

        tasks = [
            task
            for task in bill.processing_tasks.all()
            if task.processor == "summary"
        ]
        if not tasks:
            return "pending"
        status = tasks[-1].status
        return {
            "running": "running",
            "failed": "failed",
            "pending": "pending",
            "retry": "pending",
            "succeeded": "pending",
        }.get(status, "pending")


class BillDetailSerializer(BillListSerializer):
    """GET /api/bills/{bill_id} 응답."""

    billNo = serializers.CharField(source="bill_no")
    committee = serializers.CharField()
    detailLink = serializers.CharField(source="detail_link")
    viewCount = serializers.IntegerField(source="view_count")
    syncedAt = serializers.DateTimeField(source="synced_at")

    # 상속된 필드에 추가 필드를 더함


class SearchResponseSerializer(serializers.Serializer):
    """POST /api/search 응답."""

    intro = serializers.CharField()
    ids = serializers.ListField(child=serializers.CharField())
    bills = BillListSerializer(many=True)
