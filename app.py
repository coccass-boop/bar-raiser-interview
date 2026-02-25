# --- 2. 구글 시트 연동 (면접관 인증용) ---
SHEET_ID = "1c1lZRL0oOC95-YTrqMDpUaCGfbUk368yfYI-XlcJxYo"
AUTH_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=%EB%A9%B4%EC%A0%91%EA%B4%80%20%EC%BD%94%EB%93%9C"

def load_auth_data():
    try:
        fresh_url = f"{AUTH_URL}&_={int(time.time())}"
        df = pd.read_csv(fresh_url, dtype=str)
        
        df = df.fillna("")
        
        # [핵심 복구] 숫자 형식으로 바꿨을 때 몰래 붙는 쉼표(,)와 소수점(.00)을 무자비하게 날려버립니다!
        codes = df['면접관 코드(그룹입사일)'].str.replace(',', '', regex=False).str.replace(r'\.0*$', '', regex=True).str.strip()
        names = df['면접관 성명'].str.strip()
        
        valid_dict = {}
        for c, n in zip(codes, names):
            if c:  
                valid_dict[c] = n
                
        return valid_dict
    except Exception as e:
        if "HTTP Error 401" in str(e):
            st.error("🚨 구글 시트 접근 권한이 없습니다. 시트의 공유 설정을 '링크가 있는 모든 사용자 (뷰어)'로 변경해주세요.")
        else:
            st.error(f"시트 데이터를 불러오는 데 실패했습니다: {e}")
        return {}
