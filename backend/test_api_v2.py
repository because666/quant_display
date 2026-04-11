"""测试后端API"""
import requests

BASE_URL = "http://127.0.0.1:8080"

def test_health():
    print("Testing Health...")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"  Status: {r.status_code}, Response: {r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"  Failed: {e}")
        return False

def test_model_info():
    print("Testing Model Info...")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/model/info", timeout=10)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            fi = data.get("data", {}).get("feature_importance", {})
            print(f"  Feature count: {len(fi)}")
        return r.status_code == 200
    except Exception as e:
        print(f"  Failed: {e}")
        return False

def test_predict():
    print("Testing Predict...")
    try:
        r = requests.post(f"{BASE_URL}/api/v1/predict", json={"top_n": 5}, timeout=30)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            stocks = data.get("data", {}).get("top_stocks", [])
            print(f"  Top stocks count: {len(stocks)}")
            for s in stocks[:3]:
                code = s.get("code", "?")
                score = s.get("score", 0)
                print(f"    - {code}: {score:.4f}")
        return r.status_code == 200
    except Exception as e:
        print(f"  Failed: {e}")
        return False

def test_account():
    print("Testing Account List...")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/account", timeout=5)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  Response: {data}")
        return r.status_code == 200
    except Exception as e:
        print(f"  Failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    test_health()
    print()
    test_model_info()
    print()
    test_predict()
    print()
    test_account()
    print("=" * 50)
