import base64
import os
import fitz  # PyMuPDF
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

# ================= Configuration =================
PDF_PATH = os.path.join("papers", "argyrodite", "10.1002pssa.201001117.pdf")
OUTPUT_MD_PATH = "parsed_result.md"

# 모델 설정
MODEL_NAME = "qwen3-vl:32b" 
TEMPERATURE = 0.1 

# ================= Helper Functions =================

def pdf_page_to_base64(page):
    """PDF 페이지를 이미지로 변환 후 Base64 인코딩"""
    mat = fitz.Matrix(2.0, 2.0) # 2배 확대 (수식 인식률 향상)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    return base64.b64encode(img_data).decode("utf-8")

def create_prompt(b64_image):
    """
    업데이트된 프롬프트: Figure 무시 + LaTeX 강제
    """
    system_text = (
        "You are an expert research assistant. Your task is to extract text and tables from the provided academic paper page into Markdown. "
        "You must strictly follow formatting rules for math and ignore visual artifacts."
    )

    user_text = (
        "Convert the provided image of a research paper page into Markdown.\n\n"
        "**STRICT GUIDELINES:**\n"
        "1. **Text Content:** Extract all main body text accurately.\n"
        "2. **Tables:** Represent tables using standard Markdown syntax (`| header |...`). Do not skip any numerical data.\n"
        "3. **Math & Chemistry (CRITICAL):** \n"
        "   - Represent ALL mathematical expressions, variables, and chemical formulas using LaTeX.\n"
        "   - Use single dollar signs `$` for inline math (e.g., $Li_6PS_5Cl$, $\sigma = 10^{-3} S/cm$).\n"
        "   - Use double dollar signs `$$` for block equations.\n"
        "   - Never use plain text for chemical formulas (e.g., write $Li_6PS_5Cl$, NOT Li6PS5Cl).\n"
        "4. **Figures & Graphs:** \n"
        "   - **IGNORE** all figures, plots, diagrams, and images.\n"
        "   - **IGNORE** figure captions (text starting with 'Fig.' or 'Figure').\n"
        "   - Do not describe what is in the image.\n"
        "5. **Exclusions:** \n"
        "   - Omit page headers (running titles) and footers (page numbers).\n"
        "   - Omit the 'References' section.\n"
        "6. **Output:** Return ONLY the Markdown content. No conversational filler."
    )

    messages = [
        SystemMessage(content=system_text),
        HumanMessage(
            content=[
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}},
            ]
        )
    ]
    return messages

# ================= Main Execution =================

def main():
    print(f"Loading Model: {MODEL_NAME}...")
    try:
        llm = ChatOllama(
            model=MODEL_NAME,
            temperature=TEMPERATURE,
        )
    except Exception as e:
        print(f"Error initializing model: {e}")
        return

    if not os.path.exists(PDF_PATH):
        print(f"File not found: {PDF_PATH}")
        return

    print(f"Processing PDF: {PDF_PATH}")
    doc = fitz.open(PDF_PATH)
    full_markdown = []

    try:
        for i, page in enumerate(doc):
            page_num = i + 1
            print(f"Parsing Page {page_num}/{len(doc)}...", end=" ", flush=True)

            # 1. 이미지 변환
            b64_img = pdf_page_to_base64(page)

            # 2. 모델 호출
            messages = create_prompt(b64_img)
            response = llm.invoke(messages)
            
            # 3. 결과 저장
            extracted_text = response.content
            full_markdown.append(f"\n\n\n\n")
            full_markdown.append(extracted_text)
            
            print("Done.")

    except KeyboardInterrupt:
        print("\nProcess interrupted.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        doc.close()

    if full_markdown:
        with open(OUTPUT_MD_PATH, "w", encoding="utf-8") as f:
            f.write("".join(full_markdown))
        print(f"\nSaved to: {os.path.abspath(OUTPUT_MD_PATH)}")

if __name__ == "__main__":
    main()