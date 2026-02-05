#!/usr/bin/env python3
"""
Gemini API 모델 테스트 스크립트
사용법: python test_gemini_models.py YOUR_API_KEY
"""
import sys
import requests
import json

def test_model(api_key, model_name):
    """모델이 작동하는지 테스트"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    payload = {
        "contents": [{
            "parts": [{"text": "Say hello in Korean"}]
        }]
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            return True, text[:50]
        else:
            error = response.json().get('error', {}).get('message', response.text[:100])
            return False, error
    except Exception as e:
        return False, str(e)

def list_models(api_key):
    """사용 가능한 모델 목록 조회"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            models = []
            for m in data.get('models', []):
                name = m.get('name', '').replace('models/', '')
                methods = m.get('supportedGenerationMethods', [])
                if 'generateContent' in methods:
                    models.append(name)
            return models
        else:
            return []
    except:
        return []

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python test_gemini_models.py YOUR_API_KEY")
        sys.exit(1)

    api_key = sys.argv[1]

    print("=" * 50)
    print("Gemini API 모델 테스트")
    print("=" * 50)

    # 사용 가능한 모델 목록 조회
    print("\n📋 사용 가능한 모델 조회 중...")
    available = list_models(api_key)
    if available:
        print(f"✅ {len(available)}개 모델 발견:")
        for m in available[:10]:
            print(f"   - {m}")
        if len(available) > 10:
            print(f"   ... 외 {len(available) - 10}개")
    else:
        print("❌ 모델 목록 조회 실패")

    # 테스트할 모델들
    test_models = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-pro",
    ]

    print("\n🧪 모델 테스트 중...")
    working_models = []

    for model in test_models:
        success, result = test_model(api_key, model)
        if success:
            print(f"   ✅ {model}: 작동함 - {result}...")
            working_models.append(model)
        else:
            print(f"   ❌ {model}: {result[:60]}")

    print("\n" + "=" * 50)
    if working_models:
        print(f"✅ 작동하는 모델: {', '.join(working_models)}")
        print(f"\n권장 설정: model_options = {working_models}")
    else:
        print("❌ 작동하는 모델이 없습니다. API 키를 확인하세요.")
    print("=" * 50)
