import streamlit as st
import google.generativeai as genai
import json
import time
import math

# --- 1. CẤU HÌNH TRANG & TRẠNG THÁI ---
st.set_page_config(page_title="Thi Trực Tuyến", page_icon="📝", layout="wide", initial_sidebar_state="collapsed")

if "exam_data" not in st.session_state: st.session_state.exam_data = []
if "user_answers" not in st.session_state: st.session_state.user_answers = {} # Lưu index: đáp án
if "current_index" not in st.session_state: st.session_state.current_index = 0
if "exam_status" not in st.session_state: st.session_state.exam_status = "setup" # setup, ready, running, paused, review
if "start_time" not in st.session_state: st.session_state.start_time = 0
if "duration" not in st.session_state: st.session_state.duration = 0
if "theme" not in st.session_state: st.session_state.theme = "light"

# --- 2. HỆ THỐNG THEME TƯƠNG PHẢN CAO (HIGH CONTRAST) ---
themes = {
    "light": {
        "bg": "#FFFFFF", "text": "#000000", "card": "#F8F9FA",
        "border": "#DEE2E6", "primary": "#007AFF", "grid_item": "#FFFFFF",
        "grid_active": "#007AFF", "grid_text": "#000000"
    },
    "dark": {
        "bg": "#121212", "text": "#FFFFFF", "card": "#1E1E1E",
        "border": "#333333", "primary": "#0A84FF", "grid_item": "#2C2C2C",
        "grid_active": "#0A84FF", "grid_text": "#FFFFFF"
    }
}
T = themes[st.session_state.theme]

st.markdown(f"""
<style>
    /* Reset CSS */
    .stApp {{ background-color: {T['bg']}; color: {T['text']}; }}
    
    /* Typography */
    h1, h2, h3, p, span, div, label {{ color: {T['text']} !important; font-family: 'Segoe UI', sans-serif; }}
    
    /* Header Azota Style */
    .header-bar {{
        display: flex; justify-content: space-between; align-items: center;
        padding: 15px 30px; border-bottom: 1px solid {T['border']};
        background-color: {T['card']}; position: sticky; top: 0; z-index: 999;
    }}
    
    /* Question Card */
    .q-card {{
        background-color: {T['card']}; padding: 30px; border-radius: 8px;
        border: 1px solid {T['border']}; margin-bottom: 20px;
    }}
    .q-title {{ font-size: 18px; font-weight: 600; margin-bottom: 15px; }}
    
    /* Sidebar Grid (Question Palette) */
    .grid-container {{
        display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;
        padding: 15px; border: 1px solid {T['border']}; border-radius: 8px;
        background-color: {T['card']};
    }}
    .grid-btn {{
        text-align: center; padding: 8px 0; border-radius: 4px;
        border: 1px solid {T['border']}; cursor: pointer; font-weight: bold;
        background-color: {T['grid_item']}; color: {T['grid_text']}; transition: 0.2s;
    }}
    .grid-btn.done {{ background-color: #E8F5E9; border-color: #4CAF50; color: #2E7D32; }} /* Đã làm (Light) */
    .grid-btn.active {{ background-color: {T['primary']}; color: white !important; border-color: {T['primary']}; }}
    
    /* Radio Button Styling */
    div[role="radiogroup"] > label {{
        background-color: {T['bg']} !important; border: 1px solid {T['border']};
        padding: 15px; border-radius: 8px; margin-bottom: 10px; transition: 0.2s;
    }}
    div[role="radiogroup"] > label:hover {{ border-color: {T['primary']}; }}
    
    /* Input Fields */
    input, select {{ background-color: {T['card']} !important; color: {T['text']} !important; border: 1px solid {T['border']} !important; }}
    
    /* Buttons */
    button[kind="primary"] {{ background-color: {T['primary']} !important; color: white !important; border: none; }}
    button[kind="secondary"] {{ background-color: transparent; border: 1px solid {T['border']}; color: {T['text']}; }}
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIC XỬ LÝ ---

KNOWLEDGE_BASE = """
Tài liệu: Chuyên đề học tập Lịch sử 10 - Cánh Diều.
Chủ đề: Lịch sử Sử học, Di sản văn hóa, Nhà nước & Pháp luật Việt Nam.
"""

def generate_exam_data(api_key, topic, num_questions=10):
    """Sinh 1 lần 10-20 câu hỏi để tránh lag"""
    if not api_key: return None
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Tạo một bộ đề thi trắc nghiệm gồm {num_questions} câu hỏi về chủ đề: "{topic}".
    Dựa trên kiến thức: {KNOWLEDGE_BASE}.
    Trả về định dạng JSON List chuẩn (Array of Objects). KHÔNG dùng markdown code block.
    Cấu trúc:
    [
        {{
            "id": 1,
            "question": "Nội dung câu hỏi?",
            "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
            "correct_answer": "Đáp án đúng (text)",
            "explanation": "Giải thích ngắn."
        }},
        ...
    ]
    """
    try:
        response = model.generate_content(prompt)
        clean_json = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_json)
    except: return None

def format_time(seconds):
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{int(s):02d}"

# --- 4. UI: MÀN HÌNH SETUP ---
def render_setup():
    st.markdown(f"<h1 style='text-align: center; color: {T['primary']}'>🏛️ HỆ THỐNG THI SỬ K59</h1>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.container(border=True):
            st.markdown("### ⚙️ Cấu hình phòng thi")
            api = st.text_input("Nhập Gemini API Key", type="password")
            name = st.text_input("Họ tên thí sinh", "Liễu Lương")
            topic = st.selectbox("Chủ đề", ["Tổng hợp kiến thức", "Di sản văn hóa", "Nhà nước & Pháp luật"])
            q_num = st.slider("Số lượng câu hỏi", 5, 20, 10)
            minutes = st.number_input("Thời gian làm bài (phút)", 5, 120, 15)
            
            if st.button("SOẠN ĐỀ THI 🚀", use_container_width=True, type="primary"):
                if not api:
                    st.error("Thiếu API Key kìa!")
                else:
                    with st.spinner("⏳ Đang in đề... Vui lòng đợi trong giây lát!"):
                        data = generate_exam_data(api, topic, q_num)
                        if data:
                            st.session_state.exam_data = data
                            st.session_state.user_name = name
                            st.session_state.duration = minutes * 60
                            st.session_state.start_time = time.time()
                            st.session_state.exam_status = "running"
                            st.rerun()
                        else:
                            st.error("AI bị lỗi, thử lại nhé!")

# --- 5. UI: MÀN HÌNH THI (MAIN EXAM) ---
def render_exam():
    # Header Bar (Sticky)
    elapsed = time.time() - st.session_state.start_time
    remaining = max(0, st.session_state.duration - elapsed)
    
    # Nút đổi theme & Pause trên header
    col_h1, col_h2, col_h3, col_h4 = st.columns([2, 4, 2, 2])
    with col_h1:
        if st.button("🌗 Đổi nền"):
            st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
            st.rerun()
    with col_h2:
        st.markdown(f"<div style='font-size: 20px; font-weight: bold; text-align: center;'>⏱️ {format_time(remaining)}</div>", unsafe_allow_html=True)
    with col_h3:
        st.markdown(f"<b>👤 {st.session_state.user_name}</b>", unsafe_allow_html=True)
    with col_h4:
        if st.button("Nộp bài", type="primary", use_container_width=True):
            st.session_state.exam_status = "review"
            st.rerun()

    st.markdown("---")

    # Layout: Left (Question) - Right (Grid)
    col_main, col_nav = st.columns([3, 1])

    # --- RIGHT: NAVIGATION GRID ---
    with col_nav:
        st.markdown("### 🔢 Danh sách câu hỏi")
        
        # Nút Pause/Resume
        if st.button("⏸️ Tạm dừng làm bài", use_container_width=True):
            st.session_state.exam_status = "paused"
            st.session_state.pause_time = time.time() # Lưu thời điểm pause
            st.rerun()

        # Grid câu hỏi
        total_q = len(st.session_state.exam_data)
        cols = st.columns(5) # 5 cột trong grid
        for i in range(total_q):
            is_active = (i == st.session_state.current_index)
            is_done = (i in st.session_state.user_answers)
            
            # CSS class giả lập
            btn_color = T['primary'] if is_active else ("#4CAF50" if is_done else T['card'])
            btn_text = "white" if is_active or is_done else T['text']
            border = T['primary'] if is_active else T['border']
            
            # Vì Streamlit button không chỉnh style trực tiếp từng cái dễ dàng, ta dùng logic
            label = f"{i+1}"
            if cols[i % 5].button(label, key=f"nav_{i}", help="Đi tới câu này"):
                st.session_state.current_index = i
                st.rerun()
        
        st.caption("Xanh lá: Đã làm | Xanh dương: Đang chọn")

    # --- LEFT: QUESTION CONTENT ---
    with col_main:
        idx = st.session_state.current_index
        q_data = st.session_state.exam_data[idx]
        
        st.markdown(f"""
        <div class="q-card">
            <div class="q-title">Câu {idx + 1}: {q_data['question']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Radio button để chọn đáp án
        # Lưu ý: Cần xử lý default value nếu đã chọn trước đó
        prev_ans = st.session_state.user_answers.get(idx, None)
        
        user_choice = st.radio(
            "Chọn đáp án:", 
            q_data['options'], 
            index=q_data['options'].index(prev_ans) if prev_ans else None,
            key=f"q_{idx}",
            label_visibility="collapsed"
        )
        
        # Lưu đáp án ngay khi chọn (Auto-save state)
        if user_choice:
            st.session_state.user_answers[idx] = user_choice

        # Nút điều hướng Previous/Next
        c_prev, c_next = st.columns(2)
        if c_prev.button("⬅️ Câu trước", disabled=(idx==0)):
            st.session_state.current_index -= 1
            st.rerun()
        if c_next.button("Câu tiếp theo ➡️", disabled=(idx==total_q-1), type="primary"):
            st.session_state.current_index += 1
            st.rerun()

# --- 6. UI: MÀN HÌNH PAUSE ---
def render_paused():
    st.markdown(f"""
    <div style="text-align: center; padding-top: 100px;">
        <h1 style="font-size: 80px;">⏸️</h1>
        <h2>BÀI THI ĐANG TẠM DỪNG</h2>
        <p>Thí sinh: {st.session_state.user_name}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        if st.button("▶️ TIẾP TỤC LÀM BÀI", type="primary", use_container_width=True):
            # Tính toán bù giờ
            paused_duration = time.time() - st.session_state.pause_time
            st.session_state.start_time += paused_duration # Dời thời gian bắt đầu để bù giờ
            st.session_state.exam_status = "running"
            st.rerun()

# --- 7. UI: MÀN HÌNH KẾT QUẢ (REVIEW) ---
def render_review():
    st.markdown(f"<h2 style='text-align: center; color: {T['primary']}'>KẾT QUẢ BÀI THI</h2>", unsafe_allow_html=True)
    
    score = 0
    total = len(st.session_state.exam_data)
    
    for i, q in enumerate(st.session_state.exam_data):
        user_ans = st.session_state.user_answers.get(i, "Chưa trả lời")
        correct_ans = q['correct_answer']
        
        is_correct = (user_ans == correct_ans)
        if is_correct: score += 1
        
        # Màu sắc kết quả
        bg_res = "#E8F5E9" if is_correct else "#FFEBEE" # Xanh nhẹ / Đỏ nhẹ
        border_res = "green" if is_correct else "red"
        icon = "✅" if is_correct else "❌"
        
        # Hiển thị từng câu (Light mode style for review for clarity)
        st.markdown(f"""
        <div style="background-color: {bg_res}; padding: 15px; border-radius: 8px; border-left: 5px solid {border_res}; margin-bottom: 10px; color: black;">
            <strong>Câu {i+1}: {q['question']}</strong><br>
            Your answer: {user_ans} {icon}<br>
            Correct: <b>{correct_ans}</b><br>
            <em>Giải thích: {q['explanation']}</em>
        </div>
        """, unsafe_allow_html=True)

    final_score = round((score / total) * 10, 2)
    st.markdown(f"### Tổng điểm: {final_score} / 10")
    
    if st.button("Làm bài mới 🔄"):
        st.session_state.exam_data = []
        st.session_state.user_answers = {}
        st.session_state.current_index = 0
        st.session_state.exam_status = "setup"
        st.rerun()

# --- MAIN APP ---
if st.session_state.exam_status == "setup":
    render_setup()
elif st.session_state.exam_status == "running":
    render_exam()
elif st.session_state.exam_status == "paused":
    render_paused()
elif st.session_state.exam_status == "review":
    render_review()
