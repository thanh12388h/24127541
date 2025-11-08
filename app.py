# app.py - Streamlit front-end with auth & history
import streamlit as st
import requests
from datetime import date

API_URL = st.secrets.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Trip Planner", layout="wide")
st.title("Trip Planner ✈️ (Login + History)")

# Init session
for key, value in [("token", None), ("user_id", None), ("history", []), ("selected_history", None), ("last_itinerary", None)]:
    st.session_state.setdefault(key, value)

# ---------------- Sidebar (Login - Account - History)
with st.sidebar:
    st.header("🔐 Tài khoản")

    if st.session_state["token"] is None:
        # login
        st.subheader("Đăng nhập")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login ✅"):
            try:
                r = requests.post(f"{API_URL}/login",
                                  json={"email": email, "password": password},
                                  timeout=10)
                r.raise_for_status()
                data = r.json()
                st.session_state["token"] = data["access_token"]
                st.session_state["user_id"] = data["user_id"]
                st.success("Login thành công ✅")
            except Exception as e:
                st.error(f"Login failed ❌: {e}")

        st.markdown("---")

        # register
        st.subheader("Đăng ký tài khoản")
        reg_email = st.text_input("Email đăng ký")
        reg_pass = st.text_input("Password đăng ký", type="password")

        if st.button("Register & Login ✅"):
            try:
                r = requests.post(f"{API_URL}/register",
                                  json={"email": reg_email, "password": reg_pass},
                                  timeout=10)
                r.raise_for_status()
                data = r.json()
                st.session_state["token"] = data["access_token"]
                st.session_state["user_id"] = data["user_id"]
                st.success("Đăng ký + đăng nhập ✅")
            except Exception as e:
                st.error(f"Đăng ký thất bại ❌: {e}")

    else:
        st.success(f"✅ Đã đăng nhập: {st.session_state['user_id']}")
        if st.button("Đăng xuất"):
            st.session_state.update({"token": None, "user_id": None, "history": [], "selected_history": None})
            st.rerun()

        st.markdown("---")

        if st.button("🔄 Tải lịch sử"):
            try:
                headers = {"Authorization": f"Bearer {st.session_state['token']}"}
                r = requests.get(f"{API_URL}/history?limit=50",
                                 headers=headers,
                                 timeout=10)
                r.raise_for_status()
                st.session_state["history"] = r.json().get("history", [])
                st.success("Đã tải lịch sử ✅")
            except Exception as e:
                st.error(f"Lỗi tải lịch sử ❌: {e}")

        # show history list
        hist_titles = [
            f"{item['created_at']} — {item['request'].get('origin')}→{item['request'].get('destination')}"
            for item in st.session_state["history"]
        ]

        selected_idx = st.selectbox("📝 Lịch sử gần đây", options=list(range(len(hist_titles))),
                                    format_func=lambda x: hist_titles[x] if x < len(hist_titles) else "",
                                    index=0 if hist_titles else None)

        if hist_titles:
            st.session_state["selected_history"] = st.session_state["history"][selected_idx]

# ---------------- Main UI (Planner)
st.subheader("🎯 Tạo lịch trình")

origin = st.text_input("Origin city")
destination = st.text_input("Destination city")
dates = st.date_input("Travel dates", value=(date.today(), date.today()))
interests = st.multiselect("Interests", ["Food", "Museums", "Nature", "Nightlife"])
pace = st.radio("Pace", ["relaxed", "normal", "tight"])

if st.button("🧠 Generate itinerary"):
    if st.session_state["token"] is None:
        st.error("❌ Cần đăng nhập trước!")
    elif not origin or not destination or not interests:
        st.error("❌ Hãy điền đầy đủ Origin, Destination và Interests!")
    else:
        # Rewrite dates
        start_date = dates[0].isoformat()
        end_date = dates[1].isoformat()

        payload = {
            "origin": origin,
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "interests": interests,
            "pace": pace
        }
        headers = {"Authorization": f"Bearer {st.session_state['token']}"}

        with st.spinner("⏳ Đang tạo lịch trình..."):
            try:
                r = requests.post(f"{API_URL}/generate",
                                  json=payload, headers=headers, timeout=200)
                r.raise_for_status()
                st.session_state["last_itinerary"] = r.json()
                st.success("✅ Thành công — Lịch trình đã được lưu vào History")

                # refresh history
                st.session_state["history"] = requests.get(
                    f"{API_URL}/history?limit=50",
                    headers=headers).json().get("history", [])

            except Exception as e:
                st.error(f"Server Error ❌: {e}")

# ----------- Show Output (newest or selected history)
st.markdown("---")
st.subheader("📌 Lịch trình hiển thị")

display_data = None

if st.session_state.get("selected_history"):
    display_data = st.session_state["selected_history"]["response"]
elif st.session_state.get("last_itinerary"):
    display_data = st.session_state["last_itinerary"]

if not display_data:
    st.info("Chưa có nội dung. Hãy tạo lịch trình hoặc chọn lịch sử!")
else:
    for day in display_data.get("days", []):
        st.markdown(f"### 📅 {day.get('date', '')}")
        for slot in ["morning", "afternoon", "evening"]:
            s = day.get(slot)
            if s and isinstance(s, dict):
                st.markdown(f"**{slot.capitalize()} — {s.get('title', '')}**")
                st.markdown(f"`{s.get('time', '')}` — {s.get('explain', '')}")
