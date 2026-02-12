import streamlit as st
import requests
import json
import base64
from bs4 import BeautifulSoup
import datetime
import pandas as pd

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="Bar Raiser Copilot", page_icon="✈️", layout="wide")

# --- 2. API 키 가져오기 ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키가 설정되지 않았습니다.")
    st.stop()

# [공식 정의 데이터 - 생략 없이 그대로 유지]
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
    "IC-L3": "[기본기를 확립하는 실무자] 명확한 지시와 가이드 하에 업무 수행, 직무 기초 지식과 기술 학습.",
    "IC-L4": "[자기완결성을 갖춘 독립적 실무자] 실무 지식/경험으로 일상 문제를 해결. 목표 내 업무를 독립적으로 계획/실행.",
    "IC-L5": "[성장을 지원하는 핵심 직무 전문가] 직무 분야의 깊이 있는 전문성. 데이터 및 경험 기반의 최적 대안 제시.",
    "IC-L6": "[조직 변화를 이끄는 선도적 전문가] 특정 전문 영역이나 파트를 리드. 자율성과 책임감으로 전략 실행 주도.",
    "IC-L7": "[전사 혁신을 주도하는 최고 권위자] 가장 복잡하고 전례 없는 문제를 해결. 업계 표준을 정의하는 최고 수준의 전문성.",
    "M-L5": "[단일 기능의 유닛 성장을 이끄는 리더] 소속 유닛의 과제 운영 및 프로젝트/제품의 성공을 만들어 냄.",
    "M-L6": "[독립적인 유닛 성장을 이끄는 리더] 유닛의 성과와 동시에 유닛원들의 육성을 성공적으로 만듦.",
    "M-L7": "[회사의 핵심 조직 성장을 이끄는 리더] 직무/분야의 리더로서 유닛간의 시너지를 만듦."
}

# --- 3. 함수 정의 ---
def call_gemini_vision(prompt, pdf_file):
    try:
        pdf_bytes = pdf_file.getvalue()
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # [해결의 열쇠] 모델 이름을 'gemini-flash-latest'로 고정합니다. 
        # 이 별칭은 v1beta API에서 가장 범용적으로 작동하는 이름입니다.
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
        
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=60)
        
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"⚠️ 분석 실패 (코드 {response.status_code}): {response.text}"
            
    except Exception as e:
        return f"⚠️ 시스템 오류: {str(e)}"

def fetch_jd(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
        return None
    except: return None

# --- 4. UI 구성 ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    selected_level = st.selectbox("레벨 선택", list(LEVEL_GUIDELINES.keys()))
    st.info(f"💡 **Role Persona:**\n{LEVEL_GUIDELINES[selected_level]}")
    
    track_info = "Manager Track" if "M-" in selected_level else "IC Track"
    
    tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
    jd_content = ""
    with tab1:
        url = st.text_input("URL 입력")
        if url and fetch_jd(url): jd_content = fetch_jd(url)
    with tab2:
        paste = st.text_area("내용 붙여넣기", height=100)
        if paste: jd_content = paste

    resume_file = st.file_uploader("이력서 PDF", type="pdf")
    btn = st.button("질문 리스트 생성 🚀", type="primary", use_container_width=True)

    with st.expander("ℹ️ System Version 3.6 (Alias Fix)"):
        admin_pw = st.text_input("Access Key", type="password")
        mode = "Admin" if admin_pw == "admin1234" else "User"

# 메인 화면 UI (나머지 로직은 이전과 동일)
if mode == "Admin":
    st.title("📊 Insight Dashboard")
    st.metric("시스템 상태", "Active", "Flash-Latest")
else:
    st.title("✈️ Bar Raiser Copilot")
    st.divider()

    col_l, col_r = st.columns([1.2, 1])
    if "ai_result" not in st.session_state: st.session_state.ai_result = ""

    if btn:
        if not resume_file or not jd_content:
            st.toast("필요 정보를 입력해주세요!")
        else:
            prompt = f"""
            [Role] Bar Raiser Interviewer.
            [Target] {selected_level} ({track_info}) - {LEVEL_GUIDELINES[selected_level]}
            [Values] {VALUE_SYSTEM}
            [Task] Create 30 questions (10 per 3T category) in Korean.
            [Format] Question followed by '> 💡 [Specific Value] Assessment Point'.
            """
            with st.spinner("분석 중..."):
                st.session_state.ai_result = call_gemini_vision(prompt, resume_file)

    if st.session_state.ai_result:
        with col_l:
            st.subheader(f"🤖 AI 제안 질문 ({selected_level})")
            if "⚠️" in st.session_state.ai_result: st.error(st.session_state.ai_result)
            else: st.markdown(st.session_state.ai_result)
        with col_r:
            st.subheader("📝 면접관 노트")
            interview_notes = st.text_area("인터뷰 시트", height=500)
            st.download_button("💾 노트 다운로드", interview_notes, f"Interview_{selected_level}.txt")
