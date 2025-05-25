import streamlit as st
import pandas as pd
from weboutputmodel import fetch_race_card_data, model_race

# Set page title and layout
st.set_page_config(page_title="Racing Model", layout="wide")

# Title of the app
st.title("🏇 Sporting Life Racing Model")

# Prompt for the URL
st.markdown("Enter a Sporting Life Race URL to generate predictions:")

# URL input field
url = st.text_input("Race URL", "")

# Run Model Button
if st.button("Run Model"):
    if url.strip() == "":
        st.warning("⚠️ Please enter a valid race URL first.")
    else:
        with st.spinner("⏳ Running model and fetching data..."):
            try:
                # Fetch the race data (you can modify the fetch function as needed)
                csv_filename = fetch_race_card_data(url)

                # Define model weights (You can adjust the weights as needed)
                weights = {
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

                # Use the model to get predictions
                results_df = model_race(csv_filename, weights)

                # Display the results in a nice table
                st.success("✅ Model completed successfully!")
                st.markdown("### 📊 Model Output")
                st.dataframe(results_df, use_container_width=True)
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
