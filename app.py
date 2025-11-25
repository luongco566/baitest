import streamlit as st
import google.generativeai as genai
import json
import time
from datetime import datetime

# --- 1. CẤU HÌNH TRANG & CSS (GIAO DIỆN AZOTA STYLE) ---
st.set_page_config(
    page_title="Sử K59 - Thi Trực Tuyến",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS tùy chỉnh để giống Azota: Màu xanh chủ đạo, card bo tròn, đổ bóng nhẹ
st.markdown("""
<style>
    /* Tổng thể */
    .stApp {
        background-color: #f5f7fa; /* Màu nền xám xanh nhẹ */
    }
    
    /* Header chính */
    .main-header {
        color: #004d99; /* Xanh đậm Azota */
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 700;
        text-align: center;
        padding: 10px;
        background: white;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }

    /* Card câu hỏi */
    .question-card {
        background-color: white;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border-top: 5px solid #0084ff; /* Xanh Azota */
        margin-bottom: 20px;
    }
    
    .question-text {
        font-size: 1.3em;
        font-weight: 600;
        color: #333;
        line-height: 1.5;
    }

    /* Sidebar User Info */
    .user-card {
        background: linear-gradient(135deg, #0084ff 0%, #0055cc 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    
    /* Buttons */
    .stButton button {
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s;
    }
    /* Nút chính */
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }

    /* Trạng thái */
    .status-badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.8em;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. DỮ LIỆU KIẾN THỨC (TỪ PDF CÁNH DIỀU) ---
KNOWLEDGE_BASE = """
Tài liệu: Chuyên đề học tập Lịch sử 10 - Bộ sách Cánh Diều.
1. [cite_start]CÁC LĨNH VỰC CỦA SỬ HỌC: [cite: 38]
- Thông sử: Lịch sử toàn diện (chính trị, kinh tế, văn hóa...). [cite_start]VD: Lịch sử Việt Nam (Viện Sử học). [cite: 102]
- [cite_start]Lịch sử theo lĩnh vực: Lịch sử văn hóa [cite: 145][cite_start], tư tưởng [cite: 182][cite_start], kinh tế [cite: 256][cite_start], xã hội[cite: 212].
- [cite_start]Các bộ sử liệu: Đại Nam thực lục (Sử quán triều Nguyễn - Thông sử/Thực lục) [cite: 48][cite_start], Lĩnh Nam chích quái (Dã sử/Truyện kể) [cite: 64][cite_start], Đại Việt sử ký toàn thư (Sử biên niên)[cite: 77].

2. [cite_start]BẢO TỒN DI SẢN VĂN HÓA: [cite: 329]
- [cite_start]Phân loại: Vật thể (Thành quách, lăng tẩm...) [cite: 371] [cite_start]và Phi vật thể (Nhã nhạc, cồng chiêng...)[cite: 371].
- [cite_start]Xếp hạng: Cấp tỉnh -> Quốc gia -> Quốc gia đặc biệt -> Di sản thế giới[cite: 395].
- Di sản thế giới tại VN:
    + [cite_start]Vật thể: Cố đô Huế [cite: 553][cite_start], Hội An [cite: 403][cite_start], Mỹ Sơn [cite: 628][cite_start], Hoàng thành Thăng Long [cite: 617][cite_start], Thành nhà Hồ[cite: 585].
    + [cite_start]Phi vật thể: Nhã nhạc cung đình Huế [cite: 560][cite_start], Cồng chiêng Tây Nguyên [cite: 416][cite_start], Quan họ, Ca trù, Đờn ca tài tử[cite: 573].
    + [cite_start]Thiên nhiên: Vịnh Hạ Long [cite: 688][cite_start], Phong Nha - Kẻ Bàng[cite: 644].
    + [cite_start]Hỗn hợp: Tràng An (Duy nhất ĐNA)[cite: 737].

3. [cite_start]NHÀ NƯỚC & PHÁP LUẬT: [cite: 766]
- [cite_start]Thời Lý-Trần: Quân chủ quý tộc/thân dân[cite: 793].
- [cite_start]Thời Lê Sơ: Quân chủ quan liêu chuyên chế điển hình (Vua Lê Thánh Tông)[cite: 826].
- [cite_start]Thời Nguyễn: Chuyên chế tập quyền cao độ (Vua Minh Mạng cải cách hành chính 1832)[cite: 848].
- Bộ luật:
    + [cite_start]Quốc triều hình luật (Luật Hồng Đức): Thời Lê Sơ, tiến bộ, bảo vệ phụ nữ[cite: 874].
    + [cite_start]Hoàng Việt luật lệ (Luật Gia Long): Thời Nguyễn, nghiêm khắc, mô phỏng luật Thanh[cite: 884].
- [cite_start]Nhà nước VNDCCH: Ra đời 2/9/1945[cite: 899]. [cite_start]Hiến pháp 1946 (đầu tiên)[cite: 1000].
- [cite_start]Nhà nước CHXHCNVN: Đổi tên từ 1976[cite: 960]. [cite_start]Hiến pháp 1980, 1992 (Đổi mới) [cite: 1041][cite_start], 2013 (Mới nhất)[cite: 1054].
"""

# --- 3. HÀM XỬ LÝ LOGIC ---

def get_question(api_key, topic):
    """Gọi Gemini tạo câu hỏi"""
    if not api_key: return None
    
    # Cấu hình model (Dùng 1.5 Pro cho thông minh hoặc Flash cho nhanh)
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        prompt = f"""
        Bạn là hệ thống tạo đề thi trắc nghiệm Lịch sử chuyên nghiệp.
        Dựa vào kiến thức sau:
        {KNOWLEDGE_BASE}
        
        Hãy tạo 1 câu hỏi trắc nghiệm KHÓ và HAY về chủ đề: "{topic}".
        Yêu cầu JSON output:
        {{
            "question": "Câu hỏi...",
            "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
            "correct_answer": "Đáp án đúng (nguyên văn)",
            "explanation": "Giải thích ngắn gọn dựa trên sách giáo khoa."
        }}
        """
        response = model.generate_content(prompt)
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except Exception as e:
        st.error(f"Lỗi kết nối AI: {e}")
        return None

def save_progress():
    """Lưu dữ liệu phiên làm việc thành JSON"""
    data = {
        "user": st.session_state.user_name,
        "date": str(datetime.now()),
        "score": st.session_state.score,
        "total_attempted": st.session_state.count,
        "history": st.session_state.history
    }
    return json.dumps(data, indent=4, ensure_ascii=False)

# --- 4. CÁC MÀN HÌNH (SCREENS) ---

def render_login():
    """Màn hình đăng nhập"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='text-align: center; margin-top: 50px;'>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
        st.markdown("## ĐĂNG NHẬP HỆ THỐNG THI")
        st.markdown("</div>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            name = st.text_input("Họ và tên thí sinh:", placeholder="Ví dụ: Liễu Lương - Sử K59")
            api = st.text_input("Mã truy cập (API Key):", type="password")
            topic = st.selectbox("Chọn chuyên đề thi:", 
                               ["Tổng hợp kiến thức", "Di sản văn hóa", "Nhà nước & Pháp luật", "Lịch sử Sử học"])
            
            submitted = st.form_submit_button("BẮT ĐẦU LÀM BÀI ▶️", use_container_width=True)
            
            if submitted:
                if name and api:
                    st.session_state.user_name = name
                    st.session_state.api_key = api
                    st.session_state.topic = topic
                    st.session_state.page = "exam"
                    st.rerun()
                else:
                    st.warning("Vui lòng điền đầy đủ thông tin!")

def render_exam():
    """Màn hình làm bài thi chính"""
    # --- Sidebar: Thông tin & Điều khiển ---
    with st.sidebar:
        st.markdown(f"""
        <div class="user-card">
            <h3>👤 {st.session_state.user_name}</h3>
            <p>Chuyên đề: {st.session_state.topic}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Bảng điểm mini
        c1, c2 = st.columns(2)
        c1.metric("Điểm số", st.session_state.score)
        c2.metric("Số câu", st.session_state.count)
        
        st.markdown("---")
        # Nút chức năng
        if st.button("⏸️ Tạm dừng làm bài", use_container_width=True):
            st.session_state.page = "paused"
            st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Lưu kết quả & Thoát", use_container_width=True):
            json_data = save_progress()
            st.download_button(
                label="📥 Tải file kết quả (.json)",
                data=json_data,
                file_name=f"ket_qua_{st.session_state.user_name}.json",
                mime="application/json"
            )

    # --- Main Content ---
    st.markdown(f"<h2 class='main-header'>🏛️ ĐỀ THI: {st.session_state.topic.upper()}</h2>", unsafe_allow_html=True)

    # Logic lấy câu hỏi
    if st.session_state.current_q is None:
        with st.spinner("🤖 AI đang biên soạn câu hỏi..."):
            st.session_state.current_q = get_question(st.session_state.api_key, st.session_state.topic)
            st.session_state.q_start_time = time.time()
            st.rerun()

    # Hiển thị câu hỏi
    q = st.session_state.current_q
    if q:
        st.markdown(f"""
        <div class="question-card">
            <div class="status-badge" style="background:#e3f2fd; color:#0d47a1;">Câu hỏi số {st.session_state.count + 1}</div>
            <p class="question-text">{q['question']}</p>
        </div>
        """, unsafe_allow_html=True)

        # Khu vực trả lời
        answer = st.radio("Chọn đáp án của bạn:", q['options'], index=None, key="radio_ans")
        
        col_submit, col_next = st.columns([1, 4])
        
        # Logic nút bấm
        if not st.session_state.ans_submitted:
            if col_submit.button("Chốt đáp án 🔒", type="primary"):
                if answer:
                    st.session_state.ans_submitted = True
                    if answer == q['correct_answer']:
                        st.session_state.score += 10
                        st.success("🎉 Chính xác! +10 điểm")
                    else:
                        st.error(f"❌ Sai rồi! Đáp án đúng: {q['correct_answer']}")
                    
                    # Lưu lịch sử
                    st.session_state.history.append({
                        "q": q['question'],
                        "user_ans": answer,
                        "correct": q['correct_answer'],
                        "is_correct": answer == q['correct_answer']
                    })
                    st.rerun()
                else:
                    st.toast("Bạn chưa chọn đáp án!", icon="⚠️")
        else:
            # Hiện giải thích sau khi trả lời
            st.info(f"💡 **Giải thích:** {q['explanation']}")
            if col_submit.button("Câu tiếp theo ➡️"):
                st.session_state.current_q = None
                st.session_state.ans_submitted = False
                st.session_state.count += 1
                st.rerun()

def render_paused():
    """Màn hình tạm dừng"""
    st.markdown("<div style='text-align: center; padding-top: 100px;'>", unsafe_allow_html=True)
    st.markdown("<h1>⏸️</h1>", unsafe_allow_html=True)
    st.markdown("## BÀI THI ĐANG ĐƯỢC TẠM DỪNG")
    st.markdown(f"Thí sinh: **{st.session_state.user_name}** | Điểm hiện tại: **{st.session_state.score}**")
    st.markdown("Hít thở sâu và quay lại khi đã sẵn sàng nhé!")
    
    if st.button("▶️ Tiếp tục làm bài", type="primary"):
        st.session_state.page = "exam"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- 5. HÀM MAIN (KHỞI TẠO APP) ---

def main():
    # Khởi tạo Session State
    if "page" not in st.session_state: st.session_state.page = "login"
    if "score" not in st.session_state: st.session_state.score = 0
    if "count" not in st.session_state: st.session_state.count = 0
    if "current_q" not in st.session_state: st.session_state.current_q = None
    if "ans_submitted" not in st.session_state: st.session_state.ans_submitted = False
    if "history" not in st.session_state: st.session_state.history = []
    if "user_name" not in st.session_state: st.session_state.user_name = ""

    # Điều hướng
    if st.session_state.page == "login":
        render_login()
    elif st.session_state.page == "exam":
        render_exam()
    elif st.session_state.page == "paused":
        render_paused()

if __name__ == "__main__":
    main()
