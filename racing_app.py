import streamlit as st
from streamlitmodel import fetch_race_card_data, model_race
import pandas as pd

# ✅ Set this as the first Streamlit command
st.set_page_config(page_title="Racing Model App", layout="wide")

# 🎯 Page Title & Instructions
st.title("🏇 Sporting Life Racing Model")
st.markdown("Paste in a racecard URL from [Sporting Life](https://www.sportinglife.com/racing/racecards) and click **Run Model** to generate predictions.")

# 🔗 URL Input
url = st.text_input("Paste Sporting Life Race URL:")

# 🧠 Run Model
if st.button("Run Model"):
    if url.strip() == "":
        st.warning("⚠️ Please enter a race URL first.")
    else:
        with st.spinner("⏳ Fetching race data and running model..."):
            try:
                # 1. Scrape data and save as CSV
                filename = fetch_race_card_data(url)

                # 2. Define model weights (already tuned in your streamlitmodel.py)
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

                # 3. Run the model
                output_df = model_race(filename, default_weights)

                # 4. Display nicely
                st.success("✅ Model completed successfully!")
                st.markdown("### 📊 Model Output")

                # Rename columns for clarity
                output_df.columns = ["Horse", "Bookie Odds", "Modelled Odds", "Model Rating", "Value"]

                # Apply CSS style to center align and control column widths
                st.markdown("""
                    <style>
                    .dataframe th {
                        text-align: center !important;
                    }
                    .dataframe td {
                        text-align: center !important;
                        max-width: 120px !important;
                        white-space: nowrap;
                        overflow: hidden;
                    }
                    </style>
                """, unsafe_allow_html=True)

                # Display the model output
                st.dataframe(output_df, use_container_width=True)

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

