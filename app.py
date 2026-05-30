import streamlit as st
import base64
import json
import re
import os
from datetime import datetime
from openai import OpenAI
import random

# ============================================
# 直接在这里填写你的 API Key 和接入点 ID
# ============================================
API_KEY = "ark-e54efdad-caf2-44f7-93ae-44d76ea2de46-06f1f"        # 替换成你的 key，例如 ark-xxxx
MODEL_ID = "ep-20260530232836-ndltt"       # 替换成你的接入点，例如 ep-xxxx
# ============================================

client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=API_KEY,
)

st.set_page_config(page_title="一日三餐日记", page_icon="🍽️")
st.title("🍽️ 一日三餐日记")

DATA_FILE = "meals.json"

def load_meals():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_meals(meals):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(meals, f, ensure_ascii=False, indent=2)

if "meals" not in st.session_state:
    st.session_state.meals = load_meals()
if "pending_meal" not in st.session_state:
    st.session_state.pending_meal = None

def recognize_food(image_bytes):
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = (
        "识别图片中的所有食物，并估算每种食物的热量（单位：千卡）。"
        "只输出JSON数组，不要解释。格式：[{\"name\": \"食物中文名\", \"calories\": 热量数值}]"
    )
    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": prompt}
            ]
        }],
        temperature=0.1,
    )
    content = response.choices[0].message.content.strip()
    if "```" in content:
        content = content.replace("```json", "").replace("```", "").strip()
    try:
        foods = json.loads(content)
    except:
        match = re.search(r'\[.*\]', content, re.DOTALL)
        foods = json.loads(match.group()) if match else []
    result = []
    for item in foods:
        result.append({
            "name": item.get("name", "未知"),
            "calories": float(item.get("calories", 200))
        })
    return result

tab1, tab2 = st.tabs(["📷 拍照识别", "📋 历史记录"])

with tab1:
    uploaded_file = st.camera_input("拍一张食物照片")
    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()
        st.image(image_bytes, caption="你的食物", use_column_width=True)

        if st.button("🔍 开始识别"):
            with st.spinner("正在识别..."):
                try:
                    foods = recognize_food(image_bytes)
                    img_b64_str = base64.b64encode(image_bytes).decode("utf-8")
                    st.session_state.pending_meal = {
                        "foods": foods,
                        "image": img_b64_str,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    total_cal = sum(f["calories"] for f in foods)
                    st.success("识别完成！")
                    for f in foods:
                        st.write(f"**{f['name']}**：{f['calories']} 千卡")
                    st.markdown(f"**总热量：{total_cal} 千卡**")
                except Exception as e:
                    st.error(f"识别失败：{e}")

    if st.session_state.pending_meal is not None:
        st.subheader("给这顿饭打分")
        rating = st.slider("评分", 1, 10, 7)
        comment = st.text_input("备注（可选）")
        if st.button("💾 保存记录"):
            meal = st.session_state.pending_meal.copy()
            meal["rating"] = rating
            meal["comment"] = comment
            st.session_state.meals.append(meal)
            save_meals(st.session_state.meals)
            st.session_state.pending_meal = None
            st.success("已保存！")

with tab2:
    st.subheader("历史记录")
    if st.button("🎲 随机推荐一个高分（≥7）餐食"):
        high_rated = [m for m in st.session_state.meals if m.get("rating", 0) >= 7]
        if high_rated:
            meal = random.choice(high_rated)
            st.write(f"时间：{meal['time']}")
            st.write(f"评分：{meal['rating']}⭐")
            if meal.get('comment'):
                st.write(f"备注：{meal['comment']}")
            st.write("食物：")
            for f in meal['foods']:
                st.write(f"- {f['name']}：{f['calories']}千卡")
            try:
                img_bytes = base64.b64decode(meal['image'])
                st.image(img_bytes, caption="当时照片", use_column_width=True)
            except:
                st.info("图片无法显示")
        else:
            st.info("暂无高分记录")

    st.markdown("---")
    st.write(f"共 {len(st.session_state.meals)} 条记录")
    if st.button("清空所有记录"):
        st.session_state.meals = []
        save_meals([])
        st.success("已清空")
