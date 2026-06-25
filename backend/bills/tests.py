from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from unittest.mock import patch, MagicMock
import datetime
from bills.models import Bill, Category, BillCategory

class SyncBillsCommandTests(TestCase):
    @patch("requests.get")
    def test_sync_bills_and_forward_stage_update(self, mock_get):
        # 1. Setup mock responses for three API calls
        # Call 1: General bills list (page 1)
        mock_resp_bills = MagicMock()
        mock_resp_bills.status_code = 200
        mock_resp_bills.json.return_value = {
            "nzmimeepazxkubdpn": [
                {"head": [{"list_total_count": 2}]},
                {"row": [
                    {
                        "BILL_NO": "TEST001",
                        "BILL_NAME": "테스트 법안 1",
                        "PROPOSER": "국회의원 홍길동",
                        "COMMITTEE": "환경노동위원회",
                        "DETAIL_LINK": "http://example.com/1",
                        "PROPOSE_DT": "2026-05-20",
                        "PROC_RESULT": "위원회 심사" # committee
                    },
                    {
                        "BILL_NO": "TEST002",
                        "BILL_NAME": "테스트 법안 2",
                        "PROPOSER": "국회의원 이순신",
                        "COMMITTEE": "국토교통위원회",
                        "DETAIL_LINK": "http://example.com/2",
                        "PROPOSE_DT": "2026-05-21",
                        "PROC_RESULT": "발의" # proposed
                    }
                ]}
            ]
        }

        # Call 2: TVBPMBILL11 (Judiciary Committee)
        mock_resp_committee = MagicMock()
        mock_resp_committee.status_code = 200
        mock_resp_committee.json.return_value = {
            "TVBPMBILL11": [
                {"head": [{"list_total_count": 1}]},
                {"row": [
                    {
                        "BILL_NO": "TEST002",
                        "LAW_PROC_RESULT_CD": "가결",
                        "LAW_PROC_DT": "2026-05-22"
                    }
                ]}
            ]
        }

        # Call 3: nwbpacrgavhjryiph (Plenary)
        mock_resp_plenary = MagicMock()
        mock_resp_plenary.status_code = 200
        mock_resp_plenary.json.return_value = {
            "nwbpacrgavhjryiph": [
                {"head": [{"list_total_count": 1}]},
                {"row": [
                    {
                        "BILL_NO": "TEST001",
                        "PROC_RESULT_CD": "원안가결"
                    }
                ]}
            ]
        }

        mock_get.side_effect = [mock_resp_bills, mock_resp_committee, mock_resp_plenary]

        # 2. Run sync command
        call_command("sync_bills", pages=1)

        # 3. Assertions
        # Check if TEST001 was fetched as committee stage, but advanced to passed by Plenary API
        bill_1 = Bill.objects.get(bill_no="TEST001")
        self.assertEqual(bill_1.title, "테스트 법안 1")
        self.assertEqual(bill_1.stage, "passed") # committee -> plenary -> passed (via Plenary API)

        # Check if TEST002 was fetched as proposed, but advanced to plenary by Judiciary API
        bill_2 = Bill.objects.get(bill_no="TEST002")
        self.assertEqual(bill_2.title, "테스트 법안 2")
        self.assertEqual(bill_2.stage, "plenary") # proposed -> plenary (via Judiciary API)

        # Check category mappings
        self.assertTrue(bill_1.categories.filter(slug="labor").exists())
        self.assertTrue(bill_2.categories.filter(slug="housing").exists())

    @patch("requests.get")
    def test_stage_forward_only_protection(self, mock_get):
        # Test that bills already at higher stages do not get downgraded.
        # Setup: Create a bill with stage "passed"
        passed_bill = Bill.objects.create(
            bill_id="TEST003",
            bill_no="TEST003",
            title="이미 통과된 법안",
            proposer="홍길동",
            committee="환경노동위원회",
            stage="passed",
            proposed_at=datetime.date.today(),
            synced_at=timezone.now()
        )

        # Setup mock responses for sync_bills
        # General bills list includes TEST003 as "위원회 심사" (lower stage)
        mock_resp_bills = MagicMock()
        mock_resp_bills.status_code = 200
        mock_resp_bills.json.return_value = {
            "nzmimeepazxkubdpn": [
                {"head": [{"list_total_count": 1}]},
                {"row": [
                    {
                        "BILL_NO": "TEST003",
                        "BILL_NAME": "이미 통과된 법안",
                        "PROPOSER": "홍길동",
                        "COMMITTEE": "환경노동위원회",
                        "DETAIL_LINK": "http://example.com/3",
                        "PROPOSE_DT": "2026-05-20",
                        "PROC_RESULT": "위원회 심사"
                    }
                ]}
            ]
        }

        # TVBPMBILL11 (Judiciary) includes TEST003
        mock_resp_committee = MagicMock()
        mock_resp_committee.status_code = 200
        mock_resp_committee.json.return_value = {
            "TVBPMBILL11": [
                {"head": [{"list_total_count": 1}]},
                {"row": [
                    {
                        "BILL_NO": "TEST003",
                        "LAW_PROC_RESULT_CD": "가결",
                        "LAW_PROC_DT": "2026-05-22"
                    }
                ]}
            ]
        }

        # Plenary does not include TEST003 in this run
        mock_resp_plenary = MagicMock()
        mock_resp_plenary.status_code = 200
        mock_resp_plenary.json.return_value = {
            "nwbpacrgavhjryiph": [
                {"head": [{"list_total_count": 0}]},
                {"row": []}
            ]
        }

        mock_get.side_effect = [mock_resp_bills, mock_resp_committee, mock_resp_plenary]

        # Before syncing, it is "passed"
        self.assertEqual(passed_bill.stage, "passed")

        # Run command
        call_command("sync_bills", pages=1)

        # Confirm stage is NOT downgraded to "committee" or "plenary".
        # Why: Inside _normalize_stage or update_or_create, it might write the stage from nzmimeepazxkubdpn.
        # Ah, look at the update_or_create logic in sync_bills.py:
        # "stage": stage
        # That means update_or_create WILL update the database with stage="committee" (from "위원회 심사")!
        # Let's check sync_bills.py's update_or_create block:
        #
        # bill, created = Bill.objects.update_or_create(
        #     bill_id=bill_no,
        #     defaults={
        #         ...
        #         "stage": stage,
        #         ...
        #     }
        # )
        # This actually overwrites the stage of an existing bill in update_or_create defaults!
        # If the bill was already "passed" in DB, but the general API (nzmimeepazxkubdpn) returns it with PROC_RESULT="위원회 심사",
        # the update_or_create will overwrite it back to "committee" in the DB.
        # Then, if Plenary API mock doesn't return it in this run (e.g. not in the first 50 results), it will remain "committee".
        # This is a downgrade bug! We need to make sure we only update "stage" in `defaults` if the new stage is higher than the existing stage in DB,
        # or we shouldn't overwrite the stage if it's already higher in the DB.
        # Let's verify this in the test.
        # The test should check that it remains "passed".
        refreshed_bill = Bill.objects.get(bill_no="TEST003")
        self.assertEqual(refreshed_bill.stage, "passed")

