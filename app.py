import streamlit as st
import google.generativeai as genai
import json
import time

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Sử K59 - Dual Theme",
    page_icon="🌗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. QUẢN LÝ THEME (STATE) ---
if "theme" not in st.session_state:
    st.session_state.theme = "light"

# Hàm đổi theme
def toggle_theme():
    if st.session_state.theme == "light":
        st.session_state.theme = "dark"
    else:
        st.session_state.theme = "light"

# --- 3. ĐỊNH NGHĨA MÀU SẮC (PALETTE) ---
themes = {
    "light": {
        "bg_color": "#f3f4f6",           # Xám rất nhạt
        "card_bg": "#ffffff",            # Trắng tinh
        "text_main": "#111827",          # Đen than (không đen tuyền)
        "text_sub": "#4b5563",           # Xám trung tính
        "accent": "#2563eb",             # Xanh dương đậm
        "border": "#e5e7eb",             # Viền nhạt
        "shadow": "0 10px 15px -3px rgba(0, 0, 0, 0.1)", # Bóng mềm
        "input_bg": "#ffffff",
        "badge_bg": "#dbeafe",
        "badge_text": "#1e40af"
    },
    "dark": {
        "bg_color": "#0f1117",           # Đen sâu (Streamlit dark)
        "card_bg": "#1e293b",            # Xanh đen (Slate 800)
        "text_main": "#f9fafb",          # Trắng đục
        "text_sub": "#9ca3af",           # Xám sáng
        "accent": "#60a5fa",             # Xanh dương sáng (dễ đọc trên nền đen)
        "border": "#374151",             # Viền tối
        "shadow": "none",                # Dark mode ít dùng bóng, dùng màu nền để tách lớp
        "input_bg": "#334155",
        "badge_bg": "#1e3a8a",
        "badge_text": "#bfdbfe"
    }
}

current_theme = themes[st.session_state.theme]

# --- 4. CSS ĐỘNG (DYNAMIC CSS INJECTION) ---
st.markdown(f"""
<style>
    /* Global Transition */
    * {{
        transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
    }}

    /* App Background */
    .stApp {{
        background-color: {current_theme['bg_color']};
    }}
    
    /* Ẩn Header Streamlit */
    header[data-testid="stHeader"] {{
        background-color: transparent;
    }}

    /* Login Container & Exam Header & Question Box */
    .theme-card {{
        background-color: {current_theme['card_bg']};
        border-radius: 16px;
        padding: 40px;
        box-shadow: {current_theme['shadow']};
        border: 1px solid {current_theme['border']};
        color: {current_theme['text_main']};
    }}
    
    /* Typography */
    h1, h2, h3, .login-title {{
        color: {current_theme['text_main']} !important;
        font-family: 'Segoe UI', sans-serif;
    }}
    p, .login-subtitle, .question-content {{
        color: {current_theme['text_main']} !important;
        font-size: 16px;
        line-height: 1.6;
    }}
    
    /* Input Fields Fix */
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {{
        background-color: {current_theme['input_bg']} !important;
        color: {current_theme['text_main']} !important;
        border-color: {current_theme['border']} !important;
    }}
    label, .stMarkdown p {{
        color: {current_theme['text_main']} !important;
    }}
    
    /* Button Custom */
    div.stButton > button {{
        background-color: {current_theme['accent']};
        color: white !important;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
    }}
    div.stButton > button:hover {{
        filter: brightness(110%);
        box-shadow: 0 4px 12px {current_theme['accent']}40; /* 40 là độ trong suốt */
    }}

    /* Badge Style */
    .badge {{
        background-color: {current_theme['badge_bg']};
        color: {current_theme['badge_text']};
        padding: 4px 12px;
        border-radius: 99px;
        font-size: 12px;
        font-weight: bold;
        text-transform: uppercase;
    }}

    /* Custom Border Left for Question */
    .question-highlight {{
        border-left: 4px solid {current_theme['accent']};
    }}

</style>
""", unsafe_allow_html=True)

# --- 5. LOGIC DỮ LIỆU (KHÔNG ĐỔI) ---
KNOWLEDGE_BASE = """
Tài liệu: Chuyên đề học tập Lịch sử 10 - Cánh Diều.
1. SỬ HỌC: Thông sử (toàn diện), Lịch sử chuyên ngành (văn hóa, kinh tế...).
2. DI SẢN: Vật thể (Huế, Hội An...), Phi vật thể (Nhã nhạc, Quan họ...), Thiên nhiên (Hạ Long), Hỗn hợp (Tràng An).
3. NHÀ NƯỚC: Lý-Trần (Thân dân), Lê Sơ (Quan liêu chuyên chế), Nguyễn (Chuyên chế cao độ).
4. LUẬT: Hồng Đức (nhân văn), Gia Long (nghiêm khắc).
5. HIỆN ĐẠI: VNDCCH (1945), CHXHCNVN (1976). Hiến pháp: 1946, 1959, 1980, 1992, 2013.
"""

def get_question(api_key, topic):
    if not api_key: return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        prompt = f"""
        Tạo 1 câu hỏi trắc nghiệm Lịch sử 10 về: "{topic}".
        JSON format:
        {{
            "question": "Câu hỏi?",
            "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
            "correct_answer": "Đáp án đúng (text)",
            "explanation": "Giải thích."
        }}
        """
        response = model.generate_content(prompt)
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except Exception: return None

# --- 6. GIAO DIỆN LOGIN ---
def render_login():
    # Nút đổi theme nằm góc trên phải
    col_t1, col_t2 = st.columns([9, 1])
    with col_t2:
        # Icon thay đổi theo theme
        theme_icon = "🌞" if st.session_state.theme == "light" else "🌙"
        if st.button(theme_icon, key="theme_toggle_login", help="Đổi chế độ Sáng/Tối"):
            toggle_theme()
            st.rerun()

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(f"""
            <div class="theme-card" style="text-align: center; margin-top: 20px;">
                <div style="font-size: 60px; margin-bottom: 10px;">🏛️</div>
                <h2 class="login-title" style="margin: 0;">SỬ K59</h2>
                <p class="login-subtitle">Đấu trường tri thức nè</p>
                <hr style="border-color: {current_theme['border']}; margin: 20px 0;">
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Form nhập liệu
        name = st.text_input("Họ tên thí sinh", placeholder="Nhập tên của bạn...")
        api = st.text_input("Mã API Key", type="password")
        topic = st.selectbox("Chủ đề thi", ["Tổng hợp kiến thức", "Di sản văn hóa", "Nhà nước & Pháp luật"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚀 VÀO THI NGAY", use_container_width=True):
            if name and api:
                st.session_state.user_name = name
                st.session_state.api_key = api
                st.session_state.topic = topic
                st.session_state.page = "exam"
                st.rerun()
            else:
                st.error("Vui lòng nhập đủ thông tin!")

# --- 7. GIAO DIỆN THI (EXAM) ---
def render_exam():
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.caption(f"Chủ đề: {st.session_state.topic}")
        st.markdown("---")
        st.metric("Điểm số", f"{st.session_state.score}")
        
        st.markdown("<br>" * 5, unsafe_allow_html=True)
        # Nút đổi theme trong sidebar
        theme_label = "Chế độ Tối" if st.session_state.theme == "light" else "Chế độ Sáng"
        if st.button(f"🌗 {theme_label}", use_container_width=True):
            toggle_theme()
            st.rerun()
            
        if st.button("🚪 Thoát", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()

    # Header bài thi
    st.markdown(f"""
        <div class="theme-card" style="padding: 20px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div>
                <span class="badge">Đang diễn ra</span>
                <strong style="margin-left: 10px; font-size: 18px;">Phòng thi Sử K59</strong>
            </div>
            <div>Câu số: <strong>{st.session_state.count + 1}</strong></div>
        </div>
    """, unsafe_allow_html=True)

    # Lấy câu hỏi
    if st.session_state.current_q is None:
        with st.spinner("⏳ AI đang soạn đề..."):
            st.session_state.current_q = get_question(st.session_state.api_key, st.session_state.topic)
            st.rerun()

    q = st.session_state.current_q
    if q:
        # Hộp câu hỏi
        st.markdown(f"""
            <div class="theme-card question-highlight">
                <div class="question-content" style="font-size: 20px; font-weight: 600;">{q['question']}</div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Radio button
        answer = st.radio("Chọn đáp án:", q['options'], index=None)

        st.markdown("<br>", unsafe_allow_html=True)

        c1, c2 = st.columns([1, 4])
        if not st.session_state.ans_submitted:
            if c1.button("🔒 Chốt đáp án"):
                if answer:
                    st.session_state.ans_submitted = True
                    if answer == q['correct_answer']:
                        st.session_state.score += 10
                        st.success("Chính xác! +10 điểm")
                    else:
                        st.error(f"Sai rồi! Đáp án: {q['correct_answer']}")
                    st.rerun()
                else:
                    st.warning("Chưa chọn đáp án!")
        else:
            st.info(f"💡 Giải thích: {q['explanation']}")
            if c1.button("➡️ Câu tiếp theo"):
                st.session_state.current_q = None
                st.session_state.ans_submitted = False
                st.session_state.count += 1
                st.rerun()

# --- 8. MAIN ---
def main():
    if "page" not in st.session_state: st.session_state.page = "login"
    if "score" not in st.session_state: st.session_state.score = 0
    if "count" not in st.session_state: st.session_state.count = 0
    if "current_q" not in st.session_state: st.session_state.current_q = None
    if "ans_submitted" not in st.session_state: st.session_state.ans_submitted = False
    
    # State cho tên người dùng
    if "user_name" not in st.session_state: st.session_state.user_name = ""

    if st.session_state.page == "login":
        render_login()
    else:
        render_exam()

if __name__ == "__main__":
    main()
