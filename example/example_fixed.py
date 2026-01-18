import fitz
import pymupdf.layout
import pymupdf4llm
import os
import html
import json

input_dir = 'papers/argyrodite'
output_dir = 'comparison_results'
os.makedirs(output_dir, exist_ok=True)

header_height = 80
footer_height = 60
left_margin = 10
right_margin = 10
page_separator = '\n' + '-' * 50 + '\n'

results = []

for filename in os.listdir(input_dir):
    if filename.endswith(".pdf"):
        pdf_path = os.path.join(input_dir, filename)
        
        try:
            doc = fitz.open(pdf_path)
            raw_text = ""
            for page in doc:
                rect = page.rect
                clip = fitz.Rect(
                    rect.x0 + left_margin,
                    rect.y0 + header_height,
                    rect.x1 - right_margin,
                    rect.y1 - footer_height
                )
                raw_text += page.get_text(clip=clip) + page_separator
            doc.close()
            
            llm_text = pymupdf4llm.to_markdown(
                pdf_path,
                show_progress=False,
                header=False,
                footer=False,
                margins=(header_height, right_margin, footer_height, left_margin),
                ignore_graphics=True
            )
            
            results.append({
                "filename": filename,
                "raw": html.escape(raw_text),
                "llm": html.escape(llm_text)
            })
            print(f"처리 완료: {filename}")
            
        except Exception as e:
            print(f"에러 발생 ({filename}): {e}")

print(f"\n총 {len(results)}개 PDF 처리 완료")

html_content = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>PDF Comparison Viewer</title>
<style>
    * {{ box-sizing: border-box; }}
    body {{ 
        font-family: 'Segoe UI', Arial, sans-serif; 
        margin: 0; 
        padding: 0; 
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        min-height: 100vh;
        color: #fff;
    }}
    .header {{
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(10px);
        padding: 15px 30px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        position: sticky;
        top: 0;
        z-index: 100;
    }}
    .title {{ 
        font-size: 18px; 
        font-weight: 600;
        color: #e94560;
    }}
    .nav-controls {{
        display: flex;
        align-items: center;
        gap: 15px;
    }}
    .nav-btn {{
        background: linear-gradient(135deg, #e94560 0%, #0f3460 100%);
        border: none;
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.3s ease;
    }}
    .nav-btn:hover {{
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(233, 69, 96, 0.4);
    }}
    .nav-btn:disabled {{
        opacity: 0.5;
        cursor: not-allowed;
        transform: none;
        box-shadow: none;
    }}
    .file-indicator {{
        font-size: 14px;
        color: rgba(255,255,255,0.7);
    }}
    .file-name {{
        color: #e94560;
        font-weight: 600;
    }}
    .container {{ 
        display: flex; 
        gap: 20px; 
        height: calc(100vh - 70px); 
        padding: 20px;
    }}
    .column {{ 
        flex: 1; 
        background: rgba(255,255,255,0.03);
        backdrop-filter: blur(5px);
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid rgba(255,255,255,0.1);
        overflow-y: auto; 
        white-space: pre-wrap;
    }}
    .column-header {{ 
        position: sticky; 
        top: 0; 
        background: rgba(26, 26, 46, 0.95);
        padding: 12px 0; 
        border-bottom: 2px solid #e94560; 
        margin: -20px -20px 20px -20px;
        padding: 15px 20px;
        font-size: 16px;
        font-weight: 600;
        color: #fff;
    }}
    .raw-text {{ 
        font-family: 'Consolas', 'Courier New', monospace; 
        font-size: 12px; 
        color: #a0a0a0;
        line-height: 1.6;
    }}
    .markdown-text {{ 
        font-family: 'Segoe UI', sans-serif; 
        font-size: 13px; 
        color: #d0d0d0;
        line-height: 1.7;
    }}
    .pdf-content {{ display: none; }}
    .pdf-content.active {{ display: flex; }}
    ::-webkit-scrollbar {{ width: 8px; }}
    ::-webkit-scrollbar-track {{ background: rgba(255,255,255,0.05); border-radius: 4px; }}
    ::-webkit-scrollbar-thumb {{ background: #e94560; border-radius: 4px; }}
</style>
</head>
<body>

<div class="header">
    <div class="title">PDF Comparison Viewer</div>
    <div class="nav-controls">
        <button class="nav-btn" onclick="navigate(-1)" id="prevBtn">◀ Previous</button>
        <span class="file-indicator">
            <span id="currentIndex">1</span> / <span id="totalCount">{total}</span>
            &nbsp;|&nbsp;
            <span class="file-name" id="currentFile"></span>
        </span>
        <button class="nav-btn" onclick="navigate(1)" id="nextBtn">Next ▶</button>
    </div>
</div>

{pdf_sections}

<script>
const data = {json_data};
let currentIndex = 0;

function showPdf(index) {{
    document.querySelectorAll('.pdf-content').forEach((el, i) => {{
        el.classList.toggle('active', i === index);
    }});
    document.getElementById('currentIndex').textContent = index + 1;
    document.getElementById('currentFile').textContent = data[index].filename;
    document.getElementById('prevBtn').disabled = index === 0;
    document.getElementById('nextBtn').disabled = index === data.length - 1;
}}

function navigate(direction) {{
    const newIndex = currentIndex + direction;
    if (newIndex >= 0 && newIndex < data.length) {{
        currentIndex = newIndex;
        showPdf(currentIndex);
    }}
}}

document.addEventListener('keydown', (e) => {{
    if (e.key === 'ArrowLeft') navigate(-1);
    if (e.key === 'ArrowRight') navigate(1);
}});

showPdf(0);
</script>

</body>
</html>
"""

pdf_sections = ""
for i, item in enumerate(results):
    pdf_sections += f"""
<div class="container pdf-content" id="pdf-{i}">
    <div class="column raw-text">
        <div class="column-header">PyMuPDF (Raw Text)</div>
        {item['raw']}
    </div>
    <div class="column markdown-text">
        <div class="column-header">PyMuPDF4LLM (Markdown)</div>
        {item['llm']}
    </div>
</div>
"""

json_data = json.dumps([{"filename": r["filename"]} for r in results], ensure_ascii=False)

final_html = html_content.format(
    total=len(results),
    pdf_sections=pdf_sections,
    json_data=json_data
)

save_path = os.path.join(output_dir, "comparison_viewer.html")
with open(save_path, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"\n생성 완료: {save_path}")
print("좌우 화살표 키로도 네비게이션 가능합니다.")
