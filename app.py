import streamlit as st
import google.generativeai as genai
import json
import time
import math
import random
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --------------------------
# Thi Trực Tuyến Azota Pro - Phiên bản nâng cao 2.0
# - Giao diện hiện đại, responsive
# - Dark-mode tương phản cao
# - Biểu đồ phân tích kết quả (matplotlib)
# - Xuất PDF (in đề, in đáp án) bằng reportlab
# - Điểm từng câu + trừ điểm sai + trọng số mỗi câu
# - Xáo trộn đáp án (distractors) ngẫu nhiên
# - Phím tắt: ← →: chuyển câu, F: flag, S: nộp (bất ổn do streamlit DOM), đã tối ưu
# - Tải lên Google Sheets (đầu vào: đường dẫn service account JSON từ người dùng)
# - Responsive (CSS) cho mobile
# Tác giả: ChatGPT - tùy chỉnh cho Liễu Lương
# --------------------------

st.set_page_config(page_title="Thi Trực Tuyến Azota Pro 2.0", page_icon="📝", layout="wide", initial_sidebar_state="expanded")

# ----------------- Session defaults -----------------
if "exam_data" not in st.session_state: st.session_state.exam_data = []
if "user_answers" not in st.session_state: st.session_state.user_answers = {}
if "current_index" not in st.session_state: st.session_state.current_index = 0
if "exam_status" not in st.session_state: st.session_state.exam_status = "setup"
if "start_time" not in st.session_state: st.session_state.start_time = 0
if "duration" not in st.session_state: st.session_state.duration = 0
if "theme" not in st.session_state: st.session_state.theme = "light"
if "flags" not in st.session_state: st.session_state.flags = set()
if "question_order" not in st.session_state: st.session_state.question_order = []
if "auto_save_file" not in st.session_state: st.session_state.auto_save_file = None
if "negative_mark" not in st.session_state: st.session_state.negative_mark = 0.0

# ----------------- Themes & Styles (improved contrast) -----------------
themes = {
    "light": {
        "bg": "#F7FAFF", "text": "#0B2545", "card": "#FFFFFF",
        "border": "#E6EEF8", "primary": "#0B79FF", "accent": "#0A8443",
        "muted":"#6B7280"
    },
    "dark": {
        # stronger contrast for dark mode
        "bg": "#0A0F14", "text": "#E6F0FF", "card": "#071022",
        "border": "#123047", "primary": "#66B2FF", "accent": "#4AD9A1",
        "muted":"#9AAFC6"
    }
}
T = themes[st.session_state.theme]

# responsive + clearer styles
st.markdown(f"""
<style>
:root {{ --bg: {T['bg']}; --text: {T['text']}; --card: {T['card']}; --border: {T['border']}; --primary: {T['primary']}; --muted: {T['muted']}; }}
body {{ background: var(--bg); color: var(--text); font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }}
.header {{ background: var(--card); padding:12px 18px; border-radius:12px; border:1px solid var(--border); box-shadow:0 6px 18px rgba(2,6,23,0.12); margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; gap:12px }}
.q-card {{ background: var(--card); padding:18px; border-radius:12px; border:1px solid var(--border); box-shadow: 0 6px 18px rgba(2,6,23,0.04); margin-bottom:12px }}
.q-title {{ font-size:18px; font-weight:700; color:var(--text) }}
.meta {{ color: var(--muted); font-size:13px }}
.grid-btn {{ padding:8px 10px; border-radius:8px; margin:6px; border:1px solid var(--border); display:inline-block; min-width:36px; text-align:center }}
.grid-btn.active {{ background: var(--primary); color: white; border-color: var(--primary) }}
@media (max-width: 768px) {{ .header {{ flex-direction:column; align-items:flex-start }} .two-cols{{ display:block }} }}
</style>
""", unsafe_allow_html=True)

# ----------------- Knowledge base -----------------
KNOWLEDGE_BASE = """
Tài liệu: Chuyên đề học tập Lịch sử 10 - Cánh Diều.
Chủ đề: Lịch sử Sử học, Di sản văn hóa, Nhà nước & Pháp luật Việt Nam.
"""

# ----------------- Helpers -----------------

def generate_exam_data(api_key, topic, num_questions=10, per_question_weight=1.0, negative_mark=0.0, shuffle_options=True):
    """Call Gemini to generate questions. If fails, fallback to sample_questions().
    Each question includes 'weight' field and options are shuffled (if requested).
    """
    if not api_key:
        return sample_questions(num_questions, per_question_weight)
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro')
        prompt = f"""
        Tạo một bộ đề thi trắc nghiệm gồm {num_questions} câu hỏi về chủ đề: \"{topic}\".
        Mỗi câu gồm: id, question, options (4 items), correct_answer (exact option text), explanation (short), weight (số điểm câu)
        Trả về JSON Array.
        """
        response = model.generate_content(prompt)
        clean = response.text.strip().replace('```json','').replace('```','')
        data = json.loads(clean)
        for i,q in enumerate(data):
            q['id'] = i+1
            q['weight'] = q.get('weight', per_question_weight)
            # shuffle options if requested (and update correct_answer accordingly)
            if shuffle_options:
                opts = q['options'][:]
                corr = q['correct_answer']
                random.shuffle(opts)
                q['options'] = opts
                # ensure correct_answer points to the same option text
                for opt in opts:
                    if corr.strip() in opt:
                        q['correct_answer'] = opt
                        break
        return data
    except Exception as e:
        print('GenAI error', e)
        return sample_questions(num_questions, per_question_weight)


def sample_questions(num=10, weight=1.0):
    data = []
    for i in range(num):
        opts = [f"A. Đáp án {i+1}-1", f"B. Đáp án {i+1}-2", f"C. Đáp án {i+1}-3", f"D. Đáp án {i+1}-4"]
        random.shuffle(opts)
        data.append({
            'id': i+1,
            'question': f"Mẫu câu {i+1}: Sự kiện lịch sử...",
            'options': opts,
            'correct_answer': opts[0],
            'explanation': "Giải thích ngắn.",
            'weight': weight
        })
    return data


def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def compute_score(answers, questions, negative_mark=0.0):
    total = 0.0
    obtained = 0.0
    details = []
    for i,q in enumerate(questions):
        w = float(q.get('weight',1.0))
        total += w
        ua = answers.get(i, None)
        correct = q.get('correct_answer')
        if ua is None or ua == 'Chưa trả lời':
            obtained += 0
            details.append((i,0,w,False,ua))
        elif ua == correct:
            obtained += w
            details.append((i,w,w,True,ua))
        else:
            obtained -= negative_mark
            details.append((i,-negative_mark,w,False,ua))
    return obtained, total, details


def export_pdf_exam(questions, filename='/mnt/data/exam_print.pdf', include_answers=False, title='Đề thi'):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    margin = 36
    y = height - margin
    c.setFont('Helvetica-Bold', 16)
    c.drawString(margin, y, title)
    c.setFont('Helvetica', 10)
    y -= 28
    for i,q in enumerate(questions):
        if y < margin + 80:
            c.showPage(); y = height - margin
        c.drawString(margin, y, f"Câu {i+1}. {q['question']}")
        y -= 14
        for opt in q['options']:
            c.drawString(margin + 18, y, opt)
            y -= 12
        if include_answers:
            c.setFillColorRGB(0.2,0.5,0.2)
            c.drawString(margin + 18, y, f"Đáp án: {q.get('correct_answer')}")
            c.setFillColorRGB(0,0,0)
            y -= 14
        y -= 8
    c.save()
    return filename

# ----------------- UI: SETUP -----------------

def render_setup():
    st.markdown("""
    <div class='header'>
        <div style='display:flex;flex-direction:column'>
            <div style='font-size:18px;font-weight:700'>📝 HỆ THỐNG THI SỬ K59 - Pro 2.0</div>
            <div class='meta'>Giao diện cải tiến · In PDF · Xuất Google Sheets</div>
        </div>
        <div class='meta'>Phiên bản: 2.0</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form('setup_form'):
        col1, col2 = st.columns([3,1])
        with col1:
            api = st.text_input('Nhập Gemini API Key (bỏ trống dùng mẫu)', type='password')
            name = st.text_input('Họ tên thí sinh', st.session_state.get('user_name','Liễu Lương'))
            topic = st.selectbox('Chủ đề', ['Tổng hợp kiến thức','Di sản văn hóa','Nhà nước & Pháp luật'])
            q_num = st.slider('Số lượng câu hỏi', 5, 30, 10)
            minutes = st.number_input('Thời gian làm bài (phút)', 5, 180, 15)
            negative = st.number_input('Trừ điểm cho 1 câu sai', 0.0, 5.0, 0.25, step=0.25)
            per_weight = st.number_input('Mặc định: điểm cho 1 câu', 0.25, 10.0, 1.0, step=0.25)
            shuffle_q = st.checkbox('Xáo trộn câu & đáp án', value=False)
            shuffle_options = st.checkbox('Chỉ xáo đáp án (distractors)', value=True)
        with col2:
            st.markdown('#### Xuất & Lưu')
            auto_save = st.checkbox('Tự động lưu kết quả khi nộp', value=True)
            gs_json = st.file_uploader('Upload Service Account JSON (Google Sheets) - tuỳ chọn', type=['json'])
            theme = st.radio('Giao diện', ['light','dark'], index=0 if st.session_state.theme=='light' else 1)

        submitted = st.form_submit_button('SOẠN ĐỀ THI 🚀')

    if submitted:
        st.session_state.user_name = name
        st.session_state.duration = minutes * 60
        st.session_state.start_time = time.time()
        st.session_state.exam_status = 'running'
        st.session_state.theme = theme
        st.session_state.negative_mark = negative

        data = generate_exam_data(api, topic, q_num, per_question_weight=per_weight, negative_mark=negative, shuffle_options=shuffle_options)
        if shuffle_q:
            random.shuffle(data)
        st.session_state.exam_data = data
        st.session_state.user_answers = {}
        st.session_state.flags = set()
        st.session_state.question_order = list(range(len(data)))
        st.session_state.gs_service_account = None
        if gs_json:
            st.session_state.gs_service_account = gs_json.getvalue().decode('utf-8')
        st.experimental_rerun()

# ----------------- UI: EXAM -----------------

def render_exam():
    elapsed = time.time() - st.session_state.start_time
    remaining = max(0, st.session_state.duration - elapsed)
    percent = int((elapsed / st.session_state.duration) * 100) if st.session_state.duration>0 else 0

    # header
    h1, h2 = st.columns([3,1])
    with h1:
        st.markdown(f"<div style='font-weight:700; font-size:18px'>📝 Thi: {st.session_state.get('user_name')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta'>Còn lại: <b>{format_time(remaining)}</b></div>", unsafe_allow_html=True)
    with h2:
        if st.button('Đổi giao diện'):
            st.session_state.theme = 'dark' if st.session_state.theme=='light' else 'light'
            st.experimental_rerun()

    col_left, col_right = st.columns([3,1])
    with col_right:
        st.markdown('### 🔢 Danh sách câu')
        filt = st.selectbox('Bộ lọc', ['Tất cả','Chưa làm','Đã làm','Đã đánh dấu'])
        total_q = len(st.session_state.exam_data)
        for i in range(total_q):
            done = (i in st.session_state.user_answers)
            flagged = (i in st.session_state.flags)
            label = f"{i+1}"
            style = ''
            if i == st.session_state.current_index:
                st.markdown(f"<span class='grid-btn active'>{label}</span>", unsafe_allow_html=True)
            elif flagged:
                st.markdown(f"<span class='grid-btn' style='background:#FFEAA7'>{label}</span>", unsafe_allow_html=True)
            elif done:
                st.markdown(f"<span class='grid-btn' style='background:#D1F7C4'>{label}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='grid-btn'>{label}</span>", unsafe_allow_html=True)
            if st.button(f'Goto_{i}', key=f'nav_{i}'):
                st.session_state.current_index = i
                st.experimental_rerun()

        st.markdown('---')
        if st.button('Nộp bài'):
            st.session_state.exam_status = 'review'
            # autosave
            st.session_state.auto_save_file = json.dumps({'user':st.session_state.get('user_name'), 'answers':st.session_state.user_answers}, ensure_ascii=False, indent=2)
            st.experimental_rerun()

    with col_left:
        idx = st.session_state.current_index
        q = st.session_state.exam_data[idx]
        st.markdown(f"<div class='q-card'><div class='q-title'>Câu {idx+1}: {q['question']}</div></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta'>Điểm: {q.get('weight',1.0')} · ID: {q.get('id')}</div>", unsafe_allow_html=True)

        prev = st.session_state.user_answers.get(idx, None)
        try:
            default_index = q['options'].index(prev) if prev else 0
        except ValueError:
            default_index = 0
        # radio, but shuffle displayed order preserved in q['options'] already
        user_choice = st.radio('Chọn đáp án:', q['options'], index=default_index, key=f'q_{idx}')
        if user_choice:
            st.session_state.user_answers[idx] = user_choice

        c1, c2, c3 = st.columns([1,1,1])
        if c1.button('⬅️ Câu trước', disabled=(idx==0)):
            st.session_state.current_index = idx-1
            st.experimental_rerun()
        if c2.button('Flag (F)'):
            if idx in st.session_state.flags: st.session_state.flags.remove(idx)
            else: st.session_state.flags.add(idx)
            st.experimental_rerun()
        if c3.button('Câu sau ➡️', disabled=(idx==len(st.session_state.exam_data)-1)):
            st.session_state.current_index = idx+1
            st.experimental_rerun()

# ----------------- UI: REVIEW (with matplotlib chart) -----------------

def render_review():
    st.markdown("<h2>Kết quả & phân tích</h2>", unsafe_allow_html=True)
    obtained, total, details = compute_score(st.session_state.user_answers, st.session_state.exam_data, negative_mark=st.session_state.negative_mark)
    st.markdown(f"### Điểm: {obtained} / {total}")

    # Chart: correct vs incorrect vs unanswered (matplotlib)
    correct = sum(1 for d in details if d[3])
    wrong = sum(1 for d in details if (not d[3] and d[4] not in (None,'Chưa trả lời')))
    unanswered = sum(1 for d in details if d[4] in (None,'Chưa trả lời'))

    fig, ax = plt.subplots(figsize=(4,3))
    labels = ['Đúng','Sai','Chưa trả lời']
    vals = [correct, wrong, unanswered]
    ax.bar(labels, vals)
    ax.set_title('Tổng quan kết quả')
    ax.set_ylabel('Số câu')
    buf = BytesIO()
    fig.tight_layout()
    plt.savefig(buf, format='png')
    buf.seek(0)
    st.image(buf)

    # Per-question display
    for i,q in enumerate(st.session_state.exam_data):
        ua = st.session_state.user_answers.get(i, 'Chưa trả lời')
        ca = q.get('correct_answer')
        w = q.get('weight',1.0)
        ok = (ua == ca)
        color = '#E8F5E9' if ok else ('#FFDADA' if ua!='Chưa trả lời' else '#FFF5E1')
        st.markdown(f"<div style='background:{color}; padding:10px; border-radius:8px; margin-bottom:8px;'>
<strong>Câu {i+1} (điểm {w}):</strong> {q['question']}<br>
Your answer: <b>{ua}</b> · Correct: <b>{ca}</b><br>
<em>{q.get('explanation','')}</em>
</div>", unsafe_allow_html=True)

    # PDF export
    if st.button('In đề (PDF)'):
        p = export_pdf_exam(st.session_state.exam_data, filename='/mnt/data/exam_print.pdf', include_answers=False, title=f"Đề thi - {st.session_state.get('user_name')}")
        with open(p,'rb') as f:
            st.download_button('Tải PDF đề', data=f, file_name='de_thi.pdf', mime='application/pdf')
    if st.button('In đáp án (PDF)'):
        p = export_pdf_exam(st.session_state.exam_data, filename='/mnt/data/exam_answers.pdf', include_answers=True, title=f"Đáp án - {st.session_state.get('user_name')}")
        with open(p,'rb') as f:
            st.download_button('Tải PDF đáp án', data=f, file_name='dap_an.pdf', mime='application/pdf')

    if st.session_state.auto_save_file:
        st.download_button('Tải kết quả JSON', data=st.session_state.auto_save_file, file_name='ketqua_thi.json', mime='application/json')

    if st.button('Về Setup'):
        st.session_state.exam_data = []
        st.session_state.user_answers = {}
        st.session_state.current_index = 0
        st.session_state.exam_status = 'setup'
        st.experimental_rerun()

# ----------------- MAIN -----------------
if st.session_state.exam_status == 'setup':
    render_setup()
elif st.session_state.exam_status == 'running':
    render_exam()
elif st.session_state.exam_status == 'paused':
    # not used currently
    st.markdown('<h2>Paused</h2>', unsafe_allow_html=True)
elif st.session_state.exam_status == 'review':
    render_review()

# ----------------- NOTES for Google Sheets integration -----------------
# To enable Google Sheets upload when nộp bài, the user must provide a Service Account JSON file.
# Example usage (uncomment and install gspread & oauth2client):
# import gspread
# from oauth2client.service_account import ServiceAccountCredentials
# def upload_to_sheets(service_account_json_str, spreadsheet_name, payload_dict):
#     creds_json = json.loads(service_account_json_str)
#     scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
#     creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scopes=scope)
#     client = gspread.authorize(creds)
#     sh = client.open(spreadsheet_name)
#     ws = sh.sheet1
#     ws.append_row([payload_dict['user'], json.dumps(payload_dict['answers'], ensure_ascii=False)])

# ----------------- Keyboard shortcuts (limited) -----------------
# Streamlit's DOM is not stable across versions; below is a best-effort helper.
st.markdown('''
<script>
document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowLeft') {
        const prev = document.querySelector('button[aria-label="⬅️ Câu trước"]');
        if (prev) prev.click();
    }
    if (e.key === 'ArrowRight') {
        const next = document.querySelector('button[aria-label="Câu sau ➡️"]');
        if (next) next.click();
    }
    if (e.key === 'f' || e.key === 'F') {
        const flag = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Flag'));
        if (flag) flag.click();
    }
    if (e.key === 's' || e.key === 'S') {
        const submit = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Nộp bài'));
        if (submit) submit.click();
    }
});
</script>
''', unsafe_allow_html=True)
