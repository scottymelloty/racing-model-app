import streamlit as st
from streamlitmodel import fetch_race_card_data, model_race
import pandas as pd

# ✅ MUST be the first Streamlit command
st.set_page_config(page_title="Racing Model App", layout="wide")

st.title("🏇 Sporting Life Racing Model")
st.markdown("Paste in a racecard URL from Sporting Life and click **Run Model** to generate predictions.")

# 🌐 User input
url = st.text_input("Paste Sporting Life Race URL:")

# ▶️ Run Model Button
if st.button("Run Model"):
    if url.strip() == "":
        st.warning("⚠️ Please enter a race URL first.")
    else:
        with st.spinner("⏳ Fetching race data and running model..."):
            try:
                # 🐎 Step 1: Scrape & Save Race CSV
                filename = fetch_race_card_data(url)

                # ⚙️ Step 2: Define default model weights
                default_weights = {
                    "odds": 40,
                    "official_rating": 10,
                    "past_performance": 45,
                    "similar_conditions": 50,
                    "stall": 5,
                    "headgear": 5,
                    "age": 5,
                    "last_ran": 40,
                    "weight_field": 20,
                    "recent_form": 20,
                    "comments": 10,
                    "course": 20,
                    "going_suitability": 20,
                    "distance_suitability": 20,
                    "jockey_trainer": 20,
                    "class": 20
                }

                # 🧠 Step 3: Run the model
                output_df = model_race(filename, default_weights)

                # 🎉 Step 4: Show Results
                st.success("✅ Model completed successfully!")
                st.markdown("### 📊 Model Output")

                # Rename columns to be clearer for the user
                display_df = output_df.rename(columns={
                    "Odds": "Bookie Odds",
                    "CFO": "Modelled Odds",
                    "MV": "Model Rating"
                })

                # Show output nicely
                st.dataframe(display_df.style.set_properties(
                    **{
                        'text-align': 'center',
                        'font-size': '14px'
                    }
                ), use_container_width=True)

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

