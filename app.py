import streamlit as st
import google.generativeai as genai
import json
import os

# --- CẤU HÌNH TRANG & GIAO DIỆN (THEME XIAOMI/LEICA STYLE) ---
st.set_page_config(
    page_title="Sử K59 - Quiz Master",
    page_icon="📚",
    layout="centered"
)

# Custom CSS để giao diện đẹp, "nét" như ảnh Lossless
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f6;
    }
    .main-header {
        font-family: 'Helvetica Neue', sans-serif;
        color: #d32f2f; /* Màu đỏ Cánh Diều/Sư Phạm */
        text-align: center;
        font-weight: bold;
        padding-bottom: 20px;
    }
    .question-box {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border-left: 5px solid #d32f2f;
    }
    .stButton button {
        background-color: #ffffff;
        border: 1px solid #d32f2f;
        color: #d32f2f;
        border-radius: 8px;
        transition: 0.3s;
    }
    .stButton button:hover {
        background-color: #d32f2f;
        color: white;
    }
    .success-msg {
        color: #2e7d32;
        font-weight: bold;
        padding: 10px;
        background-color: #e8f5e9;
        border-radius: 5px;
    }
    .error-msg {
        color: #c62828;
        font-weight: bold;
        padding: 10px;
        background-color: #ffebee;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- DỮ LIỆU TỪ TÀI LIỆU CÁNH DIỀU (CONTEXT) ---
# Đây là phần "tinh hoa" được trích xuất từ file PDF của bạn để nạp cho AI
KNOWLEDGE_BASE = """
Tài liệu: Chuyên đề học tập Lịch sử 10 - Bộ sách Cánh Diều.
Gồm 3 chuyên đề chính:
1. CÁC LĨNH VỰC CỦA SỬ HỌC:
- Thông sử: Lịch sử toàn diện (chính trị, kinh tế, văn hóa...). Ví dụ: Đại Việt sử ký toàn thư.
- Lịch sử theo lĩnh vực: Lịch sử văn hóa, tư tưởng, kinh tế, xã hội.
- Phân biệt Lịch sử dân tộc (của 1 quốc gia) và Lịch sử thế giới (của nhân loại).
- Các bộ sử liệu quan trọng: Đại Nam thực lục, Lĩnh Nam chích quái (dã sử), Đại Việt thông sử.

2. BẢO TỒN VÀ PHÁT HUY GIÁ TRỊ DI SẢN VĂN HÓA:
- Khái niệm: Di sản văn hóa vật thể (thành quách, lăng tẩm...) và phi vật thể (nhã nhạc, cồng chiêng...).
- Xếp hạng di tích: Cấp tỉnh -> Cấp Quốc gia -> Cấp Quốc gia đặc biệt -> Di sản thế giới (UNESCO).
- Ví dụ di sản tiêu biểu: Cố đô Huế, Phố cổ Hội An, Thánh địa Mỹ Sơn, Hoàng thành Thăng Long, Vịnh Hạ Long (thiên nhiên), Tràng An (hỗn hợp/phức hợp).
- Di sản phi vật thể UNESCO: Nhã nhạc cung đình Huế, Cồng chiêng Tây Nguyên, Quan họ, Ca trù...

3. NHÀ NƯỚC VÀ PHÁP LUẬT TRONG LỊCH SỬ VIỆT NAM:
- Mô hình quân chủ: Thời Lý-Trần (quý tộc/thân dân), Lê Sơ (quan liêu chuyên chế điển hình), Nguyễn (chuyên chế cao độ).
- Bộ luật cổ: Quốc triều hình luật (Luật Hồng Đức - thời Lê Sơ, tiến bộ, bảo vệ phụ nữ), Hoàng Việt luật lệ (Luật Gia Long - thời Nguyễn, nghiêm khắc).
- Nhà nước VNDCCH (1945-1976): Ra đời 2/9/1945. Hiến pháp 1946 (đầu tiên).
- Nhà nước CHXHCNVN (1976-nay): Đổi tên từ 1976. Hiến pháp 1980, 1992 (thời kỳ đổi mới), 2013 (mới nhất).
"""

# --- XỬ LÝ GEMINI API ---
def get_quiz_from_gemini(api_key, topic):
    """Hàm gọi Gemini để sinh câu hỏi JSON"""
    if not api_key:
        st.warning("⚠️ Chưa nhập API Key kìa người anh em!")
        return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash') # Dùng bản Flash cho nhanh như điện

    prompt = f"""
    Đóng vai một giáo viên Lịch sử tâm huyết, vui tính.
    Dựa vào nội dung sau đây từ sách Chuyên đề Lịch sử 10 Cánh Diều:
    ---
    {KNOWLEDGE_BASE}
    ---
    Hãy tạo ra 1 câu hỏi trắc nghiệm về chủ đề: "{topic}".
    Yêu cầu định dạng trả về tuyệt đối phải là JSON (không có markdown ```json) với cấu trúc sau:
    {{
        "question": "Nội dung câu hỏi",
        "options": ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"],
        "correct_answer": "Đáp án đúng (chép y nguyên text của option đúng)",
        "explanation": "Giải thích ngắn gọn, thú vị tại sao đúng, dựa vào kiến thức sách giáo khoa."
    }}
    Chỉ trả về JSON, không thêm lời dẫn.
    """
    
    try:
        response = model.generate_content(prompt)
        # Làm sạch chuỗi json nếu lỡ Gemini thêm markdown
        clean_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_text)
    except Exception as e:
        st.error(f"Lỗi kết nối vệ tinh Gemini: {e}")
        return None

# --- GIAO DIỆN CHÍNH ---

def main():
    st.markdown("<h1 class='main-header'>🏛️ ĐẤU TRƯỜNG SỬ K59 - CÁNH DIỀU 🪁</h1>", unsafe_allow_html=True)
    
    # Sidebar cấu hình
    with st.sidebar:
        st.header("⚙️ Cấu hình thiết bị")
        api_key = st.text_input("Nhập Gemini API Key", type="password", help="Lấy tại aistudio.google.com")
        st.info("💡 Mẹo: Liễu Lương hãy nhập API Key để kích hoạt 'trí tuệ nhân tạo' nhé!")
        
        st.markdown("---")
        topic = st.selectbox(
            "Chọn chủ đề muốn ôn luyện:",
            ["Các lĩnh vực của Sử học", "Di sản văn hóa (Vật thể/Phi vật thể)", "Nhà nước & Pháp luật (Cổ trung đại)", "Hiến pháp Việt Nam (Hiện đại)"]
        )
        
        if st.button("🔄 Tạo câu hỏi mới", use_container_width=True):
            st.session_state.current_question = None
            st.session_state.user_answer = None
            st.session_state.submitted = False
            st.rerun()

    # Khởi tạo Session State (Bộ nhớ tạm của ứng dụng)
    if 'current_question' not in st.session_state:
        st.session_state.current_question = None
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    if 'score' not in st.session_state:
        st.session_state.score = 0

    # Logic sinh câu hỏi
    if st.session_state.current_question is None:
        if api_key:
            with st.spinner("Đang lục lọi thư tịch cổ... chờ chút nhé! ⏳"):
                quiz_data = get_quiz_from_gemini(api_key, topic)
                if quiz_data:
                    st.session_state.current_question = quiz_data
                    st.rerun()
        else:
            st.info("👈 Mời bạn nhập API Key bên tay trái để bắt đầu chuyến hành trình.")
            return

    # Hiển thị câu hỏi
    if st.session_state.current_question:
        q_data = st.session_state.current_question
        
        st.markdown(f"""
        <div class="question-box">
            <h3>🔥 Câu hỏi:</h3>
            <p style="font-size: 1.2em;">{q_data['question']}</p>
        </div>
        """, unsafe_allow_html=True)

        # Form trả lời
        with st.form("quiz_form"):
            choice = st.radio("Lựa chọn của bạn:", q_data['options'], index=None)
            submit_btn = st.form_submit_button("Chốt đáp án! 🚀")

            if submit_btn and choice:
                st.session_state.user_answer = choice
                st.session_state.submitted = True
            elif submit_btn and not choice:
                st.toast("Chưa chọn đáp án kìa bạn ơi!", icon="😅")

        # Xử lý kết quả
        if st.session_state.submitted:
            correct = q_data['correct_answer']
            user_choice = st.session_state.user_answer
            
            st.markdown("---")
            if user_choice == correct:
                st.markdown(f'<div class="success-msg">✅ Chính xác! Quá đẳng cấp!</div>', unsafe_allow_html=True)
                st.balloons()
            else:
                st.markdown(f'<div class="error-msg">❌ Sai mất rồi! Đáp án đúng là: {correct}</div>', unsafe_allow_html=True)
            
            # Giải thích (luôn hiện để học)
            with st.expander("📖 Xem giải thích chi tiết (Kiến thức Cánh Diều)", expanded=True):
                st.info(q_data['explanation'])
            
            # Nút Next
            if st.button("Câu tiếp theo ➡️"):
                st.session_state.current_question = None
                st.session_state.submitted = False
                st.rerun()

if __name__ == "__main__":
    main()
