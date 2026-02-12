import streamlit as st
import requests
import json
import base64
from bs4 import BeautifulSoup
import datetime
import pandas as pd

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="Bar Raiser Copilot", page_icon="✈️", layout="wide")

# --- 2. API 키 설정 ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키를 확인해주세요.")
    st.stop()

# --- 3. 공식 가이드 데이터 ---
VALUE_SYSTEM = {
    "Transform": [
        "1. Customer-First Innovation: 모든 결정은 고객에게 미치는 영향을 가장 먼저 고려해 이뤄집니다.",
        "2. Enduring Value Creation: 시간이 지날수록 더 큰 가치를 만들어내는 솔루션을 구축합니다.",
        "3. Excellence in Execution: 디지털 전환의 새로운 기준을 세웁니다."
    ],
    "Tomorrow": [
        "4. Active Learning: 고객 접점에서 발생하는 모든 경험을 공동의 지식으로 전환합니다.",
        "5. Forward Thinking: 미래를 고려해 확장성과 지속성을 갖춘 솔루션을 구축합니다.",
        "6. Speed with Impact: 성과는 빠르게 달성하면서도 장기적인 가치를 쌓아갑니다."
    ],
    "Together": [
        "7. Power of Three: 고객, 파트너, 그리고 우리 팀이 하나로 연결됩니다.",
        "8. Trust & Growth: 서로의 발전을 지원하며 함께 성장합니다.",
        "9. Global Perspective: 문화와 시장을 연결하는 가교 역할을 합니다."
    ]
}

LEVEL_GUIDELINES = {
    "IC-L3": "[기본기를 확립하는 실무자] 명확한 지시와 가이드 하에 업무 수행.",
    "IC-L4": "[자기완결성을 갖춘 독립적 실무자] 목표 내 업무를 독립적으로 계획/실행.",
    "IC-L5": "[성장을 지원하는 핵심 직무 전문가] 데이터/경험 기반의 최적 대안 제시 및 전파.",
    "IC-L6": "[조직 변화를 이끄는 선도적 전문가] 비효율 제거 및 성과 선순환 구조 구축.",
    "IC-L7": "[전사 혁신을 주도하는 최고 권위자] 업계 표준을 정의하는 최고 수준 전문성.",
    "M-L5": "[단일 기능 유닛 성장 리더] 유닛 운영 및 프로젝트 성공 리딩.",
    "M-L6": "[기능 통합 유닛 성장 리더] 유닛 성과와 유닛원 육성 성공 리딩.",
    "M-L7": "[핵심 조직 성장 리더] 전략 방향 및 조직 구조 총괄."
}

# --- 4. 핵심 함수 ---
def call_gemini_vision(prompt, pdf_file):
    try:
        pdf_base64 = base64.b64encode(pdf_file.getvalue()).decode('utf-8')
        target_model = "gemini-flash-latest"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={API_KEY}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "application/pdf", "data": pdf_base64}}
                ]
            }]
        }
        res = requests.post(url, headers=headers, data=json.dumps(data), timeout=60)
        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        return f"⚠️ 오류: {res.text}"
    except Exception as e:
        return f"⚠️ 시스템 에러: {str(e)}"

# --- 5. UI 세션 관리 ---
if "ai_questions" not in st.session_state: st.session_state.ai_questions = []
if "selected_qs_set" not in st.session_state: st.session_state.selected_qs_set = set()
if "memo_content" not in st.session_state: st.session_state.memo_content = ""

# --- 6. 사이드바 ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    selected_level = st.selectbox("레벨 선택", list(LEVEL_GUIDELINES.keys()))
    st.info(f"💡 {LEVEL_GUIDELINES[selected_level]}")
    
    resume_file = st.file_uploader("이력서 업로드", type="pdf")
    jd_input = st.text_area("JD 내용")
    
    btn = st.button("질문 설계 시작 🚀", type="primary", use_container_width=True)
    
    st.divider()
    with st.expander("ℹ️ System Version 3.8"):
        admin_pw = st.text_input("Access Key", type="password")
        mode = "Admin" if admin_pw == "admin1234" else "User"

# --- 7. 메인 화면 ---
if mode == "Admin":
    st.title("📊 Admin Dashboard")
    st.write("데이터 관리 및 로그 확인 페이지입니다.")
    # (삭제 기능 등 로직 유지)

else:
    st.title("✈️ Bar Raiser Copilot")
    
    # [1] 3T & 9VALUE 상단 고정 (기본적으로 닫아두어 공간 확보)
    with st.expander("💡 바레이저 판단 기준 (3T & 9VALUE) 확인하기"):
        c1, c2, c3 = st.columns(3)
        for i, category in enumerate(["Transform", "Tomorrow", "Together"]):
            with [c1, c2, c3][i]:
                st.markdown(f"**{category}**")
                for v in VALUE_SYSTEM[category]: st.caption(v)

    if btn:
        if resume_file and jd_input:
            prompt = f"""
            [Role] Bar Raiser Interviewer Assistant.
            [Target] {selected_level}. Framework: 3T & 9Value.
            [Task] Create 30 questions (10 per 3T) in JSON format.
            [Format] Return ONLY a JSON list: [{{"cat": "Transform", "q": "질문", "i": "의도"}}, ...]
            """
            with st.spinner("이력서를 스캔하여 질문을 구성 중입니다..."):
                raw_res = call_gemini_vision(prompt, resume_file)
                try:
                    cleaned_res = raw_res.replace("```json", "").replace("```", "").strip()
                    st.session_state.ai_questions = json.loads(cleaned_res)
                except:
                    st.error("JSON 파싱 오류가 발생했습니다. 다시 시도해주세요.")

    # [2] 질문 리스트 & 노트 (2단 구성)
    col_q, col_n = st.columns([1.2, 1])

    with col_q:
        st.subheader("🤖 제안 질문 리스트")
        if not st.session_state.ai_questions:
            st.write("이력서를 업로드하고 버튼을 누르면 질문이 생성됩니다.")
        else:
            for i, q in enumerate(st.session_state.ai_questions):
                cols = st.columns([0.15, 0.85])
                # 체크박스 상태 관리
                is_selected = cols[0].checkbox("선택", key=f"chk_{i}")
                
                # 체크박스 선택 시 세션 세트에 추가/삭제
                if is_selected:
                    st.session_state.selected_qs_set.add(q['q'])
                else:
                    st.session_state.selected_qs_set.discard(q['q'])
                
                with cols[1].expander(f"Q{i+1}. {q['q'][:45]}..."):
                    st.write(f"**질문:** {q['q']}")
                    st.caption(f"🎯 의도: {q['i']}")

    with col_n:
        # [핵심 업데이트] 면접관 노트 접기/펴기 기능 (기본: 펼침)
        with st.expander("📝 면접관 노트 (클릭하여 접기/펴기)", expanded=True):
            st.caption("질문 리스트에서 체크한 문항이 자동으로 추가됩니다.")
            
            # 선택된 질문들을 텍스트화
            auto_added_text = ""
            if st.session_state.selected_qs_set:
                for sq in st.session_state.selected_qs_set:
                    auto_added_text += f"❓ {sq}\n└ 💡 메모: \n\n"
            
            # 메모장 영역
            final_memo = st.text_area("인터뷰 기록창", 
                                      value=auto_added_text if not st.session_state.memo_content else st.session_state.memo_content + auto_added_text,
                                      height=500,
                                      placeholder="직접 입력하거나 왼쪽에서 질문을 선택하세요.")
            
            st.session_state.memo_content = final_memo # 내용 유지용
            
            st.download_button(
                "💾 인터뷰 결과 저장 (.txt)", 
                final_memo, 
                f"Interview_Note_{datetime.datetime.now().strftime('%m%d_%H%M')}.txt",
                type="primary", 
                use_container_width=True
            )
