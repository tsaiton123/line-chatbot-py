import cv2
import easyocr
import matplotlib.pyplot as plt
from openai import OpenAI
import os   
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def ocr_translate(image_path, output_dir, key):


    client = OpenAI(api_key=key)


    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


    # Initialize EasyOCR reader
    reader = easyocr.Reader(['en', 'ch_sim'])
    results = reader.readtext(image_rgb)

    # Extract words with bounding boxes
    word_bbox_list = []
    for bbox, text, confidence in results:
        if confidence > 0.1:
            word_bbox_list.append({'text': text, 'bbox': bbox})
            cv2.rectangle(image_rgb, tuple(map(int, bbox[0])), tuple(map(int, bbox[2])), (0, 255, 0), 2)
            # plt.text(bbox[0][0], bbox[0][1] - 10, text, color='red', fontsize=8, backgroundcolor='white')



    # Translate text using OpenAI GPT-4
    for word_info in word_bbox_list:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Translate the following text into Traditional Chinese."},
                {"role": "user", "content": word_info['text']}
            ]
        )
        translation = response.choices[0].message.content
        word_info['translation'] = translation


    # # Output translated words with bbox
    for word_info in word_bbox_list:
        print(f"Original: {word_info['text']} | Translation: {word_info['translation']} | BBox: {word_info['bbox']}")



    # Convert to PIL Image for multilingual support
    image_pil = Image.fromarray(image_rgb)
    draw = ImageDraw.Draw(image_pil)

    font_path = 'NotoSansCJK-Regular.ttc'

    # Example of dynamic font sizing based on bbox height
    for word_info in word_bbox_list:
        bbox = word_info['bbox']
        pts = np.array(bbox, dtype=np.int32)

        bbox_height = np.linalg.norm(pts[0] - pts[3])
        font_size = max(int(bbox_height * 0.8), 12)  # ensure minimum font size is readable

        font = ImageFont.truetype(font_path, font_size)

        # Cover original text with white polygon
        draw.polygon([tuple(pt) for pt in pts], fill='white')

        # Position for translated text
        x, y = pts[0]

        # Overlay translated text
        draw.text((x, y - 5), word_info['translation'], font=font, fill='black')


    # Convert back to OpenCV format and visualize
    final_image = np.array(image_pil)
    output_image_path = f"{output_dir}/transformed.jpg"
    cv2.imwrite(output_image_path, final_image)

    return output_image_path