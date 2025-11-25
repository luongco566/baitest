import streamlit as st
import json
import time
import random
from datetime import datetime
from io import BytesIO
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Path to uploaded screenshot (for reference). The platform will convert local path to URL where needed.
SCREENSHOT_PATH = "/mnt/data/1cb43eaf-1441-4d15-ae42-2f526840ef55.png"

st.set_page_config(page_title="Thi Trực Tuyến Azota Pro v3", page_icon="📝", layout="wide", initial_sidebar_state="expanded")

# ---------------- Session defaults ----------------
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

# ---------------- Themes & CSS ----------------
THEMES = {
    "light": {"bg": "#F7FAFF", "text": "#0B2545", "card": "#FFFFFF", "border": "#E6EEF8", "primary": "#0B79FF", "muted": "#6B7280"},
    "dark":  {"bg": "#08121A", "text": "#E6F0FF", "card": "#071622", "border": "#123047", "primary": "#66B2FF", "muted": "#9AAFC6"}
}
T = THEMES[st.session_state.theme]

st.markdown(f"""
<style>
:root {{ --bg: {T['bg']}; --text: {T['text']}; --card: {T['card']}; --border: {T['border']}; --primary: {T['primary']}; --muted: {T['muted']}; }}
body {{ background: var(--bg); color: var(--text); font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }}
.header {{ background: var(--card); padding:12px 18px; border-radius:12px; border:1px solid var(--border); margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; gap:12px }}
.q-card {{ background: var(--card); padding:18px; border-radius:12px; border:1px solid var(--border); margin-bottom:12px }}
.q-title {{ font-size:18px; font-weight:700; color:var(--text) }}
.meta {{ color: var(--muted); font-size:13px }}
.grid-btn {{ padding:6px 8px; border-radius:8px; margin:4px; border:1px solid var(--border); display:inline-block; min-width:36px; text-align:center }}
.grid-btn.active {{ background: var(--primary); color: white; border-color: var(--primary) }}
@media (max-width: 768px) {{ .header {{ flex-direction:column; align-items:flex-start }} }}
</style>
""", unsafe_allow_html=True)

# ---------------- Knowledge base ----------------
KNOWLEDGE_BASE = "Chuyên đề Lịch sử 10 - Cánh Diều. Chủ đề: Lịch sử Sử học, Di sản văn hóa, Nhà nước & Pháp luật VN."

# ---------------- Helpers ----------------

def sample_questions(num=10, weight=1.0):
    out = []
    for i in range(num):
        opts = [f"A. Phương án {i+1}-1", f"B. Phương án {i+1}-2", f"C. Phương án {i+1}-3", f"D. Phương án {i+1}-4"]
        random.shuffle(opts)
        out.append({
            'id': i+1,
            'question': f"Mẫu câu {i+1}: Đề bài mô phỏng...",
            'options': opts,
            'correct_answer': opts[0],
            'explanation': 'Giải thích ngắn cho câu mẫu',
            'weight': weight
        })
    return out


def format_time(s):
    m, sec = divmod(int(s), 60)
    return f"{m:02d}:{sec:02d}"


def compute_score(answers, questions, negative_mark=0.0):
    total = 0.0
    obtained = 0.0
    details = []
    for idx, q in enumerate(questions):
        w = float(q.get('weight', 1.0))
        total += w
        ua = answers.get(idx, None)
        ca = q.get('correct_answer')
        if ua is None:
            details.append({'index': idx, 'score': 0.0, 'weight': w, 'correct': False, 'ua': None})
        elif ua == ca:
            obtained += w
            details.append({'index': idx, 'score': w, 'weight': w, 'correct': True, 'ua': ua})
        else:
            obtained -= negative_mark
            details.append({'index': idx, 'score': -negative_mark, 'weight': w, 'correct': False, 'ua': ua})
    return obtained, total, details


def export_pdf(questions, filename, include_answers=False, title='Đề thi'):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    margin = 40
    y = height - margin
    c.setFont('Helvetica-Bold', 16)
    c.drawString(margin, y, title)
    c.setFont('Helvetica', 10)
    y -= 28
    for i, q in enumerate(questions):
        if y < margin + 80:
            c.showPage()
            y = height - margin
        text = f"Câu {i+1}. {q['question']}"
        c.drawString(margin, y, text)
        y -= 14
        for opt in q['options']:
            c.drawString(margin + 14, y, opt)
            y -= 12
        if include_answers:
            c.setFillColorRGB(0.1, 0.4, 0.1)
            c.drawString(margin + 14, y, f"Đáp án: {q.get('correct_answer')}")
            c.setFillColorRGB(0, 0, 0)
            y -= 12
        y -= 8
    c.save()
    return filename

# ---------------- UI: Setup ----------------

def render_setup():
    st.markdown('<div class="header"><div style="display:flex;flex-direction:column"><div style="font-size:18px;font-weight:700">📝 HỆ THỐNG THI SỬ K59 - Pro v3</div><div class="meta">Giao diện modern · In PDF · Xuất Google Sheets</div></div><div class="meta">Phiên bản: v3</div></div>', unsafe_allow_html=True)

    with st.form('form_setup'):
        c1, c2 = st.columns([3,1])
        with c1:
            api = st.text_input('Gemini API Key (bỏ trống dùng mẫu)', type='password')
            name = st.text_input('Họ tên thí sinh', st.session_state.get('user_name', '......'))
            topic = st.selectbox('Chủ đề', ['Tổng hợp kiến thức', 'Di sản văn hóa', 'Nhà nước & Pháp luật'])
            q_num = st.slider('Số lượng câu', 5, 20, 25 30, 10)
            minutes = st.number_input('Thời gian (phút)', 5, 180, 15)
            negative = st.number_input('Trừ điểm cho câu sai', 0.0, 5.0, 0.25, step=0.25)
            per_weight = st.number_input('Điểm mặc định/câu', 0.25, 10.0, 1.0, step=0.25)
            shuffle_q = st.checkbox('Xáo trộn câu (Shuffle)', value=False)
            shuffle_opts = st.checkbox('Xáo đáp án (Distractors)', value=True)
        with c2:
            st.markdown('#### Xuất & Lưu')
            auto_save = st.checkbox('Tự động lưu khi nộp', value=True)
            gs_file = st.file_uploader('Service Account JSON (Google Sheets) - tuỳ chọn', type=['json'])
            theme = st.radio('Giao diện', ['light', 'dark'], index=0 if st.session_state.theme=='light' else 1)
        submit = st.form_submit_button('Soạn đề (🚀)')

    if submit:
        st.session_state.user_name = name
        st.session_state.duration = minutes * 60
        st.session_state.start_time = time.time()
        st.session_state.exam_status = 'running'
        st.session_state.theme = theme
        st.session_state.negative_mark = negative
        data = sample_questions(q_num, per_weight)
        if shuffle_opts:
            for q in data:
                random.shuffle(q['options'])
        if shuffle_q:
            random.shuffle(data)
        st.session_state.exam_data = data
        st.session_state.user_answers = {}
        st.session_state.flags = set()
        st.session_state.question_order = list(range(len(data)))
        st.session_state.gs_service_account = None
        if gs_file:
            st.session_state.gs_service_account = gs_file.getvalue().decode('utf-8')
        st.experimental_rerun()

# ---------------- UI: Exam ----------------

def render_exam():
    elapsed = time.time() - st.session_state.start_time
    remaining = max(0, st.session_state.duration - elapsed)
    percent = int((elapsed / st.session_state.duration) * 100) if st.session_state.duration > 0 else 0

    h1, h2 = st.columns([3,1])
    with h1:
        st.markdown(f"<div style='font-weight:700; font-size:18px'>📝 Thi: {st.session_state.get('user_name')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta'>Còn lại: <b>{format_time(remaining)}</b></div>", unsafe_allow_html=True)
    with h2:
        if st.button('Đổi giao diện'):
            st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'
            st.experimental_rerun()

    left, right = st.columns([3,1])
    with right:
        st.markdown('### 🔢 Danh sách câu')
        total = len(st.session_state.exam_data)
        filt = st.selectbox('Bộ lọc', ['Tất cả', 'Chưa làm', 'Đã làm', 'Đã đánh dấu'])
        for i in range(total):
            done = (i in st.session_state.user_answers)
            flagged = (i in st.session_state.flags)
            if filt == 'Chưa làm' and done: continue
            if filt == 'Đã làm' and not done: continue
            if filt == 'Đã đánh dấu' and not flagged: continue
            label = str(i+1)
            if i == st.session_state.current_index:
                st.markdown(f"<span class='grid-btn active'>{label}</span>", unsafe_allow_html=True)
            elif flagged:
                st.markdown(f"<span class='grid-btn' style='background:#FFEAA7'>{label}</span>", unsafe_allow_html=True)
            elif done:
                st.markdown(f"<span class='grid-btn' style='background:#D1F7C4'>{label}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='grid-btn'>{label}</span>", unsafe_allow_html=True)
            if st.button(f'goto_{i}', key=f'goto_{i}'):
                st.session_state.current_index = i
                st.experimental_rerun()
        st.markdown('---')
        if st.button('Nộp bài'):
            st.session_state.exam_status = 'review'
            st.session_state.auto_save_file = json.dumps({'user': st.session_state.get('user_name'), 'answers': st.session_state.user_answers}, ensure_ascii=False, indent=2)
            st.experimental_rerun()

    with left:
        idx = st.session_state.current_index
        q = st.session_state.exam_data[idx]
        st.markdown(f"<div class='q-card'><div class='q-title'>Câu {idx+1}: {q['question']}</div></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta'>Điểm: {q.get('weight', 1.0)} · ID: {q.get('id')}</div>", unsafe_allow_html=True)

        prev = st.session_state.user_answers.get(idx, None)
        try:
            default_index = q['options'].index(prev) if prev else 0
        except ValueError:
            default_index = 0
        choice = st.radio('Chọn đáp án:', q['options'], index=default_index, key=f'q_{idx}')
        if choice:
            st.session_state.user_answers[idx] = choice

        c1, c2, c3 = st.columns([1,1,1])
        if c1.button('⬅️ Câu trước', disabled=(idx==0)):
            st.session_state.current_index = idx - 1
            st.experimental_rerun()
        if c2.button('Flag (F)'):
            if idx in st.session_state.flags:
                st.session_state.flags.remove(idx)
            else:
                st.session_state.flags.add(idx)
            st.experimental_rerun()
        if c3.button('Câu sau ➡️', disabled=(idx==len(st.session_state.exam_data)-1)):
            st.session_state.current_index = idx + 1
            st.experimental_rerun()

# ---------------- UI: Review ----------------

def render_review():
    st.markdown('<h2>Kết quả & Phân tích</h2>', unsafe_allow_html=True)
    obtained, total, details = compute_score(st.session_state.user_answers, st.session_state.exam_data, negative_mark=st.session_state.negative_mark)
    st.markdown(f"### Điểm: {obtained} / {total}")

    correct = sum(1 for d in details if d['correct'])
    wrong = sum(1 for d in details if (not d['correct'] and d['ua'] is not None))
    unanswered = sum(1 for d in details if d['ua'] is None)

    fig, ax = plt.subplots(figsize=(4,3))
    labels = ['Đúng', 'Sai', 'Chưa trả lời']
    vals = [correct, wrong, unanswered]
    ax.bar(labels, vals)
    ax.set_title('Tổng quan kết quả')
    ax.set_ylabel('Số câu')
    buf = BytesIO()
    fig.tight_layout()
    plt.savefig(buf, format='png')
    buf.seek(0)
    st.image(buf)

    for d in details:
        i = d['index']
        q = st.session_state.exam_data[i]
        ua = d['ua'] if d['ua'] is not None else 'Chưa trả lời'
        ca = q.get('correct_answer')
        w = d['weight']
        color = '#E8F5E9' if d['correct'] else ('#FFDADA' if ua != 'Chưa trả lời' else '#FFF5E1')
        st.markdown(f"<div style='background:{color}; padding:10px; border-radius:8px; margin-bottom:8px;'>
<strong>Câu {i+1} (điểm {w}):</strong> {q['question']}<br>
Your answer: <b>{ua}</b> · Correct: <b>{ca}</b><br>
<em>{q.get('explanation','')}</em>
</div>", unsafe_allow_html=True)

    if st.button('In đề (PDF)'):
        path = export_pdf(st.session_state.exam_data, '/mnt/data/exam_print_v3.pdf', include_answers=False, title=f"Đề thi - {st.session_state.get('user_name')}")
        with open(path, 'rb') as f:
            st.download_button('Tải PDF đề', data=f, file_name='de_thi_v3.pdf', mime='application/pdf')
    if st.button('In đáp án (PDF)'):
        path = export_pdf(st.session_state.exam_data, '/mnt/data/exam_answers_v3.pdf', include_answers=True, title=f"Đáp án - {st.session_state.get('user_name')}")
        with open(path, 'rb') as f:
            st.download_button('Tải PDF đáp án', data=f, file_name='dap_an_v3.pdf', mime='application/pdf')

    if st.session_state.auto_save_file:
        st.download_button('Tải kết quả JSON', data=st.session_state.auto_save_file, file_name='ketqua_thi_v3.json', mime='application/json')

    if st.button('Về Setup'):
        st.session_state.exam_data = []
        st.session_state.user_answers = {}
        st.session_state.current_index = 0
        st.session_state.exam_status = 'setup'
        st.experimental_rerun()

# ---------------- Keyboard shortcuts (best-effort) ----------------
st.markdown('''
<script>
document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowLeft') {
        const prev = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Câu trước'));
        if (prev) prev.click();
    }
    if (e.key === 'ArrowRight') {
        const next = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Câu sau'));
        if (next) next.click();
    }
    if (e.key.toLowerCase() === 'f') {
        const flag = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Flag'));
        if (flag) flag.click();
    }
    if (e.key.toLowerCase() === 's') {
        const submit = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Nộp bài'));
        if (submit) submit.click();
    }
});
</script>
''', unsafe_allow_html=True)

# ---------------- Main ----------------
if st.session_state.exam_status == 'setup':
    render_setup()
elif st.session_state.exam_status == 'running':
    render_exam()
elif st.session_state.exam_status == 'review':
    render_review()
else:
    st.markdown('<h3>Trạng thái không xác định</h3>', unsafe_allow_html=True)

# End of file
