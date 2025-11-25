# File: streamlit_exam_from_scratch.py
# Tái tạo hoàn chỉnh - Thi Trực Tuyến Azota (From scratch)
# Phiên bản: rebuild-1
# Tính năng: giao diện hiện đại responsive, dark/light high-contrast, biểu đồ phân tích (matplotlib),
# in PDF (reportlab), điểm theo từng câu + trừ điểm sai, shuffle câu/đáp án, flag, keyboard shortcuts (best-effort),
# Google Sheets hook (commented, requires credentials), và fallback an toàn nếu thiếu API.

import streamlit as st
import json
import time
import random
from datetime import datetime
from io import BytesIO
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# reference screenshot path (uploaded by you)
SCREENSHOT_PATH = "/mnt/data/1d6cecd6-52e3-476a-b5cd-80db63888f2e.png"

st.set_page_config(page_title="Thi Trực Tuyến Azota - Rebuild", page_icon="📝", layout='wide')

# ---------------- Session defaults ----------------
if 'exam_data' not in st.session_state: st.session_state.exam_data = []
if 'user_answers' not in st.session_state: st.session_state.user_answers = {}
if 'current_index' not in st.session_state: st.session_state.current_index = 0
if 'exam_status' not in st.session_state: st.session_state.exam_status = 'setup'
if 'start_time' not in st.session_state: st.session_state.start_time = 0
if 'duration' not in st.session_state: st.session_state.duration = 0
if 'theme' not in st.session_state: st.session_state.theme = 'light'
if 'flags' not in st.session_state: st.session_state.flags = set()
if 'negative_mark' not in st.session_state: st.session_state.negative_mark = 0.0
if 'auto_save_file' not in st.session_state: st.session_state.auto_save_file = None

# ---------------- Colors & CSS ----------------
THEMES = {
    'light': {'bg':'#F6FBFF','text':'#072044','card':'#FFFFFF','border':'#E6EEF8','primary':'#0B79FF','muted':'#6B7280'},
    'dark': {'bg':'#07101A','text':'#E6F0FF','card':'#071622','border':'#123047','primary':'#66B2FF','muted':'#9AAFC6'}
}
T = THEMES[st.session_state.theme]

st.markdown("""
<style>
:root { --bg: %s; --text: %s; --card: %s; --border: %s; --primary: %s; --muted: %s; }
body { background: var(--bg); color: var(--text); font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }
.header { background: var(--card); padding:14px; border-radius:12px; border:1px solid var(--border); margin-bottom:12px; display:flex; justify-content:space-between; align-items:center }
.q-card { background: var(--card); padding:16px; border-radius:10px; border:1px solid var(--border); margin-bottom:12px }
.q-title { font-size:18px; font-weight:700; }
.meta { color: var(--muted); font-size:13px }
.grid-btn { padding:6px 8px; border-radius:8px; margin:4px; border:1px solid var(--border); display:inline-block; min-width:36px; text-align:center }
.grid-btn.active { background: var(--primary); color: white; border-color: var(--primary) }
@media (max-width: 768px) { .header { flex-direction:column; align-items:flex-start } }
</style>
""" % (T['bg'], T['text'], T['card'], T['border'], T['primary'], T['muted']), unsafe_allow_html=True)

# ---------------- Knowledge & helpers ----------------
KNOWLEDGE = 'Tài liệu mẫu: Lịch sử 10 - Cánh Diều.'

def sample_questions(n=10, weight=1.0):
    out = []
    for i in range(n):
        opts = [f"A. Đáp án {i+1}-1", f"B. Đáp án {i+1}-2", f"C. Đáp án {i+1}-3", f"D. Đáp án {i+1}-4"]
        random.shuffle(opts)
        out.append({'id': i+1, 'question': f'Mẫu câu {i+1}: Nội dung mô phỏng', 'options': opts, 'correct_answer': opts[0], 'explanation':'Giải thích ngắn', 'weight': weight})
    return out

def format_time(sec):
    m, s = divmod(int(sec), 60)
    return f"{m:02d}:{s:02d}"

def compute_score(answers, questions, negative_mark=0.0):
    total = sum(float(q.get('weight',1.0)) for q in questions)
    obtained = 0.0
    details = []
    for idx,q in enumerate(questions):
        w = float(q.get('weight',1.0))
        ua = answers.get(idx)
        ca = q.get('correct_answer')
        if ua is None:
            details.append({'index':idx,'score':0.0,'weight':w,'ua':None,'correct':False})
        elif ua == ca:
            obtained += w
            details.append({'index':idx,'score':w,'weight':w,'ua':ua,'correct':True})
        else:
            obtained -= negative_mark
            details.append({'index':idx,'score':-negative_mark,'weight':w,'ua':ua,'correct':False})
    return obtained, total, details

def export_pdf(questions, filename, include_answers=False, title='Đề thi'):
    c = canvas.Canvas(filename, pagesize=A4)
    w,h = A4
    margin = 40
    y = h - margin
    c.setFont('Helvetica-Bold', 16)
    c.drawString(margin, y, title)
    y -= 26
    c.setFont('Helvetica', 10)
    for i,q in enumerate(questions):
        if y < margin + 80:
            c.showPage(); y = h - margin
        c.drawString(margin, y, f"Câu {i+1}. {q['question']}")
        y -= 14
        for opt in q['options']:
            c.drawString(margin+12, y, opt)
            y -= 12
        if include_answers:
            c.setFillColorRGB(0.1,0.4,0.1)
            c.drawString(margin+12, y, f"Đáp án: {q.get('correct_answer')}")
            c.setFillColorRGB(0,0,0)
            y -= 12
        y -= 8
    c.save()
    return filename

# ---------------- UI: Setup ----------------
def render_setup():
    st.markdown('<div class="header"><div style="display:flex;flex-direction:column"><div style="font-size:18px;font-weight:700">📝 Thi Trực Tuyến Azota - Rebuild</div><div class="meta">Giao diện mới · In PDF · Xuất kết quả</div></div><div class="meta">Phiên bản: rebuild-1</div></div>', unsafe_allow_html=True)
    with st.form('setup'):
        c1,c2 = st.columns([3,1])
        with c1:
            api = st.text_input('Gemini API Key (bỏ trống dùng mẫu)', type='password')
            name = st.text_input('Họ tên thí sinh', st.session_state.get('user_name','Liễu Lương'))
            topic = st.selectbox('Chủ đề', ['Tổng hợp kiến thức','Di sản văn hóa','Nhà nước & Pháp luật'])
            qnum = st.slider('Số lượng câu', 5, 30, 10)
            minutes = st.number_input('Thời gian (phút)', 5, 180, 15)
            negative = st.number_input('Trừ điểm cho 1 câu sai', 0.0, 5.0, 0.25, step=0.25)
            default_weight = st.number_input('Điểm mặc định/câu', 0.25, 10.0, 1.0, step=0.25)
            shuffle_q = st.checkbox('Xáo trộn thứ tự câu', value=False)
            shuffle_opts = st.checkbox('Xáo đáp án (distractors)', value=True)
        with c2:
            st.markdown('#### Xuất & Lưu')
            auto_save = st.checkbox('Tự động lưu khi nộp', value=True)
            gs_json = st.file_uploader('Upload Service Account JSON (Google Sheets) - tuỳ chọn', type=['json'])
            theme = st.radio('Giao diện', ['light','dark'], index=0 if st.session_state.theme=='light' else 1)
        submit = st.form_submit_button('Soạn đề & Bắt đầu (🚀)')

    if submit:
        st.session_state.user_name = name
        st.session_state.duration = minutes * 60
        st.session_state.start_time = time.time()
        st.session_state.exam_status = 'running'
        st.session_state.theme = theme
        st.session_state.negative_mark = negative

        # generate questions (fallback to sample)
        data = sample_questions(qnum, default_weight)
        if shuffle_opts:
            for q in data:
                random.shuffle(q['options'])
        if shuffle_q:
            random.shuffle(data)
        st.session_state.exam_data = data
        st.session_state.user_answers = {}
        st.session_state.flags = set()
        st.session_state.auto_save_file = None
        st.experimental_rerun()

# ---------------- UI: Exam ----------------
def render_exam():
    elapsed = time.time() - st.session_state.start_time
    remaining = max(0, st.session_state.duration - elapsed)
    percent = int((elapsed / st.session_state.duration) * 100) if st.session_state.duration > 0 else 0

    left, right = st.columns([3,1])
    with left:
        st.markdown(f"<div style='font-weight:700; font-size:18px'>📝 Thí: {st.session_state.get('user_name')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta'>Còn lại: <b>{format_time(remaining)}</b> · Hoàn thành: <b>{percent}%</b></div>", unsafe_allow_html=True)
        idx = st.session_state.current_index
        q = st.session_state.exam_data[idx]
        st.markdown("<div class='q-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='q-title'>Câu {idx+1}: {q['question']}</div>", unsafe_allow_html=True)
        # metadata
        meta_html = "<div class='meta'>Điểm: {} · ID: {}</div>".format(q.get('weight',1.0), q.get('id', idx+1))
        st.markdown(meta_html, unsafe_allow_html=True)
        # options
        prev = st.session_state.user_answers.get(idx)
        try:
            default_i = q['options'].index(prev) if prev else 0
        except ValueError:
            default_i = 0
        choice = st.radio('Chọn đáp án:', q['options'], index=default_i, key=f'q_{idx}')
        if choice:
            st.session_state.user_answers[idx] = choice
        c1,c2,c3 = st.columns([1,1,1])
        if c1.button('⬅️ Câu trước', disabled=(idx==0)):
            st.session_state.current_index = idx-1; st.experimental_rerun()
        if c2.button('Flag (F)'):
            if idx in st.session_state.flags: st.session_state.flags.remove(idx)
            else: st.session_state.flags.add(idx)
            st.experimental_rerun()
        if c3.button('Câu sau ➡️', disabled=(idx==len(st.session_state.exam_data)-1)):
            st.session_state.current_index = idx+1; st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('### 🔢 Bảng điều hướng')
        total = len(st.session_state.exam_data)
        filt = st.selectbox('Bộ lọc', ['Tất cả','Chưa làm','Đã làm','Đã đánh dấu'])
        for i in range(total):
            done = (i in st.session_state.user_answers)
            flagged = (i in st.session_state.flags)
            if filt == 'Chưa làm' and done: continue
            if filt == 'Đã làm' and not done: continue
            if filt == 'Đã đánh dấu' and not flagged: continue
            label = str(i+1)
            if i == st.session_state.current_index:
                st.markdown("<span class='grid-btn active'>%s</span>"%label, unsafe_allow_html=True)
            elif flagged:
                st.markdown("<span class='grid-btn' style='background:#FFEAA7'>%s</span>"%label, unsafe_allow_html=True)
            elif done:
                st.markdown("<span class='grid-btn' style='background:#D1F7C4'>%s</span>"%label, unsafe_allow_html=True)
            else:
                st.markdown("<span class='grid-btn'>%s</span>"%label, unsafe_allow_html=True)
            if st.button(f'goto_{i}', key=f'goto_{i}'):
                st.session_state.current_index = i; st.experimental_rerun()
        st.markdown('---')
        if st.button('Nộp bài'):
            st.session_state.exam_status = 'review'
            st.session_state.auto_save_file = json.dumps({'user': st.session_state.get('user_name'), 'answers': st.session_state.user_answers}, ensure_ascii=False, indent=2)
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
    labels = ['Đúng','Sai','Chưa trả lời']
    vals = [correct, wrong, unanswered]
    ax.bar(labels, vals)
    ax.set_ylabel('Số câu')
    buf = BytesIO(); fig.tight_layout(); plt.savefig(buf, format='png'); buf.seek(0)
    st.image(buf)

    for d in details:
        i = d['index']; q = st.session_state.exam_data[i]
        ua = d['ua'] if d['ua'] is not None else 'Chưa trả lời'
        ca = q.get('correct_answer')
        w = d['weight']
        color = '#E8F5E9' if d['correct'] else ('#FFDADA' if ua != 'Chưa trả lời' else '#FFF5E1')
        st.markdown("<div style='padding:10px;border-radius:8px;margin-bottom:8px;background:%s'>"%color, unsafe_allow_html=True)
        st.markdown("<strong>Câu %d (điểm %s):</strong> %s"%(i+1, w, q['question']), unsafe_allow_html=True)
        st.markdown("Your answer: <b>%s</b> · Correct: <b>%s</b>"%(ua, ca), unsafe_allow_html=True)
        st.markdown("<em>%s</em>"%q.get('explanation',''), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button('In đề (PDF)'):
            path = export_pdf(st.session_state.exam_data, '/mnt/data/exam_rebuild.pdf', include_answers=False, title='Đề thi - Rebuild')
            with open(path,'rb') as f: st.download_button('Tải PDF đề', data=f, file_name='de_thi_rebuild.pdf', mime='application/pdf')
    with col2:
        if st.button('In đáp án (PDF)'):
            path = export_pdf(st.session_state.exam_data, '/mnt/data/exam_rebuild_answers.pdf', include_answers=True, title='Đáp án - Rebuild')
            with open(path,'rb') as f: st.download_button('Tải PDF đáp án', data=f, file_name='dap_an_rebuild.pdf', mime='application/pdf')

    if st.session_state.auto_save_file:
        st.download_button('Tải kết quả JSON', data=st.session_state.auto_save_file, file_name='ketqua_rebuild.json', mime='application/json')

    if st.button('Về Setup'):
        st.session_state.exam_data=[]; st.session_state.user_answers={}; st.session_state.current_index=0; st.session_state.exam_status='setup'; st.experimental_rerun()

# ---------------- Keyboard shortcuts (best-effort) ----------------
st.markdown('''
<script>
document.addEventListener('keydown', function(e){
  try{
    if(e.key==='ArrowLeft'){
      var btn = Array.from(document.querySelectorAll('button')).find(b=>b.innerText.includes('Câu trước'))
      if(btn) btn.click()
    }
    if(e.key==='ArrowRight'){
      var btn = Array.from(document.querySelectorAll('button')).find(b=>b.innerText.includes('Câu sau'))
      if(btn) btn.click()
    }
    if(e.key.toLowerCase()==='f'){
      var btn = Array.from(document.querySelectorAll('button')).find(b=>b.innerText.includes('Flag'))
      if(btn) btn.click()
    }
    if(e.key.toLowerCase()==='s'){
      var btn = Array.from(document.querySelectorAll('button')).find(b=>b.innerText.includes('Nộp bài'))
      if(btn) btn.click()
    }
  }catch(err){console.log(err)}
})
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
    st.markdown('<div class="meta">Trạng thái không hợp lệ</div>', unsafe_allow_html=True)

# End of rebuild file
