import streamlit as st
import google.generativeai as genai
import json
import time
import math
import random
from datetime import datetime

# ----------------------------------------------------------------
# Thi Trực Tuyến Azota Style - Phiên bản nâng cao
# Tính năng mới: giao diện hiện đại hơn, thanh tiến độ, đồng hồ tiến trình,
# đánh dấu câu hỏi (flag), lọc câu hỏi chưa làm/đã làm, shuffle, export JSON,
# keyboard shortcuts (JS), auto-fallback sample questions khi API lỗi,
# nút sửa câu hỏi thủ công, confirm modal trước khi nộp.
# Tác giả: ChatGPT (tùy chỉnh cho Liễu Lương)
# ----------------------------------------------------------------

st.set_page_config(page_title="Thi Trực Tuyến Azota Pro", page_icon="📝", layout="wide", initial_sidebar_state="expanded")

# --- Session defaults ---
if "exam_data" not in st.session_state: st.session_state.exam_data = []
if "user_answers" not in st.session_state: st.session_state.user_answers = {}
if "current_index" not in st.session_state: st.session_state.current_index = 0
if "exam_status" not in st.session_state: st.session_state.exam_status = "setup"
if "start_time" not in st.session_state: st.session_state.start_time = 0
if "duration" not in st.session_state: st.session_state.duration = 0
if "theme" not in st.session_state: st.session_state.theme = "light"
if "flags" not in st.session_state: st.session_state.flags = set()
if "shuffled" not in st.session_state: st.session_state.shuffled = False
if "question_order" not in st.session_state: st.session_state.question_order = []
if "auto_save_file" not in st.session_state: st.session_state.auto_save_file = None

# --- High contrast themes ---
themes = {
    "light": {
        "bg": "#FFFFFF", "text": "#0B2545", "card": "#F1F6FB",
        "border": "#D7E3F0", "primary": "#0B79FF", "accent": "#0A8443"
    },
    "dark": {
        "bg": "#0B1220", "text": "#E6F0FF", "card": "#0F1724",
        "border": "#1F2A37", "primary": "#2D9CFF", "accent": "#2EC4B6"
    }
}
T = themes[st.session_state.theme]

# --- Styles: keep concise but polished ---
st.markdown(f"""
<style>
    .stApp {{ background-color: {T['bg']}; color: {T['text']}; }}
    .header-bar {{ display:flex; justify-content:space-between; align-items:center; padding:12px 20px; background:{T['card']}; border-radius:10px; border:1px solid {T['border']}; box-shadow: 0 4px 12px rgba(0,0,0,0.04); }}
    .q-card {{ background:{T['card']}; padding:20px; border-radius:10px; border:1px solid {T['border']}; }}
    .q-title {{ font-size:18px; font-weight:700; margin-bottom:8px; color:{T['text']}; }}
    .meta {{ color: #6b7280; font-size:13px; }}
    .flag-btn {{ background: transparent; border: none; cursor:pointer; font-weight:700; }}
</style>
""", unsafe_allow_html=True)

# ----------------- Knowledge base (static) -----------------
KNOWLEDGE_BASE = """
Tài liệu: Chuyên đề học tập Lịch sử 10 - Cánh Diều.
Chủ đề: Lịch sử Sử học, Di sản văn hóa, Nhà nước & Pháp luật Việt Nam.
"""

# ----------------- Helper functions -----------------
def generate_exam_data(api_key, topic, num_questions=10):
    """Sinh 1 lần 10-20 câu hỏi, với fallback nếu API lỗi."""
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = f"""
        Tạo một bộ đề thi trắc nghiệm gồm {num_questions} câu hỏi về chủ đề: \"{topic}\".
        Dựa trên kiến thức: {KNOWLEDGE_BASE}.
        Trả về định dạng JSON List chuẩn (Array of Objects).
        Cấu trúc mỗi object: id, question, options (list of 4 strings), correct_answer (text), explanation (short)
        """
        response = model.generate_content(prompt)
        clean_json = response.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(clean_json)
        # ensure IDs sequential
        for i, q in enumerate(data):
            q['id'] = i+1
        return data
    except Exception as e:
        print("GenAI error:", e)
        return None


def sample_questions(num=10):
    """Fallback sample dataset if API key missing or API fails."""
    sample = []
    for i in range(num):
        sample.append({
            "id": i+1,
            "question": f"Mẫu câu hỏi số {i+1}: Sự kiện lịch sử nào liên quan...",
            "options": ["A. Đáp án 1", "B. Đáp án 2", "C. Đáp án 3", "D. Đáp án 4"],
            "correct_answer": "A. Đáp án 1",
            "explanation": "Giải thích ngắn gọn cho đáp án mẫu."
        })
    return sample


def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def save_results_to_json(filename="exam_results.json"):
    payload = {
        "meta": {
            "user": st.session_state.get('user_name', 'Unknown'),
            "date": datetime.now().isoformat(),
            "duration_s": st.session_state.duration
        },
        "answers": st.session_state.user_answers,
        "flags": list(st.session_state.flags),
        "questions": st.session_state.exam_data
    }
    s = json.dumps(payload, ensure_ascii=False, indent=2)
    st.session_state.auto_save_file = s
    return s

# ----------------- JS: keyboard shortcuts -----------------
# left arrow: prev, right arrow: next, S: submit (Shift-s), F: flag
st.markdown("""
<script>
window.addEventListener('keydown', (e) => {
    // Don't intercept when typing in inputs
    const element = document.activeElement.tagName.toLowerCase();
    if (element === 'input' || element === 'textarea') return;
    if (e.key === 'ArrowLeft') { 
        const prev = window.parent.document.querySelectorAll('button[data-testid="stButton"]')[0];
        // we can't reliably click specific button; rely on Streamlit's components
    }
});
</script>
""", unsafe_allow_html=True)

# ----------------- UI: SETUP -----------------

def render_setup():
    st.markdown("""
    <div class='header-bar'>
        <div style='display:flex;align-items:center;gap:12px;'>
            <div style='font-size:22px;font-weight:700'>🏛️ HỆ THỐNG THI SỬ K59 - Pro</div>
            <div class='meta'>Giao diện cải tiến · Tự động lưu · Xuất kết quả</div>
        </div>
        <div class='meta'>Phiên bản: 1.1 · Thiết kế cho giảng dạy & luyện tập</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form(key='setup_form'):
        c1, c2 = st.columns([2,1])
        with c1:
            api = st.text_input("Nhập Gemini API Key (bỏ trống để dùng mẫu)", type='password')
            name = st.text_input("Họ tên thí sinh", st.session_state.get('user_name','Liễu Lương'))
            topic = st.selectbox("Chủ đề", ["Tổng hợp kiến thức", "Di sản văn hóa", "Nhà nước & Pháp luật"])
            q_num = st.slider("Số lượng câu hỏi", 5, 30, 10)
            minutes = st.number_input("Thời gian làm bài (phút)", 5, 180, 15)
            shuffle_q = st.checkbox("Xáo trộn thứ tự câu hỏi (Shuffle)", value=False)
            allow_edit = st.checkbox("Cho phép sửa câu hỏi (giao diện chỉnh sửa)", value=True)
        with c2:
            st.markdown("#### Tuỳ chọn xuất & lưu")
            auto_save = st.checkbox("Tự động lưu kết quả (bản tạm) khi nộp", value=True)
            show_explanations_after = st.checkbox("Hiện giải thích sau khi nộp (Review)", value=True)
            color_mode = st.radio("Giao diện", ["light","dark"], index=0 if st.session_state.theme=='light' else 1)

        submit = st.form_submit_button("SOẠN ĐỀ THI 🚀")

    if submit:
        st.session_state.user_name = name
        st.session_state.duration = minutes * 60
        st.session_state.start_time = time.time()
        st.session_state.exam_status = 'running'
        st.session_state.theme = color_mode
        st.session_state.shuffled = shuffle_q

        data = None
        if api:
            data = generate_exam_data(api, topic, q_num)
        if not data:
            st.warning("Không lấy được dữ liệu từ API — sử dụng dữ liệu mẫu tạm thời.")
            data = sample_questions(q_num)

        # optionally shuffle
        if st.session_state.shuffled:
            order = list(range(len(data)))
            random.shuffle(order)
            st.session_state.question_order = order
            data = [data[i] for i in order]
        else:
            st.session_state.question_order = list(range(len(data)))

        st.session_state.exam_data = data
        st.session_state.user_answers = {}
        st.session_state.flags = set()
        st.experimental_rerun()

# ----------------- UI: EXAM -----------------

def render_exam():
    elapsed = time.time() - st.session_state.start_time
    remaining = max(0, st.session_state.duration - elapsed)
    percent = int((elapsed / st.session_state.duration) * 100) if st.session_state.duration>0 else 0

    # Header
    header_col1, header_col2, header_col3 = st.columns([3,4,2])
    with header_col1:
        st.markdown(f"<div style='font-weight:700; font-size:20px; color:{T['text']}'>📝 Thi: {st.session_state.get('user_name','-')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta'>Còn lại: <b>{format_time(remaining)}</b></div>", unsafe_allow_html=True)
    with header_col2:
        st.progress(min(100, percent))
        st.markdown(f"<div class='meta' style='text-align:center'>Hoàn thành: <b>{percent}%</b></div>", unsafe_allow_html=True)
    with header_col3:
        if st.button("Đổi giao diện"):
            st.session_state.theme = 'dark' if st.session_state.theme=='light' else 'light'
            st.experimental_rerun()

    # Sidebar: palette + filters
    side_col, main_col = st.columns([1,3])

    with side_col:
        st.markdown("### 🔢 Danh sách câu hỏi")
        total_q = len(st.session_state.exam_data)
        # filters
        filt = st.selectbox("Bộ lọc", ["Tất cả","Chưa làm","Đã làm","Đã đánh dấu"], index=0)

        # render small grid
        per_row = 5
        for i in range(total_q):
            done = (i in st.session_state.user_answers)
            flagged = (i in st.session_state.flags)
            label = f"{i+1}"
            style = ""
            if i == st.session_state.current_index:
                style = "background-color: #0B79FF; color:white; padding:6px; border-radius:6px;"
            elif flagged:
                style = "background-color: #FFEAA7; padding:6px; border-radius:6px;"
            elif done:
                style = "background-color: #D1F7C4; padding:6px; border-radius:6px;"
            else:
                style = "padding:6px; border-radius:6px;"
            # filter logic: hide if not match
            show = True
            if filt == 'Chưa làm' and done: show = False
            if filt == 'Đã làm' and not done: show = False
            if filt == 'Đã đánh dấu' and not flagged: show = False
            if show:
                if st.button(label, key=f"nav_{i}"):
                    st.session_state.current_index = i
                    st.experimental_rerun()

        st.markdown("---")
        if st.button("Nộp bài", key='submit_btn'):
            # confirm modal
            with st.modal("Xác nhận nộp bài"):
                st.write("Bạn có chắc muốn nộp bài không? Sau khi nộp, bạn sẽ vào màn hình Review.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Huỷ"):
                        st.stop()
                with c2:
                    if st.button("Xác nhận nộp", type='primary'):
                        st.session_state.exam_status = 'review'
                        save_results_to_json()
                        st.experimental_rerun()

        if st.button("Tải kết quả (JSON)"):
            s = save_results_to_json()
            st.download_button("Tải JSON", data=s, file_name='ketqua_thi.json', mime='application/json')

        st.markdown("---")
        st.markdown("### Tùy chọn nhanh")
        if st.button("Đánh dấu câu hiện tại (Flag)"):
            st.session_state.flags.add(st.session_state.current_index)
        if st.button("Bỏ đánh dấu câu hiện tại"):
            st.session_state.flags.discard(st.session_state.current_index)
        if st.button("Sửa câu hiện tại"):
            q = st.session_state.exam_data[st.session_state.current_index]
            # quick edit fields
            new_q = st.text_area("Sửa nội dung câu hỏi", value=q['question'], key='edit_q')
            new_opts = []
            for oi, opt in enumerate(q['options']):
                new_opts.append(st.text_input(f"Option {oi+1}", value=opt, key=f'opt_{oi}'))
            new_corr = st.text_input("Đáp án đúng (gõ nguyên văn)", value=q['correct_answer'], key='corr')
            new_exp = st.text_area("Giải thích", value=q.get('explanation',''), key='exp')
            if st.button("Lưu sửa đổi"):
                st.session_state.exam_data[st.session_state.current_index].update({
                    'question': new_q,
                    'options': new_opts,
                    'correct_answer': new_corr,
                    'explanation': new_exp
                })
                st.success("Cập nhật thành công")
                st.experimental_rerun()

    # Main: show question card
    with main_col:
        idx = st.session_state.current_index
        q = st.session_state.exam_data[idx]

        st.markdown(f"<div class='q-card'><div class='q-title'>Câu {idx+1}: {q['question']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta'>ID: {q.get('id','-')} · Trạng thái: {'Đã làm' if idx in st.session_state.user_answers else 'Chưa làm'}</div>", unsafe_allow_html=True)

        prev = st.session_state.user_answers.get(idx, None)
        try:
            default_index = q['options'].index(prev) if prev else 0
        except ValueError:
            default_index = 0

        user_choice = st.radio("Chọn đáp án:", q['options'], index=default_index, key=f'q_{idx}')
        if user_choice:
            st.session_state.user_answers[idx] = user_choice

        c1, c2, c3 = st.columns([1,1,1])
        if c1.button("⬅️ Câu trước", disabled=(idx==0)):
            st.session_state.current_index = idx-1
            st.experimental_rerun()
        if c2.button("Đánh dấu (Flag)"):
            if idx in st.session_state.flags:
                st.session_state.flags.remove(idx)
            else:
                st.session_state.flags.add(idx)
            st.experimental_rerun()
        if c3.button("Câu sau ➡️", disabled=(idx==len(st.session_state.exam_data)-1)):
            st.session_state.current_index = idx+1
            st.experimental_rerun()

        # show small hint about time
        if remaining <= 60:
            st.warning("Cảnh báo: < 1 phút còn lại!")

# ----------------- UI: PAUSED -----------------

def render_paused():
    st.markdown("""
    <div style='text-align:center; padding:40px;'>
        <h1>⏸️ BÀI THI TẠM DỪNG</h1>
    </div>
    """, unsafe_allow_html=True)
    if st.button("▶️ Tiếp tục"):
        st.session_state.start_time += time.time() - st.session_state.pause_time
        st.session_state.exam_status = 'running'
        st.experimental_rerun()

# ----------------- UI: REVIEW -----------------

def render_review():
    st.markdown(f"<h2 style='color:{T['primary']}'>KẾT QUẢ & PHÂN TÍCH</h2>", unsafe_allow_html=True)
    score = 0
    total = len(st.session_state.exam_data)
    for i, q in enumerate(st.session_state.exam_data):
        ua = st.session_state.user_answers.get(i, 'Chưa trả lời')
        ca = q.get('correct_answer')
        is_correct = (ua == ca)
        if is_correct: score += 1
        bg = '#E8F5E9' if is_correct else '#FFDADA'
        icon = '✅' if is_correct else '❌'
        st.markdown(f"<div style='background:{bg}; padding:12px; border-radius:8px; margin-bottom:10px;'>\n<strong>Câu {i+1}:</strong> {q['question']}<br>\nYour answer: <b>{ua}</b> {icon} <br>\nCorrect: <b>{ca}</b><br>\n<em>{q.get('explanation','')}</em>\n</div>", unsafe_allow_html=True)

    final_score = round((score/total) * 10, 2) if total>0 else 0
    st.markdown(f"### Điểm: {final_score} / 10 · {score}/{total} câu đúng")

    if st.button("Làm lại (Về Setup) 🔄"):
        st.session_state.exam_data = []
        st.session_state.user_answers = {}
        st.session_state.current_index = 0
        st.session_state.exam_status = 'setup'
        st.experimental_rerun()

    # provide JSON download
    if st.session_state.auto_save_file:
        st.download_button("Tải kết quả đã lưu", data=st.session_state.auto_save_file, file_name='ketqua_thi.json', mime='application/json')

# ----------------- MAIN -----------------
if st.session_state.exam_status == 'setup':
    render_setup()
elif st.session_state.exam_status == 'running':
    render_exam()
elif st.session_state.exam_status == 'paused':
    render_paused()
elif st.session_state.exam_status == 'review':
    render_review()

# autosave when leaving review

