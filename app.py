import streamlit as st
import requests
import json
import base64
import datetime
from bs4 import BeautifulSoup

# --- 1. 페이지 설정 및 디자인 CSS ---
st.set_page_config(page_title="Bar Raiser Copilot", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    /* 카테고리 헤더 폰트 강화 */
    .cat-header {
        font-size: 20px !important;
        font-weight: 700 !important;
        margin-bottom: 5px;
    }
    /* 버튼 중앙 정렬 보정 */
    .stButton button {
        margin-top: 5px !important;
        padding: 2px 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API 키 설정 ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키를 설정해주세요.")
    st.stop()

# --- 3. 데이터 초기화 ---
if "ai_questions" not in st.session_state:
    st.session_state.ai_questions = {"Transform": [], "Tomorrow": [], "Together": []}
if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = []

LEVEL_GUIDELINES = {
    "IC-L3": "[기본기 실무자] 가이드 하 업무 수행.",
    "IC-L4": "[자기완결 실무자] 목표 내 업무 독립적 계획/실행.",
    "IC-L5": "[핵심 전문가] 최적 대안 제시 및 전파.",
    "IC-L6": "[선도적 전문가] 파트 리드, 성과 선순환 구조 구축.",
    "IC-L7": "[전사 혁신 주도] 업계 표준 정의 최고 수준 전문성.",
    "M-L5": "[유닛 리더] 과제 운영 및 프로젝트 성공 리딩.",
    "M-L6": "[시니어 리더] 유닛 성과 및 육성 관리.",
    "M-L7": "[디렉터] 전략 방향 및 조직 시너시 총괄."
}

# --- 4. 함수 정의 ---
def fetch_jd(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
    except: return None

def generate_questions_by_category(category, level, resume_file, jd_text):
    prompt = f"""
    [Role] Bar Raiser Interviewer. Framework: Trinity Values.
    [Target] {level}. [Category] {category}.
    [JD] {jd_text[:3000]}
    [Task] Create 10 unique questions in Korean for '{category}'. 
    [Format] JSON ONLY: [{{"q": "질문", "i": "의도"}}, ...]
    """
    try:
        pdf_base64 = base64.b64encode(resume_file.getvalue()).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"
        data = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "application/pdf", "data": pdf_base64}}]}]}
        res = requests.post(url, json=data, timeout=60)
        cleaned = res.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except: return []

# --- 5. 사이드바 (설정 유지) ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    selected_level = st.selectbox("레벨 선택", list(LEVEL_GUIDELINES.keys()))
    st.info(f"💡 {LEVEL_GUIDELINES[selected_level]}")
    
    st.subheader("2. JD (채용공고)")
    tab1, tab2 = st.tabs(["🔗 URL", "📝 텍스트"])
    with tab1:
        url_input = st.text_input("URL 입력")
        jd_from_url = fetch_jd(url_input) if url_input else ""
    with tab2:
        jd_from_text = st.text_area("내용 붙여넣기", height=150)
    jd_final_content = jd_from_text if jd_from_text else jd_from_url

    resume_file = st.file_uploader("이력서 PDF", type="pdf")
    st.divider()
    if st.button("전체 질문 생성 시작 🚀", type="primary", use_container_width=True):
        if resume_file and jd_final_content:
            with st.spinner("분석 중..."):
                for cat in ["Transform", "Tomorrow", "Together"]:
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final_content)
        else: st.error("입력 정보를 확인해주세요.")

# --- 6. 메인 화면 ---
st.title("✈️ Bar Raiser Copilot")

# [복구] Trinity Values 이미지형 카드 디자인 + 접기 기능
with st.expander("💎 Trinity Values (클릭하여 기준 확인)", expanded=False):
    st.markdown("<h3 style='text-align: center;'>Trinity Values</h3>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("#### **We TRANSFORM through :**")
            st.caption("💡 Customer-First Innovation")
            st.caption("📈 Enduring Value Creation")
            st.caption("🎯 Excellence in Execution")
    with c2:
        with st.container(border=True):
            st.markdown("#### **We shape TOMORROW by :**")
            st.caption("🌱 Active Learning")
            st.caption("🚀 Forward Thinking")
            st.caption("⚡ Speed with Impact")
    with c3:
        with st.container(border=True):
            st.markdown("#### **We succeed TOGETHER through :**")
            st.caption("🤝 Power of Three")
            st.caption("💗 Trust & Growth")
            st.caption("🌐 Global Perspective")

st.divider()

col_q, col_n = st.columns([1.1, 1])

# [왼쪽] 질문 리스트 (항목별 접기 + 새로고침)
with col_q:
    st.markdown('<p class="cat-header">🤖 제안 질문 리스트</p>', unsafe_allow_html=True)
    
    for cat in ["Transform", "Tomorrow", "Together"]:
        # [복구] 카테고리별 접기 버튼(Expander)
        with st.expander(f"📌 {cat} 리스트", expanded=True):
            # 새로고침 버튼 (우측 상단 작게 배치)
            c_head, c_ref = st.columns([0.88, 0.12])
            if c_ref.button("🔄", key=f"ref_{cat}", help=f"{cat} 새로고침"):
                if resume_file and jd_final_content:
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_final_content)
                    st.rerun()
            
            if not st.session_state.ai_questions[cat]:
                st.write("질문이 없습니다.")
            
            for i, q in enumerate(st.session_state.ai_questions[cat]):
                # [수정] +버튼 중앙 정렬 및 크기 최적화
                qc, ac = st.columns([0.9, 0.1])
                qc.write(f"**Q. {q['q']}**")
                if ac.button("➕", key=f"add_{cat}_{i}"):
                    if q['q'] not in [sq['q'] for sq in st.session_state.selected_questions]:
                        st.session_state.selected_questions.append({"q": q['q'], "cat": cat, "memo": ""})
                st.caption(f"🎯 의도: {q['i']}")
                st.divider()

# [오른쪽] 면접관 실시간 노트
with col_n:
    st.markdown('<p class="cat-header">📝 면접관 실시간 노트</p>', unsafe_allow_html=True)
    with st.expander("기록창 열기/닫기", expanded=True):
        if st.button("➕ 개별 질문 추가", use_container_width=True):
            st.session_state.selected_questions.append({"q": "", "cat": "Custom", "memo": ""})
        
        st.divider()
        for idx, item in enumerate(st.session_state.selected_questions):
            tag_col, del_col = st.columns([0.93, 0.07])
            tag_col.markdown(f"<span style='font-size:0.8rem; color:gray;'>Q{idx+1}</span> <span style='background-color:#f0f2f6; padding:2px 6px; border-radius:4px; font-size:0.7rem; font-weight:bold;'>{item.get('cat','Custom')}</span>", unsafe_allow_html=True)
            if del_col.button("✕", key=f"del_{idx}"):
                st.session_state.selected_questions.pop(idx)
                st.rerun()
            
            st.session_state.selected_questions[idx]['q'] = st.text_area(f"q_{idx}", value=item['q'], placeholder="질문을 직접 입력하세요.", label_visibility="collapsed", height=70, key=f"area_q_{idx}")
            st.session_state.selected_questions[idx]['memo'] = st.text_area(f"m_{idx}", value=item.get('memo',''), placeholder="답변 메모...", label_visibility="collapsed", height=100, key=f"area_m_{idx}")
            st.markdown("<div style='margin-bottom:20px; border-bottom:1px solid #eee;'></div>", unsafe_allow_html=True)

        if st.session_state.selected_questions:
            out_data = f"Target: {selected_level}\n"
            for s in st.session_state.selected_questions:
                out_data += f"\n[{s.get('cat','Custom')}] Q: {s['q']}\nA: {s.get('memo','')}\n"
            st.download_button("💾 결과 저장 (.txt)", out_data, f"Interview_Note.txt", type="primary", use_container_width=True)
