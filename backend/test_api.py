"""测试后端API是否正常工作"""
import requests
import json

BASE_URL = "http://127.0.0.1:8080"

def test_health():
    """测试健康检查接口"""
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Health check: {r.status_code} - {r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_model_info():
    """测试模型信息接口"""
    try:
        r = requests.get(f"{BASE_URL}/api/v1/model/info", timeout=10)
        print(f"Model info: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Model type: {data.get('data', {}).get('model_type')}")
            fi = data.get('data', {}).get('feature_importance', {})
            print(f"Feature count: {len(fi)}")
            print(f"Top 5 features: {list(fi.keys())[:5]}")
        return r.status_code == 200
    except Exception as e:
        print(f"Model info failed: {e}")
        return False

def test_predict():
    """测试预测接口"""
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/predict",
            json={"top_n": 10},
            timeout=30
        )
        print(f"Predict: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            stocks = data.get('data', {}).get('top_stocks', [])
            print(f"Top stocks count: {len(stocks)}")
            for i, s in enumerate(stocks[:5]):
                print(f"  {i+1}. {s['code']}: {s['score']:.4f}")
        return r.status_code == 200
    except Exception as e:
        print(f"Predict failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Testing Backend API")
    print("=" * 50)
    
    test_health()
    print()
    test_model_info()
    print()
    test_predict()
