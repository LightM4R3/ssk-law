"""Integration test suite using standard library urllib to verify all SSK-Law API endpoints."""

import json
import urllib.request
import urllib.parse

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"


def http_get(url_path):
    url = f"{BASE_URL}{url_path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8")
            return resp.status, json.loads(data)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))
    except Exception as e:
        return 0, str(e)


def http_post(url_path, payload):
    url = f"{BASE_URL}{url_path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_data = resp.read().decode("utf-8")
            return resp.status, json.loads(resp_data)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))
    except Exception as e:
        return 0, str(e)


def test_categories():
    print("Testing GET /api/categories...")
    status, data = http_get("/api/categories")
    assert status == 200, f"Failed: {status}, {data}"
    assert "categories" in data, "No 'categories' key in response"
    print(f"  Success: Found {len(data['categories'])} categories.")
    for cat in data["categories"]:
        print(f"    - {cat['label']} ({cat['id']}): {cat['count']} bills")


def test_picks():
    print("\nTesting GET /api/home/picks...")
    status, data = http_get("/api/home/picks")
    assert status == 200, f"Failed: {status}, {data}"
    assert "picks" in data, "No 'picks' key in response"
    print(f"  Success: Found {len(data['picks'])} picks.")
    if data["picks"]:
        p = data["picks"][0]
        print(f"    - Top Pick: {p['title']}")
        print(f"      Summary: {p['summary']}")
        print(f"      Sentiment: {p['sentiment']}")


def test_bills():
    print("\nTesting GET /api/bills...")
    status, data = http_get("/api/bills")
    assert status == 200, f"Failed: {status}, {data}"
    assert "bills" in data, "No 'bills' key in response"
    assert "pagination" in data, "No 'pagination' key in response"
    print(f"  Success: Found {len(data['bills'])} bills (Total: {data['pagination']['total_count']}).")

    print("Testing GET /api/bills?category=labor...")
    status, data = http_get("/api/bills?category=labor")
    assert status == 200, f"Failed: {status}"
    print(f"  Success: Found {len(data['bills'])} labor bills.")
    for b in data["bills"]:
        print(f"    - {b['title']} (Cats: {b['categories']})")

    print("Testing GET /api/bills?sort=-view_count&page_size=3...")
    status, data = http_get("/api/bills?sort=-view_count&page_size=3")
    assert status == 200, f"Failed: {status}"
    print("  Success: Top 3 viewed bills:")
    for i, b in enumerate(data["bills"]):
        print(f"    {i+1}. {b['title']} (Views: {b['comments']})")


def test_bill_detail():
    # Get a real bill_id dynamically from the bills list
    status, data = http_get("/api/bills")
    assert status == 200, f"Failed to get bills list: {status}, {data}"
    assert "bills" in data and data["bills"], "No bills available to test detail view"
    bill_id = data["bills"][0]["id"]

    print(f"\nTesting GET /api/bills/{bill_id}...")
    status, data = http_get(f"/api/bills/{bill_id}")
    assert status == 200, f"Failed: {status}, {data}"
    assert data["id"] == bill_id, f"Incorrect id returned: {data['id']}"
    print(f"  Success: Detailed bill '{data['title']}' loaded.")
    print(f"    Committee: {data['committee']}")
    print(f"    Similar Bills: {[s['title'] for s in data['similar']]}")


def test_search():
    print("\nTesting POST /api/search (AI Search)...")
    payload = {"query": "청년 월세 지원 정책"}
    status, data = http_post("/api/search", payload)
    assert status == 200, f"Failed: {status}, {data}"
    assert "intro" in data, "No 'intro' in response"
    assert "ids" in data, "No 'ids' in response"
    assert "bills" in data, "No 'bills' in response"
    print("  Success: AI Search Response received.")
    print(f"    AI Intro: {data['intro']}")
    print(f"    Matched Bills: {[b['title'] for b in data['bills']]}")


def test_chat_and_history():
    print("\nTesting POST /api/chat (AI Chatbot)...")
    payload = {"message": "플랫폼 노동자 보호법이 통과되면 배달 기사에게 어떤 변화가 있어?"}
    status, data = http_post("/api/chat", payload)
    assert status == 200, f"Failed: {status}, {data}"
    assert "session_key" in data, "No 'session_key' in response"
    assert "reply" in data, "No 'reply' in response"
    assert "related_bills" in data, "No 'related_bills' in response"
    session_key = data["session_key"]
    print("  Success: Chat reply received.")
    print(f"    Session Key: {sessionKey_mask(session_key)}")
    print(f"    AI Reply (First 150 chars): {data['reply'][:150]}...")
    print(f"    Related Bills: {[b['title'] for b in data['related_bills']]}")

    print("\nTesting GET /api/chat/history...")
    status, data = http_get(f"/api/chat/history?session_key={session_key}")
    assert status == 200, f"Failed: {status}, {data}"
    assert len(data["messages"]) >= 2, "History does not contain expected messages"
    print(f"  Success: Chat history loaded. Messages in session: {len(data['messages'])}")
    for msg in data["messages"]:
        print(f"    - [{msg['role']}]: {msg['content'][:60]}...")


def sessionKey_mask(key):
    return key[:8] + "-xxxx-xxxx-xxxx-" + key[-12:]


def main():
    print("=================== SSK-LAW API INTEGRATION TEST ===================")
    try:
        test_categories()
        test_picks()
        test_bills()
        test_bill_detail()
        test_search()
        test_chat_and_history()
        print("\n=================== ALL TESTS PASSED SUCCESSFULLY! ===================")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
