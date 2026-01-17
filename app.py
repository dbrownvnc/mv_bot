# [수정됨] 쿼터 초과 시 자동으로 넉넉한 하위 버전으로 전환하는 로직
def generate_with_fallback(prompt, api_key, start_model="gemini-2.0-flash"):
    genai.configure(api_key=api_key)
    
    # [전략]
    # 1. 최신 모델(2.0 등)을 먼저 시도
    # 2. 429(쿼터 초과) 발생 시, 무료 한도가 넉넉한 1.5 Flash 계열로 즉시 전환
    # 3. 그래도 안 되면 구버전 1.0 Pro 시도
    
    fallback_chain = [
        start_model,               # 1순위: 지정된 모델 (예: 최신 버전)
        "gemini-1.5-flash",        # 2순위: [추천] 무료 쿼터가 가장 넉넉함 (하루 1500회 이상)
        "gemini-1.5-flash-8b",     # 3순위: 더 가볍고 빠른 모델
        "gemini-1.5-pro",          # 4순위: 성능은 좋으나 쿼터가 적을 수 있음
        "gemini-1.0-pro"           # 5순위: 최후의 보루 (구버전)
    ]
    
    # 중복 모델 제거 로직
    seen = set()
    unique_chain = []
    for m in fallback_chain:
        if m not in seen and m: # 빈 문자열 제외
            unique_chain.append(m)
            seen.add(m)

    last_error = None
    
    for model_name in unique_chain:
        try:
            # 모델 생성 시도
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            # 성공 시 약간의 대기 후 반환 (연속 호출 방지)
            time.sleep(1) 
            return response.text, model_name 
            
        except Exception as e:
            last_error = e
            error_str = str(e)
            
            # 429(Quota) 에러가 떴을 때 로그 출력 후 즉시 다음 모델로
            if "429" in error_str or "Quota" in error_str:
                print(f"⚠️ {model_name} 모델 쿼터 초과(429). 즉시 대안 모델로 전환합니다.")
                # st.toast(f"⚠️ {model_name} 한도 초과 -> {unique_chain[unique_chain.index(model_name)+1]}로 전환") # 필요 시 주석 해제
                time.sleep(0.5)
                continue
            
            # 그 외 에러(404 등)도 다음 모델 시도
            time.sleep(0.5)
            continue
            
    # 모든 모델 실패 시
    raise Exception(f"모든 모델이 실패했습니다. (마지막 에러: {last_error})\n다른 구글 계정의 키를 사용하거나 잠시 후 시도해주세요.")
