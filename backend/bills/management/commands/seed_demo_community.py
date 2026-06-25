from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from random import Random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Account
from bills.models import Bill
from posts.models import Comment, Post


DEMO_PASSWORD = "DemoPass123"
COMMENT_TOTAL = 50
POST_TOTAL = 20
USER_TOTAL = 10


@dataclass(frozen=True)
class DemoUser:
    account_id: str
    nickname: str
    voice: str
    concern: str


DEMO_USERS = [
    DemoUser("demo_user01", "차분한서연", "차분하게 따져보는 편", "대상 기준이 명확한지"),
    DemoUser("demo_user02", "꼼꼼한민준", "숫자와 절차를 먼저 보는 편", "예산과 집행 방식"),
    DemoUser("demo_user03", "현실주의유진", "현장 적용 가능성을 중시하는 편", "실제로 체감될 변화"),
    DemoUser("demo_user04", "동네기록자", "생활 사례를 곁들여 말하는 편", "지역마다 차이가 생기지 않는지"),
    DemoUser("demo_user05", "느린독서가", "긴 호흡으로 읽고 정리하는 편", "설명이 충분히 쉬운지"),
    DemoUser("demo_user06", "청년사장준", "사업자 입장에서 보는 편", "소규모 사업장 부담"),
    DemoUser("demo_user07", "아이둘엄마", "가정과 돌봄 관점이 강한 편", "아이와 가족에게 미칠 영향"),
    DemoUser("demo_user08", "정책메모", "정책 효과를 비교해보는 편", "기존 제도와의 연결"),
    DemoUser("demo_user09", "궁금한해솔", "질문을 많이 던지는 편", "구체적인 신청 절차"),
    DemoUser("demo_user10", "퇴근길시민", "짧고 솔직하게 반응하는 편", "시민이 바로 이해할 수 있는지"),
]


POST_TITLES = [
    "{title} 보면서 제일 먼저 든 생각",
    "취지는 좋은데 현장 안내가 관건 같아요",
    "이 법안, 실제로 체감될 수 있을까요?",
    "{category} 쪽에서는 꽤 중요한 변화처럼 보여요",
    "좋은 방향이지만 기준이 더 궁금합니다",
    "법안 제목보다 요약을 보니 이해가 조금 됐어요",
    "이건 시행 과정까지 같이 봐야 할 것 같습니다",
    "관련 당사자 입장에서 보면 이런 점이 보여요",
    "원문까지 보니 기대되는 부분과 걱정되는 부분",
    "조금 더 쉽게 설명되면 좋겠다는 생각",
]


ROOT_COMMENTS = [
    "저도 비슷하게 봤어요. 취지는 이해되는데 실제 안내가 얼마나 빨리 나오는지가 중요할 것 같습니다.",
    "이 부분은 지자체나 현장 기관에서 해석을 다르게 하면 체감이 많이 달라질 것 같아요.",
    "대상 기준이 넓어 보이는데, 오히려 그래서 세부 기준이 더 필요해 보입니다.",
    "요약만 보면 좋아 보이지만 예산이나 담당 기관이 같이 정리되어야 설득력이 생길 것 같아요.",
    "관련된 분들은 환영할 수도 있겠지만, 준비 기간 없이 바로 적용되면 혼란도 있지 않을까요?",
    "저는 제목보다 요약 세 줄이 훨씬 이해가 잘 됐어요. 이런 식으로 계속 정리되면 좋겠습니다.",
    "현장에서는 서류나 신청 절차가 복잡하면 좋은 제도도 잘 안 쓰이더라고요.",
    "이 법안은 찬반보다도 실제 적용 사례를 같이 봐야 판단이 될 것 같습니다.",
    "기존 제도와 겹치는 부분이 있는지 궁금합니다. 중복 지원처럼 보이면 논란이 생길 수도 있어서요.",
    "시민 입장에서는 법안이 통과됐는지보다 언제부터 바뀌는지가 더 궁금한 것 같아요.",
]


REPLIES = [
    "맞아요. 시행령이나 세부 지침이 나와야 진짜 그림이 보일 것 같습니다.",
    "저도 그 지점이 궁금했어요. 특히 지역별 차이가 생기면 정보 접근성이 중요해질 것 같아요.",
    "동의합니다. 법안 자체보다 안내 방식이 친절해야 실제로 쓰일 것 같아요.",
    "그 부분은 원문 보기로 계속 추적해보면 좋겠네요. 단계가 바뀌는지도 같이 봐야 할 것 같고요.",
    "말씀처럼 예산과 담당 부처가 같이 설명되면 훨씬 납득하기 쉬울 것 같습니다.",
    "저도 비슷하게 느꼈습니다. 좋은 방향이어도 준비 기간이 없으면 현장에서 부담이 커질 수 있죠.",
    "그래서 관련 법안끼리 묶어서 보는 기능이 유용한 것 같아요. 맥락이 보여야 판단이 되니까요.",
    "일단 발의 단계에서는 기대와 우려를 같이 적어두고, 위원회 심사 때 다시 보는 게 좋겠습니다.",
]


class Command(BaseCommand):
    help = "Reset community data and create realistic demo accounts, posts, comments, and replies."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-accounts",
            action="store_true",
            help="Do not delete existing accounts. Demo accounts are still recreated if missing.",
        )
        parser.add_argument(
            "--password",
            default=DEMO_PASSWORD,
            help=f"Password for demo users. Default: {DEMO_PASSWORD}",
        )

    def handle(self, *args, **options):
        password = options["password"]
        bills = self._select_bills()
        if len(bills) < POST_TOTAL:
            raise CommandError(
                f"요약이 준비된 법안이 {POST_TOTAL}개 이상 필요합니다. 현재 선택 가능: {len(bills)}개"
            )

        with transaction.atomic():
            deleted = self._clear_existing(keep_accounts=options["keep_accounts"])
            accounts = self._create_accounts(password)
            posts = self._create_posts(accounts, bills)
            comments = self._create_comments(accounts, posts)

        self.stdout.write(self.style.SUCCESS("시연용 커뮤니티 데이터를 생성했습니다."))
        self.stdout.write(
            f"deleted={deleted} users={len(accounts)} posts={len(posts)} comments={len(comments)}"
        )
        self.stdout.write(f"demo password: {password}")

    def _clear_existing(self, keep_accounts=False):
        comment_count = Comment.objects.count()
        post_count = Post.objects.count()
        account_count = 0 if keep_accounts else Account.objects.count()

        Comment.objects.all().delete()
        Post.objects.all().delete()
        if keep_accounts:
            Account.objects.filter(id__startswith="demo_user").delete()
        else:
            Account.objects.all().delete()

        return {
            "accounts": account_count,
            "posts": post_count,
            "comments": comment_count,
        }

    def _create_accounts(self, password):
        accounts = []
        for user in DEMO_USERS:
            account = Account(id=user.account_id, nickname=user.nickname)
            account.set_password(password)
            account.save()
            accounts.append(account)
        return accounts

    def _select_bills(self):
        bills = list(
            Bill.objects.filter(summary__isnull=False)
            .select_related("summary")
            .prefetch_related("bill_categories__category")
            .order_by("-proposed_at", "bill_id")[:250]
        )

        buckets: dict[str, list[Bill]] = {}
        for bill in bills:
            key = self._primary_category_label(bill) or bill.committee or "기타"
            buckets.setdefault(key, []).append(bill)

        selected = []
        seen = set()
        while len(selected) < POST_TOTAL and any(buckets.values()):
            for key in list(buckets.keys()):
                bucket = buckets[key]
                if not bucket:
                    continue
                bill = bucket.pop(0)
                if bill.bill_id in seen:
                    continue
                selected.append(bill)
                seen.add(bill.bill_id)
                if len(selected) >= POST_TOTAL:
                    break

        return selected

    def _create_posts(self, accounts, bills):
        now = timezone.now()
        rng = Random(20260625)
        posts = []
        for index, bill in enumerate(bills[:POST_TOTAL]):
            user = accounts[index % len(accounts)]
            demo_user = DEMO_USERS[index % len(DEMO_USERS)]
            category = self._primary_category_label(bill) or "생활"
            title = POST_TITLES[index % len(POST_TITLES)].format(
                title=self._short_title(bill.title),
                category=category,
            )
            content = self._post_content(index, bill, demo_user, category)
            post = Post.objects.create(
                title=title,
                content=content,
                user=user,
                bill=bill,
                view_count=rng.randint(4, 38),
            )
            created_at = now - timedelta(days=8 - (index // 3), hours=index * 2)
            updated_at = created_at
            if index in {2, 5, 11, 16}:
                updated_at = created_at + timedelta(hours=6 + index)
            Post.objects.filter(pk=post.pk).update(created_at=created_at, updated_at=updated_at)
            post.created_at = created_at
            post.updated_at = updated_at
            posts.append(post)
        return posts

    def _create_comments(self, accounts, posts):
        now = timezone.now()
        comments = []
        for index, post in enumerate(posts[:10]):
            root_a = self._make_comment(accounts, post, index, None, ROOT_COMMENTS[index % len(ROOT_COMMENTS)], now)
            root_b = self._make_comment(accounts, post, index + 3, None, ROOT_COMMENTS[(index + 4) % len(ROOT_COMMENTS)], now)
            reply = self._make_comment(accounts, post, index + 6, root_a, REPLIES[index % len(REPLIES)], now)
            comments.extend([root_a, root_b, reply])

        for index, post in enumerate(posts[10:15], start=10):
            root_a = self._make_comment(accounts, post, index, None, ROOT_COMMENTS[index % len(ROOT_COMMENTS)], now)
            root_b = self._make_comment(accounts, post, index + 4, None, ROOT_COMMENTS[(index + 5) % len(ROOT_COMMENTS)], now)
            reply = self._make_comment(accounts, post, index + 7, root_a, REPLIES[index % len(REPLIES)], now)
            nested = self._make_comment(accounts, post, index + 9, reply, REPLIES[(index + 3) % len(REPLIES)], now)
            comments.extend([root_a, root_b, reply, nested])

        if len(comments) != COMMENT_TOTAL:
            raise CommandError(f"댓글 생성 수가 예상과 다릅니다. expected={COMMENT_TOTAL}, actual={len(comments)}")
        return comments

    def _make_comment(self, accounts, post, seed, parent, content, now):
        user = accounts[(seed + 1) % len(accounts)]
        if parent and parent.user_id == user.idx:
            user = accounts[(seed + 2) % len(accounts)]
        comment = Comment.objects.create(
            post=post,
            parent=parent,
            user=user,
            content=self._personalize_comment(content, seed),
            view_count=0,
            is_deleted=False,
        )
        created_at = post.created_at + timedelta(minutes=12 + seed * 7)
        if created_at > now:
            created_at = now - timedelta(minutes=seed + 1)
        updated_at = created_at
        if seed % 11 == 0:
            updated_at = created_at + timedelta(minutes=25)
        Comment.objects.filter(pk=comment.pk).update(created_at=created_at, updated_at=updated_at)
        comment.created_at = created_at
        comment.updated_at = updated_at
        return comment

    def _post_content(self, index, bill, demo_user, category):
        summary = self._summary_text(bill)
        opener = [
            f"{bill.title}을 읽어보니 {category} 분야에서 그냥 지나치기 어려운 내용처럼 느껴졌습니다.",
            f"처음에는 제목만 보고 감이 잘 안 왔는데, 요약을 보니 {category} 쪽 생활 변화와 연결되어 보였습니다.",
            f"이 법안은 큰 방향보다 실제 적용 방식이 더 중요해 보입니다.",
            f"저는 이 법안을 보면서 {demo_user.concern}가 가장 먼저 떠올랐습니다.",
        ][index % 4]
        middle = (
            f"핵심은 '{summary}' 정도로 이해했습니다. "
            f"{demo_user.voice}이라서 그런지, 좋은 취지와 별개로 현장에서 시민이 바로 이해할 수 있는 설명이 필요해 보였어요."
        )
        ending = [
            "특히 시행 시점, 담당 기관, 신청이나 신고 절차가 함께 정리되면 더 설득력이 있을 것 같습니다.",
            "찬성이나 반대보다도 이 법안이 실제로 어떤 사람에게 먼저 닿는지 계속 확인해보고 싶습니다.",
            "위원회 심사 과정에서 예산이나 현장 부담 이야기가 얼마나 다뤄지는지도 지켜볼 만하다고 봅니다.",
            "비슷한 법안들과 같이 보면 방향성이 더 잘 보일 것 같아서, 유사 법안도 함께 확인해보려 합니다.",
        ][index % 4]
        return f"{opener}\n\n{middle}\n\n{ending}"

    def _personalize_comment(self, content, seed):
        prefixes = ["", "저도요. ", "개인적으로는 ", "맞습니다. ", "조금 다르게 보면 "]
        suffixes = ["", " 계속 지켜봐야겠네요.", " 이 부분이 시연 때도 잘 보이면 좋겠습니다.", " 실제 사례가 더 붙으면 이해가 쉬울 듯합니다."]
        return f"{prefixes[seed % len(prefixes)]}{content}{suffixes[seed % len(suffixes)]}".strip()

    def _summary_text(self, bill):
        summary = getattr(bill, "summary", None)
        if not summary:
            return "요약 준비 중"
        for value in (summary.summary_1, summary.summary_2, summary.summary_3, summary.impact):
            value = (value or "").strip()
            if value:
                return value[:90]
        return "요약 준비 중"

    def _primary_category_label(self, bill):
        categories = list(bill.bill_categories.all())
        if not categories:
            return ""
        primary = next((mapping for mapping in categories if mapping.is_primary), categories[0])
        return primary.category.label

    def _short_title(self, title):
        value = (title or "").replace("일부개정법률안", "").replace("전부개정법률안", "").strip()
        return value[:28] if len(value) > 28 else value
