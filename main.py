
import streamlit as st
import datetime
import json
import os

# ─────────────────────────────────────────────────────────────
#  DATA LOADING HELPERS
# ─────────────────────────────────────────────────────────────

def load_heartbeat_data(filepath="heartbeat.txt"):
    """
    heartbeat.txt format (space-separated):
        Age(Months) AvgLow AvgHigh
        1 100 160
        12 80 140
        ...
    Returns list of dicts.
    """
    data = []
    with open(filepath, "r") as f:
        lines = f.readlines()
    for line in lines[1:]:  # skip header
        parts = line.strip().split()
        if len(parts) == 3:
            data.append({
                "age_months": int(parts[0]),
                "avg_low": int(parts[1]),
                "avg_high": int(parts[2]),
            })
    return data


def load_bmi_data(filepath="bmi.txt"):
    """
    bmi.txt format:
        Line 1: source URL
        Line 2: BMI 19,20,21,...,54
        Line 3: H(cm) --> Mass (lbs)
        Lines 4+: height_cm, mass_for_bmi19, mass_for_bmi20, ...
    Returns (bmi_values: list[int], rows: list[dict]) where each row has
    'height_cm' and 'masses' (list of masses corresponding to each BMI).
    """
    with open(filepath, "r") as f:
        lines = f.readlines()

    # Line 2 has BMI indices
    bmi_parts = lines[1].strip().split(",")
    # First element is "BMI 19" — extract starting from the label
    bmi_label_and_first = bmi_parts[0].split()
    bmi_values = [int(bmi_label_and_first[-1])] + [int(x) for x in bmi_parts[1:]]

    rows = []
    for line in lines[3:]:  # skip first 3 header lines
        parts = line.strip().split(",")
        if len(parts) > 1:
            height_cm = int(parts[0])
            masses = [int(x) for x in parts[1:]]
            rows.append({"height_cm": height_cm, "masses": masses})

    return bmi_values, rows


def get_heartbeat_range(heartbeat_data, age_months):
    """Return (low, high) heartbeat range for a given age in months."""
    # Find the closest bracket
    best = heartbeat_data[0]
    for entry in heartbeat_data:
        if age_months >= entry["age_months"]:
            best = entry
        else:
            break
    return best["avg_low"], best["avg_high"]


def lookup_bmi(bmi_values, bmi_rows, height_cm, weight_lbs):
    """Find the closest BMI value given height (cm) and weight (lbs)."""
    # Find the closest height row
    closest_row = min(bmi_rows, key=lambda r: abs(r["height_cm"] - height_cm))

    # Find the mass entry closest to the user's weight
    min_diff = float("inf")
    best_bmi = bmi_values[0]
    for i, mass in enumerate(closest_row["masses"]):
        if i < len(bmi_values):
            diff = abs(mass - weight_lbs)
            if diff < min_diff:
                min_diff = diff
                best_bmi = bmi_values[i]

    return best_bmi, closest_row["height_cm"]


def bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight", "⚠️"
    elif bmi < 25:
        return "Normal", "✅"
    elif bmi < 30:
        return "Overweight", "⚠️"
    else:
        return "Obese", "🔴"


# ─────────────────────────────────────────────────────────────
#  IQ TEST QUESTIONS
# ─────────────────────────────────────────────────────────────

IQ_QUESTIONS = [
    {
        "question": "What comes next in the sequence: 2, 6, 12, 20, 30, ?",
        "options": ["40", "42", "38", "44"],
        "answer": "42",
    },
    {
        "question": "Which word does NOT belong: Apple, Banana, Carrot, Grape?",
        "options": ["Apple", "Banana", "Carrot", "Grape"],
        "answer": "Carrot",
    },
    {
        "question": "If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies?",
        "options": ["Yes", "No", "Maybe", "Not enough info"],
        "answer": "Yes",
    },
    {
        "question": "What is the next letter: A, C, F, J, O, ?",
        "options": ["T", "U", "S", "V"],
        "answer": "U",
    },
    {
        "question": "A clock shows 3:15. What is the angle between the hour and minute hands?",
        "options": ["0°", "7.5°", "15°", "22.5°"],
        "answer": "7.5°",
    },
    {
        "question": "Which number is the odd one out: 3, 5, 11, 14, 17, 23?",
        "options": ["3", "14", "17", "23"],
        "answer": "14",
    },
    {
        "question": "If you rearrange 'CIFAIPC', you get the name of a(n):",
        "options": ["City", "Ocean", "Animal", "Country"],
        "answer": "Ocean",
    },
    {
        "question": "What is 15% of 200?",
        "options": ["25", "30", "35", "20"],
        "answer": "30",
    },
    {
        "question": "Complete the analogy: Book is to Reading as Fork is to ?",
        "options": ["Drawing", "Writing", "Eating", "Cooking"],
        "answer": "Eating",
    },
    {
        "question": "How many squares are on a standard chessboard (all sizes)?",
        "options": ["64", "204", "128", "256"],
        "answer": "204",
    },
]


def estimate_iq(score, total):
    """Rough IQ estimate based on percentage correct."""
    pct = score / total
    if pct >= 0.9:
        return 130
    elif pct >= 0.8:
        return 120
    elif pct >= 0.7:
        return 115
    elif pct >= 0.6:
        return 110
    elif pct >= 0.5:
        return 105
    elif pct >= 0.4:
        return 100
    elif pct >= 0.3:
        return 95
    elif pct >= 0.2:
        return 90
    else:
        return 85


# ─────────────────────────────────────────────────────────────
#  SCORE PERSISTENCE
# ─────────────────────────────────────────────────────────────

SCORES_FILE = "saved_scores.txt"


def save_scores(data):
    """Append a result record to saved_scores.txt as JSON lines."""
    with open(SCORES_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")


def load_all_scores():
    """Load all saved score records."""
    records = []
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return records


# ─────────────────────────────────────────────────────────────
#  POWER BI EMBED HELPER
# ─────────────────────────────────────────────────────────────

def render_powerbi_embed(embed_url: str):
    """Render a Power BI report inside Streamlit via iframe."""
    iframe_html = f"""
    <iframe
        width="100%"
        height="600"
        src="{embed_url}"
        frameborder="0"
        allowFullScreen="true"
        style="border:1px solid #ddd; border-radius:8px;">
    </iframe>
    """
    st.components.v1.html(iframe_html, height=620)


# ─────────────────────────────────────────────────────────────
#  STREAMLIT APP
# ─────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="TheScale – Health & IQ Dashboard", layout="wide")

    st.title("⚖️ TheScale")
    st.markdown("**Your personal health metrics and IQ assessment tool**")

    # Sidebar navigation
    page = st.sidebar.radio(
        "Navigate",
        ["🏠 Home", "❤️ Heartbeat Check", "📏 BMI Calculator", "🧠 IQ Test", "📊 Dashboard / Power BI"],
    )

    # ── HOME ──────────────────────────────────────────────────
    if page == "🏠 Home":
        st.header("Welcome to TheScale!")
        st.write(
            "This app lets you check your health metrics and take a quick IQ assessment. "
            "Use the sidebar to navigate between sections."
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("❤️ **Heartbeat Check**\nSee if your resting heart rate is within a healthy range for your age.")
        with col2:
            st.info("📏 **BMI Calculator**\nLook up your BMI using official NIH data tables.")
        with col3:
            st.info("🧠 **IQ Test**\nTake a 10-question reasoning test and get an estimated IQ score.")

    # ── HEARTBEAT ─────────────────────────────────────────────
    elif page == "❤️ Heartbeat Check":
        st.header("❤️ Heartbeat Check")
        st.write("Enter your details below to see if your heart rate is within a healthy range.")

        try:
            hb_data = load_heartbeat_data()
        except FileNotFoundError:
            st.error("⚠️ `heartbeat.txt` not found. Make sure it's in the same directory.")
            return

        name = st.text_input("Your Name")
        age_years = st.number_input("Age (years)", min_value=0, max_value=120, value=25)
        age_months_total = age_years * 12
        heart_rate = st.number_input("Resting Heart Rate (bpm)", min_value=30, max_value=250, value=72)

        if st.button("Check Heartbeat"):
            low, high = get_heartbeat_range(hb_data, age_months_total)
            st.subheader("Results")

            col1, col2, col3 = st.columns(3)
            col1.metric("Your BPM", heart_rate)
            col2.metric("Healthy Low", low)
            col3.metric("Healthy High", high)

            if low <= heart_rate <= high:
                st.success(f"✅ {name or 'Your'} heart rate of {heart_rate} bpm is within the healthy range ({low}–{high} bpm) for your age.")
            elif heart_rate < low:
                st.warning(f"⚠️ {name or 'Your'} heart rate of {heart_rate} bpm is below the typical range ({low}–{high} bpm). Consider consulting a doctor.")
            else:
                st.warning(f"⚠️ {name or 'Your'} heart rate of {heart_rate} bpm is above the typical range ({low}–{high} bpm). Consider consulting a doctor.")

            # Save result
            save_scores({
                "test": "heartbeat",
                "name": name,
                "age_years": age_years,
                "heart_rate": heart_rate,
                "range_low": low,
                "range_high": high,
                "status": "normal" if low <= heart_rate <= high else "abnormal",
                "timestamp": str(datetime.datetime.now()),
            })

    # ── BMI ───────────────────────────────────────────────────
    elif page == "📏 BMI Calculator":
        st.header("📏 BMI Calculator")
        st.write("Uses the NIH BMI reference table to look up your BMI based on height and weight.")

        try:
            bmi_values, bmi_rows = load_bmi_data()
        except FileNotFoundError:
            st.error("⚠️ `bmi.txt` not found. Make sure it's in the same directory.")
            return

        name = st.text_input("Your Name")

        unit = st.radio("Preferred Units", ["Imperial (ft/in, lbs)", "Metric (cm, kg)"])

        if unit == "Imperial (ft/in, lbs)":
            col1, col2 = st.columns(2)
            with col1:
                feet = st.number_input("Height – Feet", min_value=1, max_value=8, value=5)
                inches = st.number_input("Height – Inches", min_value=0, max_value=11, value=8)
            with col2:
                weight_lbs = st.number_input("Weight (lbs)", min_value=50, max_value=700, value=160)
            height_cm = round((feet * 12 + inches) * 2.54)
        else:
            col1, col2 = st.columns(2)
            with col1:
                height_cm = st.number_input("Height (cm)", min_value=100, max_value=250, value=172)
            with col2:
                weight_kg = st.number_input("Weight (kg)", min_value=20, max_value=320, value=72)
            weight_lbs = round(weight_kg * 2.20462)

        if st.button("Calculate BMI"):
            bmi, matched_height = lookup_bmi(bmi_values, bmi_rows, height_cm, weight_lbs)
            category, icon = bmi_category(bmi)

            st.subheader("Results")
            col1, col2, col3 = st.columns(3)
            col1.metric("BMI", bmi)
            col2.metric("Category", f"{icon} {category}")
            col3.metric("Matched Height (cm)", matched_height)

            # Visual gauge
            if bmi < 18.5:
                st.progress(max(0.05, bmi / 50))
            elif bmi < 25:
                st.progress(bmi / 50)
            elif bmi < 30:
                st.progress(bmi / 50)
            else:
                st.progress(min(1.0, bmi / 50))

            st.caption("BMI data sourced from [NIH NHLBI](https://www.nhlbi.nih.gov/sites/default/files/media/docs/bmi_tbl.pdf)")

            save_scores({
                "test": "bmi",
                "name": name,
                "height_cm": height_cm,
                "weight_lbs": weight_lbs,
                "bmi": bmi,
                "category": category,
                "timestamp": str(datetime.datetime.now()),
            })

    # ── IQ TEST ───────────────────────────────────────────────
    elif page == "🧠 IQ Test":
        st.header("🧠 IQ Test")
        st.write("Answer the following 10 questions. Your estimated IQ will be shown at the end.")

        name = st.text_input("Your Name (for the score record)")

        # Use session state to track answers
        if "iq_submitted" not in st.session_state:
            st.session_state.iq_submitted = False

        answers = {}
        with st.form("iq_form"):
            for i, q in enumerate(IQ_QUESTIONS):
                answers[i] = st.radio(
                    f"**Q{i+1}.** {q['question']}",
                    q["options"],
                    key=f"iq_q_{i}",
                )
            submitted = st.form_submit_button("Submit Test")

        if submitted:
            score = 0
            st.subheader("Answer Review")
            for i, q in enumerate(IQ_QUESTIONS):
                correct = q["answer"]
                chosen = answers[i]
                is_correct = chosen == correct
                if is_correct:
                    score += 1
                    st.write(f"✅ **Q{i+1}:** {chosen} — Correct!")
                else:
                    st.write(f"❌ **Q{i+1}:** {chosen} — Incorrect (Answer: {correct})")

            iq = estimate_iq(score, len(IQ_QUESTIONS))
            st.divider()

            col1, col2, col3 = st.columns(3)
            col1.metric("Score", f"{score} / {len(IQ_QUESTIONS)}")
            col2.metric("Percentage", f"{score * 100 // len(IQ_QUESTIONS)}%")
            col3.metric("Estimated IQ", iq)

            if iq >= 120:
                st.success("🎉 Excellent reasoning ability!")
            elif iq >= 105:
                st.info("👍 Above average reasoning ability.")
            elif iq >= 95:
                st.info("👌 Average reasoning ability.")
            else:
                st.info("Keep practicing! Reasoning skills can be improved over time.")

            save_scores({
                "test": "iq",
                "name": name,
                "score": score,
                "total": len(IQ_QUESTIONS),
                "estimated_iq": iq,
                "timestamp": str(datetime.datetime.now()),
            })

    # ── DASHBOARD / POWER BI ──────────────────────────────────
    elif page == "📊 Dashboard / Power BI":
        st.header("📊 Dashboard & Power BI")

        # ── Local Scores Summary ──
        st.subheader("Saved Scores Summary")
        records = load_all_scores()

        if not records:
            st.info("No saved scores yet. Complete a Heartbeat Check, BMI Calculation, or IQ Test first!")
        else:
            # Separate by test type
            hb_records = [r for r in records if r.get("test") == "heartbeat"]
            bmi_records = [r for r in records if r.get("test") == "bmi"]
            iq_records = [r for r in records if r.get("test") == "iq"]

            tab1, tab2, tab3 = st.tabs(["❤️ Heartbeat", "📏 BMI", "🧠 IQ"])

            with tab1:
                if hb_records:
                    st.dataframe(hb_records, use_container_width=True)
                else:
                    st.write("No heartbeat records yet.")

            with tab2:
                if bmi_records:
                    st.dataframe(bmi_records, use_container_width=True)
                    # Simple chart
                    import pandas as pd
                    df = pd.DataFrame(bmi_records)
                    if "bmi" in df.columns and len(df) > 1:
                        st.line_chart(df["bmi"])
                else:
                    st.write("No BMI records yet.")

            with tab3:
                if iq_records:
                    st.dataframe(iq_records, use_container_width=True)
                    import pandas as pd
                    df = pd.DataFrame(iq_records)
                    if "estimated_iq" in df.columns and len(df) > 1:
                        st.bar_chart(df["estimated_iq"])
                else:
                    st.write("No IQ test records yet.")

        # ── Power BI Embed ──
        st.divider()
        st.subheader("📊 Power BI Report")
        st.write(
            "Paste your Power BI **Publish to Web** embed URL below to display your report. "
            "You can get this from Power BI → File → Embed report → Publish to web."
        )

        default_url = ""
        powerbi_url = st.text_input(
            "Power BI Embed URL",
            value=default_url,
            placeholder="https://app.powerbi.com/view?r=...",
        )

        if powerbi_url and "powerbi.com" in powerbi_url:
            render_powerbi_embed(powerbi_url)
        elif powerbi_url:
            st.warning("Please enter a valid Power BI embed URL.")
        else:
            st.info(
                "💡 **Tip:** To connect your data to Power BI:\n"
                "1. Export `saved_scores.txt` (or convert it to CSV/Excel).\n"
                "2. Import it into Power BI Desktop.\n"
                "3. Build your visuals (heart rate trends, BMI distribution, IQ scores).\n"
                "4. Publish to Power BI Service → **Publish to Web** → paste the URL here."
            )

        # ── CSV Export for Power BI ──
        st.divider()
        st.subheader("📤 Export Data for Power BI")
        if records:
            import pandas as pd
            df_all = pd.DataFrame(records)
            csv = df_all.to_csv(index=False)
            st.download_button(
                label="⬇️ Download All Scores as CSV",
                data=csv,
                file_name="thescale_scores.csv",
                mime="text/csv",
            )
        else:
            st.write("No data to export yet.")


if __name__ == "__main__":
    main()