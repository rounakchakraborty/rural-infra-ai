import streamlit as st
from mistralai import Mistral
import json
import re
import os

# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="Rural Infra AI", layout="wide")

# -----------------------------
# Mistral API Setup
# -----------------------------
api_key = os.getenv("MISTRAL_API_KEY")  # ✅ correct way

if not api_key:
    st.warning("⚠️ Add your Mistral API key in Streamlit secrets.")
    st.stop()

client = Mistral(api_key=api_key)

# -----------------------------
# Data
# -----------------------------
DISTRICTS = {
    "Jhansi": {"climate": "low rainfall (~750mm), high solar irradiance"},
    "Gorakhpur": {"climate": "high rainfall (~1800mm), flood-prone"},
    "Meerut": {"climate": "high electricity demand, good solar"},
}

FARMER_ISSUES = [
    "Water availability decreasing",
    "High diesel/electricity cost",
    "Low productivity",
]

MSME_ISSUES = [
    "High electricity bill",
    "Power cuts affecting operations",
]

# -----------------------------
# Helpers
# -----------------------------
def build_financials(profile, acres, monthly_bill):
    if profile == "Farmer":
        return f"""
Farmer with {acres} acres.
Drip cost ₹45k/acre (50% subsidy).
Solar pump net ₹1.28L after subsidy.
"""
    else:
        kw = monthly_bill / 8000
        return f"""
MSME electricity bill ₹{monthly_bill}.
System size ~{kw:.1f} kW.
Solar saves ~₹{round(kw * 12000)} annually.
"""

def build_prompt(district, profile, challenges, acres, monthly_bill):
    info = DISTRICTS[district]
    financials = build_financials(profile, acres, monthly_bill)

    return f"""
You are a rural infrastructure investment advisor in Uttar Pradesh.

District: {district} ({info['climate']})
Profile: {profile}
Challenges: {', '.join(challenges)}

{financials}

CRITICAL:
Return ONLY valid JSON. No text outside JSON.

{{
  "topRecommendation": "string",
  "reasoningBullets": ["string"],
  "risks": ["string"],
  "financialNarrative": "string",
  "districtInsight": "string"
}}
"""

# -----------------------------
# JSON Parser
# -----------------------------
def extract_json_safe(text):
    try:
        return json.loads(text)
    except:
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                return None
        return None

# -----------------------------
# Mistral API Call (FIXED)
# -----------------------------
def run_analysis(prompt):
    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=500
        )

        raw = response.choices[0].message.content
        parsed = extract_json_safe(raw)

        return parsed, raw

    except Exception as e:
        return None, str(e)

# -----------------------------
# UI
# -----------------------------
st.title("🌾 Rural Infrastructure Investment Intelligence")

col1, col2 = st.columns(2)

with col1:
    district = st.selectbox("Select District", list(DISTRICTS.keys()))
    profile = st.selectbox("Profile", ["Farmer", "MSME"])

with col2:
    if profile == "Farmer":
        acres = st.number_input("Land (acres)", 1, 100, 3)
        monthly_bill = 0
        challenges = st.multiselect("Challenges", FARMER_ISSUES)
    else:
        monthly_bill = st.number_input(
            "Monthly Electricity Bill (₹)", 1000, 1000000, 50000
        )
        acres = 0
        challenges = st.multiselect("Challenges", MSME_ISSUES)

st.markdown("---")

if st.button("Run AI Analysis"):

    if not challenges:
        st.warning("Please select at least one challenge.")
    else:
        prompt = build_prompt(
            district, profile, challenges, acres, monthly_bill
        )

        with st.spinner("Running analysis..."):
            result, raw_output = run_analysis(prompt)

        st.success("Analysis Complete")

        if result:
            st.subheader("📍 District Insight")
            st.write(result.get("districtInsight"))

            st.subheader("🎯 Recommendation")
            st.write(result.get("topRecommendation"))

            st.subheader("💰 Financial Narrative")
            st.write(result.get("financialNarrative"))

            st.subheader("✅ Why this fits")
            for r in result.get("reasoningBullets", []):
                st.write("•", r)

            st.subheader("⚠️ Risks")
            for r in result.get("risks", []):
                st.write("•", r)

        else:
            st.warning("⚠️ Could not parse structured output. Showing raw response:")
            st.subheader("📄 AI Response")
            st.write(raw_output)
