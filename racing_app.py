import streamlit as st
st.set_page_config(page_title="Racing Model App", layout="wide")  # Must be first

from streamlitmodel import fetch_race_card_data, model_race
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

st.title("🏇 Sporting Life Racing Model")
st.markdown("Paste in a racecard URL from Sporting Life and click **Run Model** to generate predictions.")

# Input field
url = st.text_input("Paste Sporting Life Race URL:")

# Run Model
if st.button("Run Model"):
    if url.strip() == "":
        st.warning("⚠️ Please enter a race URL first.")
    else:
        with st.spinner("⏳ Fetching race data and running model..."):
            try:
                # Fetch data
                filename = fetch_race_card_data(url)

                # Default weights
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

                # Run model
                df = model_race(filename, default_weights)

                # Rename columns
                df = df.rename(columns={
                    "CFO": "Modelled Odds",
                    "MV": "Model Rating"
                })

                st.success("✅ Model completed successfully!")
                st.markdown("### 📊 Model Output")

                # Configure AgGrid
                gb = GridOptionsBuilder.from_dataframe(df)
                gb.configure_columns(
                    ["Odds", "Modelled Odds", "Model Rating", "Value"],
                    cellStyle={"textAlign": "center"},
                    width=100
                )
                gb.configure_column("Horse Name", width=200)
                gb.configure_default_column(resizable=True, filter=True, sortable=True)

                AgGrid(
                    df,
                    gridOptions=gb.build(),
                    fit_columns_on_grid_load=False,
                    theme="material",
                    height=600
                )

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
