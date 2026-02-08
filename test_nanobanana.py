#!/usr/bin/env python3
"""
Nano Banana (Gemini Image) API 테스트 스크립트
사용법: python test_nanobanana.py YOUR_GEMINI_API_KEY
"""
import sys
import os

def test_nanobanana_image_generation(api_key):
    print("=" * 50)
    print("🍌 Nano Banana (Gemini Image) API 테스트")
    print("=" * 50)

    prompt = "A cute robot cat sitting on a neon-lit rooftop in Tokyo at night, cyberpunk style, no text"

    # google-genai SDK 테스트
    print("\n[테스트] google-genai SDK...")
    try:
        from google import genai
        from google.genai import types

        print("   ✅ google-genai 임포트 성공")

        client = genai.Client(api_key=api_key)
        print("   ✅ Client 생성 성공")

        # 여러 모델 시도
        models_to_try = [
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash-preview-image-generation",
        ]

        for model_name in models_to_try:
            print(f"\n   모델 테스트: {model_name}")
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=f"Generate an image: {prompt}",
                    config=types.GenerateContentConfig(
                        response_modalities=['Image', 'Text']
                    )
                )

                print(f"   응답 수신됨")

                # 응답 구조 확인
                if response.candidates:
                    print(f"   candidates 수: {len(response.candidates)}")
                    if response.candidates[0].content.parts:
                        print(f"   parts 수: {len(response.candidates[0].content.parts)}")

                        for i, part in enumerate(response.candidates[0].content.parts):
                            print(f"   part[{i}] 타입: {type(part)}")

                            if hasattr(part, 'inline_data') and part.inline_data is not None:
                                data_size = len(part.inline_data.data)
                                print(f"   ✅ 이미지 발견! (크기: {data_size} bytes)")

                                # 이미지 저장
                                with open("test_nanobanana_output.png", "wb") as f:
                                    f.write(part.inline_data.data)
                                print(f"   💾 저장됨: test_nanobanana_output.png")

                                # PIL로 확인
                                try:
                                    from PIL import Image
                                    from io import BytesIO
                                    img = Image.open(BytesIO(part.inline_data.data))
                                    print(f"   📐 이미지 크기: {img.size}")
                                except Exception as pil_err:
                                    print(f"   ⚠️ PIL 확인 실패: {pil_err}")

                                return True

                            elif hasattr(part, 'text') and part.text:
                                print(f"   📝 텍스트: {part.text[:100]}...")
                else:
                    print("   ❌ candidates 없음")

            except Exception as model_err:
                print(f"   ❌ {model_name} 오류: {model_err}")

    except ImportError as e:
        print(f"   ❌ google-genai 미설치: {e}")
        print("   설치 명령: pip install google-genai")
        return False

    except Exception as e:
        print(f"   ❌ 오류: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 50)
    print("결과 요약:")
    print("   - 이미지 생성: 실패")
    print("\n💡 확인사항:")
    print("   1. API 키가 유효한지 확인")
    print("   2. 무료 티어 할당량 초과 여부 확인")
    print("   3. 이미지 생성은 일부 지역/계정에서만 지원될 수 있음")
    print("=" * 50)
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("사용법: python test_nanobanana.py YOUR_GEMINI_API_KEY")
            print("또는 GOOGLE_API_KEY 환경변수 설정")
            sys.exit(1)
    else:
        api_key = sys.argv[1]

    success = test_nanobanana_image_generation(api_key)
    sys.exit(0 if success else 1)
