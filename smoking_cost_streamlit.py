import streamlit as st
import pandas as pd
import math
import smtplib
from email.message import EmailMessage
from io import BytesIO
from datetime import datetime
import os
import time


# --------------------------
# Helper functions
# --------------------------

def login():
    entered = st.session_state.get("passcode_input", "")
    
    if entered == st.secrets["PASSCODE"]:
        st.session_state.authenticated = True
        success = st.success("✅ Login successful!")
        time.sleep(0.5)
        success.empty()
    else:
        st.error("Incorrect passcode. Try again.")
        time.sleep(0.5)

def get_default_yield(meat_type: str) -> float:
    meat_type = meat_type.lower()
    yield_map = {
        "brisket": 0.6, "pork butt": 0.67, "pork shoulder": 0.67,
        "ribs": 0.65, "beef ribs": 0.6, "pork ribs": 0.65,
        "chicken": 0.78, "turkey": 0.72, "tri-tip": 0.8,
        "sausage": 0.9, "other": 0.7
    }
    return yield_map.get(meat_type, yield_map["other"])

def smoking_cost(
    meat_type, raw_meat_weight_lbs, meat_price_per_lb, serving_size_lbs,
    smoking_hours, pellet_bag_cost, pellet_bag_weight, pellet_usage_per_hour_lb,
    seasoning_cost, misc_cost, markup_multiplier, tax_rate
):
    pellet_price_per_lb = pellet_bag_cost / pellet_bag_weight
    pellet_used_lbs = smoking_hours * pellet_usage_per_hour_lb
    electricity_cost = pellet_used_lbs * 0.25
    pellet_cost = pellet_used_lbs * pellet_price_per_lb + electricity_cost

    cook_yield = get_default_yield(meat_type)
    cooked_meat_lbs = raw_meat_weight_lbs * cook_yield
    servings = cooked_meat_lbs / serving_size_lbs if serving_size_lbs > 0 else 0

    meat_cost = raw_meat_weight_lbs * meat_price_per_lb
    total_cost = meat_cost + pellet_cost + seasoning_cost + misc_cost
    cost_per_serving = total_cost / servings if servings > 0 else 0

    retail_price_per_serving = cost_per_serving * markup_multiplier
    tax_multiplier = 1 + (tax_rate / 100)
    menu_price_pre_round = retail_price_per_serving * tax_multiplier
    menu_price = math.ceil(menu_price_pre_round)

    true_taxable_base = round(menu_price / tax_multiplier, 2)
    true_tax_portion = round(menu_price - true_taxable_base, 2)

    return {
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Meat Type": meat_type.title(),
        "Raw Weight (lbs)": raw_meat_weight_lbs,
        "Cooked Weight (lbs)": round(cooked_meat_lbs, 2),
        "Yield (%)": round(cook_yield * 100, 1),
        "Servings": int(servings),
        "Meat Cost ($)": round(meat_cost, 2),
        "Pellet Used (lbs)": round(pellet_used_lbs, 2),
        "Pellet Cost ($)": round(pellet_cost, 2),
        "Total Cost ($)": round(total_cost, 2),
        "Cost/Serving ($)": round(cost_per_serving, 2),
        "Menu Price/Serving ($)": menu_price,
        "Tax Rate (%)": tax_rate,
        "Tax Portion/Serving ($)": true_tax_portion,
        "Markup Multiplier": markup_multiplier,
    }

def email_csv(df: pd.DataFrame):
    sender_email = st.secrets["SENDEMAIL"]
    sender_password = st.secrets["PASS"]
    recipient_email = st.secrets["RECEIVEEMAIL"]

    if not sender_email or not sender_password or not recipient_email:
        st.error("⚠️ Missing Gmail credentials or recipient in .env file.")
        return

    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    csv_bytes = csv_buffer.getvalue()

    msg = EmailMessage()
    msg["Subject"] = f"Smoke Log - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg.set_content("Attached is your smoke cost and menu price report.")
    msg.add_attachment(csv_bytes, maintype="text", subtype="csv", filename="smoke_log.csv")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
        st.success(f"✅ Email sent to {recipient_email}")
    except Exception as e:
        st.error(f"⚠️ Failed to send email: {e}")

# --------------------------
# Streamlit UI
# --------------------------
st.set_page_config(page_title="Smoker Cost Calculator", page_icon="🔥", layout="centered")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align:center;'>🔒 Login Required</h2>", unsafe_allow_html=True)
    st.text_input(
        "Enter Passcode:",
        type="password",
        key="passcode_input",
        on_change=login,
        placeholder="Enter your passcode",
    )
    st.button("Login", use_container_width=True, on_click=login)
    st.markdown("<br><p style='text-align:center;color:gray;'>Secure access to your smoker cost tool</p>", unsafe_allow_html=True)

else:
    st.markdown("<h2 style='text-align:center;'>🔥 Pellet Smoker Cost & Retail Calculator</h2>", unsafe_allow_html=True)
    st.divider()

    with st.expander("Pellet Info", expanded=True):
        pellet_bag_cost = st.number_input("Pellet Bag Cost ($)", 0.0, 100.0, 20.0)
        pellet_bag_weight = st.number_input("Pellet Bag Weight (lbs)", 1.0, 100.0, 40.0)
        pellet_usage_per_hour_lb = st.number_input("Pellet Usage per Hour (lbs/hour)", 0.1, 5.0, 0.6)
        tax_rate = st.number_input("Sales Tax Rate (%)", 0.0, 25.0, 11.0)

    with st.expander("Meat Details", expanded=True):
        meat_type = st.selectbox("Select Meat Type", ["Brisket", "Pork Butt", "Ribs", "Chicken", "Turkey", "Tri-tip", "Other"])
        raw_meat_weight_lbs = st.number_input("Raw Meat Weight (lbs)", 0.1, 200.0, 10.0)
        meat_price_per_lb = st.number_input("Meat Price per lb ($)", 0.0, 50.0, 3.5)
        serving_size_lbs = st.number_input("Serving Size per Person (lbs)", 0.1, 2.0, 0.5)
        smoking_hours = st.number_input("Smoking Time (hours)", 1.0, 48.0, 8.0)
        seasoning_cost = st.number_input("Seasoning Cost ($)", 0.0, 50.0, 5.0)
        misc_cost = st.number_input("Misc. Cost ($)", 0.0, 50.0, 2.0)
        markup_multiplier = st.number_input("Markup Multiplier", 1.0, 10.0, 2.0, step=0.1)

    if st.button("📧 Calculate & Email Report", use_container_width=True):
        result = smoking_cost(
            meat_type, raw_meat_weight_lbs, meat_price_per_lb, serving_size_lbs,
            smoking_hours, pellet_bag_cost, pellet_bag_weight, pellet_usage_per_hour_lb,
            seasoning_cost, misc_cost, markup_multiplier, tax_rate
        )
        df = pd.DataFrame([result])
        st.dataframe(df, use_container_width=True)
        email_csv(df)

    st.divider()
    st.button("Logout", use_container_width=True, on_click=lambda: st.session_state.update({"authenticated": False}))
