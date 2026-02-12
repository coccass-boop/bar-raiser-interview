import streamlit as st
import requests
import json
import base64
import datetime

# --- 1. 페이지 설정 및 스타일 ---
st.set_page_config(page_title="Bar Raiser Copilot", page_icon="✈️", layout="wide")

# --- 2. API 키 설정 ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키를 설정해주세요.")
    st.stop()

# --- 3. 세션 상태 초기화 (데이터 보존의 핵심) ---
if "ai_questions" not in st.session_state:
    st.session_state.ai_questions = {"Transform": [], "Tomorrow": [], "Together": []}
if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = []  # [{"q": "질문", "memo": ""}, ...]
if "jd_cache" not in st.session_state: st.session_state.jd_cache = ""

# --- 4. 질문 생성 함수 (항목별 타겟팅) ---
def generate_questions_by_category(category, level, resume_file, jd_text):
    prompt = f"""
    [Role] Bar Raiser Interviewer.
    [Target Level] {level}
    [Target Category] {category} (from 3T Framework)
    [Candidate Resume] (PDF attached)
    [Job Description] {jd_text}
    [Task] Create 10 unique interview questions for the '{category}' category.
    [Format] Return ONLY a JSON list: [{{"q": "질문", "i": "의도"}}, ...]
    """
    try:
        pdf_base64 = base64.b64encode(resume_file.getvalue()).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"
        data = {
            "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "application/pdf", "data": pdf_base64}}]}]
        }
        res = requests.post(url, json=data, timeout=60)
        if res.status_code == 200:
            cleaned = res.json()['candidates'][0]['content']['parts'][0]['text'].replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
    except:
        st.error(f"{category} 질문 생성 실패")
        return []

# --- 5. 사이드바 구성 ---
with st.sidebar:
    st.title("✈️ Copilot Menu")
    selected_level = st.selectbox("레벨 선택", ["IC-L3", "IC-L4", "IC-L5", "IC-L6", "IC-L7", "M-L5", "M-L6", "M-L7"])
    resume_file = st.file_uploader("이력서 PDF", type="pdf")
    jd_input = st.text_area("JD 내용", value=st.session_state.jd_cache)
    st.session_state.jd_cache = jd_input

    if st.button("전체 질문 생성 시작 🚀", type="primary", use_container_width=True):
        if resume_file and jd_input:
            for cat in ["Transform", "Tomorrow", "Together"]:
                st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_input)
        else:
            st.warning("이력서와 JD를 확인해주세요.")

# --- 6. 메인 UI ---
st.title("✈️ Bar Raiser Copilot")

col_q, col_n = st.columns([1.2, 1])

# --- 왼쪽: 질문 리스트 (카테고리별 새로고침) ---
with col_q:
    st.subheader("🤖 카테고리별 제안 질문")
    
    for cat in ["Transform", "Tomorrow", "Together"]:
        with st.expander(f"📌 {cat} 항목 질문 리스트", expanded=True):
            # 새로고침 버튼
            if st.button(f"🔄 {cat} 질문 새로고침", key=f"ref_{cat}"):
                if resume_file:
                    st.session_state.ai_questions[cat] = generate_questions_by_category(cat, selected_level, resume_file, jd_input)
                else: st.error("이력서가 필요합니다.")
            
            # 질문 나열
            for i, q in enumerate(st.session_state.ai_questions[cat]):
                c1, c2 = st.columns([0.85, 0.15])
                c1.write(f"**Q. {q['q']}**")
                if c2.button("추가", key=f"add_{cat}_{i}"):
                    # 노트에 중복 방지하며 추가
                    if q['q'] not in [sq['q'] for sq in st.session_state.selected_questions]:
                        st.session_state.selected_questions.append({"q": q['q'], "memo": ""})
                st.caption(f"🎯 의도: {q['i']}")
                st.divider()

# --- 오른쪽: 면접관 노트 (개별 삭제 및 커스텀 추가) ---
with col_n:
    with st.expander("📝 면접관 실시간 노트", expanded=True):
        st.subheader("인터뷰 기록")
        
        # [기능 1] 커스텀 질문 수동 추가
        if st.button("➕ 개별 질문(직접 준비) 추가"):
            st.session_state.selected_questions.append({"q": "직접 입력한 질문입니다.", "memo": ""})

        # [기능 2] 추가된 질문들 표시 (삭제 기능 포함)
        for idx, item in enumerate(st.session_state.selected_questions):
            st.markdown(f"**질문 {idx+1}**")
            
            # 질문 내용 편집 가능 (커스텀 질문일 경우 대비)
            new_q = st.text_input("질문 내용", value=item['q'], key=f"edit_q_{idx}")
            st.session_state.selected_questions[idx]['q'] = new_q
            
            # 답변 메모칸
            new_memo = st.text_area("답변 메모 및 평가", value=item['memo'], key=f"memo_{idx}", height=100)
            st.session_state.selected_questions[idx]['memo'] = new_memo
            
            # 삭제 버튼
            if st.button(f"❌ 질문 {idx+1} 삭제", key=f"del_q_{idx}"):
                st.session_state.selected_questions.pop(idx)
                st.rerun()
            
            st.divider()

        # [기능 3] 결과 저장
        if st.session_state.selected_questions:
            final_output = f"인터뷰 대상: {selected_level}\n날짜: {datetime.datetime.now()}\n\n"
            for sq in st.session_state.selected_questions:
                final_output += f"질문: {sq['q']}\n답변: {sq['memo']}\n\n"
            
            st.download_button("💾 인터뷰 결과 (.txt) 다운로드", final_output, f"Result_{datetime.datetime.now().strftime('%m%d_%H%M')}.txt", type="primary", use_container_width=True)
        else:
            st.write("왼쪽에서 질문을 '추가'하거나 직접 질문을 생성해 보세요.")
