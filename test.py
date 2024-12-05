import pymupdf
import numpy as np
from PIL import Image

import logging

# 设置全局日志配置
logging.basicConfig(
    level=logging.ERROR,  # 设置日志级别为INFO
    format='%(asctime)s - %(levelname)s - %(message)s',  # 设置日志格式
)

from paddleocr import PaddleOCR
from pdf2zh.doclayout import DocLayoutModel

model = DocLayoutModel.load_available()

file="3433701.3433723.pdf"

def ocrpdf(file):
    ocr = PaddleOCR(use_angle_cls=True, lang="en")
    doc_en=pymupdf.open(file)
    pix = doc_en[0].get_pixmap()
    image = np.fromstring(pix.samples, np.uint8).reshape(
        pix.height, pix.width, 3
    )[:, :, ::-1]
    # image = np.array(Image.open("output_image.png"))
    page_layout = model.predict(image, imgsz=int(pix.height / 32) * 32)[0]
    box = np.ones((pix.height, pix.width))
    h, w = box.shape
    result_text=[]
    vcls = ["abandon", "figure", "table", "isolate_formula", "formula_caption"]
    for i, d in enumerate(page_layout.boxes):
        text=""
        x0, y0, x1, y1 = d.xyxy.squeeze()
        x0, y0, x1, y1 = (
                np.clip(int(x0 - 1), 0, w - 1),
                np.clip(int(h - y1 - 1), 0, h - 1),
                np.clip(int(x1 + 1), 0, w - 1),
                np.clip(int(h - y0 + 1), 0, h - 1),
            )
        if not page_layout.names[int(d.cls)] in vcls:
            box[y0:y1, x0:x1] = i + 2
            if page_layout.names[int(d.cls)]=="plain text":
                imagex = image[y0:y1,x0:x1]
                result = ocr.ocr(imagex, cls=False)
                for idx in range(len(result)):
                    res = result[idx]
                    for line in res:
                        text+=line[1][0]
                result_text.append(translation(text))
        else:
            box[y0:y1, x0:x1] = 0
        
        imagex = image[y0:y1,x0:x1]
        png = Image.fromarray(imagex)
        png.save(f"output_image_{i}_{page_layout.names[int(d.cls)]}.png")
    return result_text

import httpx, json
deeplx_api = "http://127.0.0.1:1188/translate"

def translation(text):
    data = {
        "text": text,
        "source_lang": "EN",
        "target_lang": "ZH"
    }

    post_data = json.dumps(data)
    r = httpx.post(url = deeplx_api, data = post_data).text
    text_zh = json.loads(r)
    return text_zh["alternatives"][0]

for l in ocrpdf(file):
    print(l)
# print(text)