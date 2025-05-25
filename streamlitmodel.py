import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TensorFlow and other logs
import time
import re
import math
import pandas as pd
import numpy as np
from fractions import Fraction
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


##############################
# Scraping Functions
##############################
def fix_weight(weight_str):
    if "-" in weight_str:
        parts = weight_str.split("-")
        if len(parts) == 2:
            first, second = parts[0].strip(), parts[1].strip()
            month_map = {
                "Jan": "1", "Feb": "2", "Mar": "3", "Apr": "4", "May": "5",
                "Jun": "6", "Jul": "7", "Aug": "8", "Sep": "9", "Oct": "10",
                "Nov": "11", "Dec": "12"
            }
            if second[:3] in month_map:
                try:
                    fixed_first = str(int(first))
                except:
                    fixed_first = first
                fixed_second = month_map[second[:3]]
                return f"{fixed_first}-{fixed_second}"
    return weight_str

def parse_weight_to_lbs(weight_str):
    try:
        stones, pounds = weight_str.split("-")
        return int(stones) * 14 + int(pounds)
    except:
        return np.nan

def fetch_race_card_data(url):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from webdriver_manager.chrome import ChromeDriverManager
    import pandas as pd
    import time
    from datetime import datetime
    import os
    import re

    service = Service(ChromeDriverManager().install(), service_log_path=os.devnull)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    time.sleep(5)

    try:
        time_location_text = driver.find_element(By.CSS_SELECTOR, "p.CourseListingHeader__StyledMainTitle-sc-af53af6-5").text
        race_time, race_location = time_location_text.split()
        race_time = race_time.replace(":", "-")
    except:
        race_time = "Unknown"
        race_location = "Unknown"

    try:
        date_text = driver.find_element(By.CSS_SELECTOR, "p.CourseListingHeader__StyledMainSubTitle-sc-af53af6-7").text
        race_date = datetime.strptime(date_text, "%A %d %B %Y").strftime("%d/%m/%Y")
    except:
        race_date = "Unknown"

    try:
        race_name = driver.find_element(By.CSS_SELECTOR, "h1[data-test-id='racecard-race-name']").text
    except:
        race_name = "Unknown"

    try:
        meta_text = driver.find_element(By.CSS_SELECTOR, "li.RacingRacecardSummary__StyledAdditionalInfo-sc-ff7de2c2-3").text
        parts = [p.strip() for p in meta_text.split("|")]
        distance = next((p for p in parts if "m" in p), "Unknown")
        going = next((p for p in parts if "Good" in p or "Soft" in p or "Firm" in p), "Unknown")
        race_class = next((p for p in parts if "Class" in p or "Group" in p), "Unknown")
        race_type_data = f"{distance} | {going} | {race_class}"
    except:
        race_type_data = "Unknown"

    csv_filename = f"{race_time}_{race_location}.csv" if race_time != "Unknown" and race_location != "Unknown" else "Unknown_Race.csv"
    runners = driver.find_elements(By.CLASS_NAME, "Runner__StyledRunnerContainer-sc-c8a39dcf-0")
    race_data = []

    def safe_find(find_func, by, selector, default="Unknown"):
        try:
            return find_func(by, selector).text
        except:
            return default

    for runner in runners:
        horse_name = safe_find(runner.find_element, By.CSS_SELECTOR, "a[data-test-id='horse-name-link']")
        raw_odds = safe_find(runner.find_element, By.CLASS_NAME, "BetLink__BetLinkStyle-sc-7392938a-0", default="")
        if "Evs" in raw_odds:
            odds = "'1/1"
        elif "/" in raw_odds:
            odds = f"'{raw_odds.strip()}"
        else:
            odds = "'1000/1"

        headgear = safe_find(runner.find_element, By.CSS_SELECTOR, "sup[data-test-id='headgear']", "None")
        last_ran = safe_find(runner.find_element, By.CSS_SELECTOR, "sup[data-test-id='last-ran']", "Unknown")
        saddle_cloth = safe_find(runner.find_element, By.CLASS_NAME, "SaddleAndStall__StyledSaddleClothNo-sc-2df3fa22-1")
        stall_number = safe_find(runner.find_element, By.CLASS_NAME, "SaddleAndStall__StyledStallNo-sc-2df3fa22-2")

        sub_info = runner.find_elements(By.CLASS_NAME, "Runner__StyledSubInfoLink-sc-c8a39dcf-16")
        jockey = sub_info[0].text if len(sub_info) > 0 else "Unknown"
        trainer = sub_info[1].text if len(sub_info) > 1 else "Unknown"

        try:
            horse_info = runner.find_element(By.CLASS_NAME, "Runner__StyledSubInfo-sc-c8a39dcf-4").text
            parts = [p.strip() for p in horse_info.split("|")]
            age = weight = official_rating = "Unknown"
            for part in parts:
                if "Age:" in part:
                    age = part.replace("Age:", "").strip()
                elif "Weight:" in part:
                    weight = part.replace("Weight:", "").strip()
                elif "OR:" in part:
                    official_rating = part.replace("OR:", "").strip()
        except:
            age = weight = official_rating = "Unknown"

        form_string = safe_find(runner.find_element, By.CLASS_NAME, "Runner__StyledFormButton-sc-c8a39dcf-3", "No form available").replace("Form:", "").strip()
        comments = safe_find(runner.find_element, By.CSS_SELECTOR, "div[data-test-id='commentary']", "No comments available")

        try:
            expand_button = runner.find_element(By.CLASS_NAME, "Runner__StyledFormButton-sc-c8a39dcf-3")
            driver.execute_script("arguments[0].click();", expand_button)
            time.sleep(1.2)
        except:
            pass

        past_form_list = []
        try:
            form_table = runner.find_element(By.CSS_SELECTOR, "table[class^='FormTable__']")
            rows = form_table.find_elements(By.TAG_NAME, "tr")[1:]
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 7:
                    date = cols[0].text.strip()
                    course = cols[1].text.strip()
                    race_class = cols[2].text.strip() or "N/A"
                    distance = cols[3].text.strip()
                    going = cols[4].text.strip()
                    orating = cols[5].text.strip()
                    position = cols[6].text.strip()
                    past_form_list.append(
                        f"Date: {date} | Course: {course} | Class: {race_class} | Distance: {distance} | Going: {going} | OR: {orating} | Position: {position}"
                    )
        except:
            pass

        past_race_history = " |||| ".join(past_form_list) if past_form_list else "Unknown"

        race_data.append([
            race_date, race_time.replace("-", ":"), race_location, race_name, race_type_data, horse_name, headgear,
            last_ran, saddle_cloth, stall_number, jockey, trainer, age, weight, official_rating,
            form_string, comments, odds, past_race_history
        ])

    driver.quit()

    columns = [
        "Race Date", "Race Time", "Race Location", "Race Name", "Race Type Data", "Horse Name", "Headgear",
        "Last Ran (Days)", "Saddle Cloth", "Stall", "Jockey", "Trainer", "Age", "Weight", "Official Rating",
        "Recent Form", "Comments", "Odds", "Past Race History"
    ]

    df = pd.DataFrame(race_data, columns=columns)
    df.to_csv(csv_filename, index=False, encoding='utf-8')
    print("=====================================")
    print(f"Race card data successfully saved as '{csv_filename}'.")
    return csv_filename






##############################
# Modelling Helper Functions
##############################
def parse_headgear_factor(headgear, comments):
    if not isinstance(headgear, str):
        return 0.0
    h = headgear.lower().strip()
    if h == "none" or h == "":
        return 0.0
    bonus = 0.0
    if "blinkers" in h:
        bonus += 0.10
    if "visor" in h:
        bonus += 0.05
    if "hood" in h:
        bonus += 0.07
    if bonus == 0.0:
        bonus = 0.03
    comments_lower = comments.lower()
    if "first-time" in comments_lower:
        if "blinkers" in comments_lower and "blinkers" in h:
            bonus += 0.05
        elif "visor" in comments_lower and "visor" in h:
            bonus += 0.03
        elif "hood" in comments_lower and "hood" in h:
            bonus += 0.04
    return bonus

def age_factor(age_str, optimal=7, std=3):
    try:
        age = float(age_str)
        return math.exp(-((age - optimal) ** 2) / (2 * (std ** 2)))
    except:
        return 0.5

def parse_distance(distance_str):
    miles = 0
    furlongs = 0
    yards = 0
    match = re.search(r"(\d+)m", distance_str)
    if match:
        miles = int(match.group(1))
    match = re.search(r"(\d+)f", distance_str)
    if match:
        furlongs = int(match.group(1))
    match = re.search(r"(\d+)y", distance_str)
    if match:
        yards = int(match.group(1))
    total_yards = miles * 1760 + furlongs * 220 + yards
    return total_yards

def get_todays_distance(race_type_data):
    parts = [p.strip() for p in race_type_data.split("|")]
    if len(parts) >= 2:
        distance_str = parts[1]
        return parse_distance(distance_str)
    return None

def get_todays_going(race_type_data):
    parts = [p.strip() for p in race_type_data.split("|")]
    if len(parts) >= 3:
        return parts[2].lower()
    return None

def parse_class_from_race_type(race_type_data):
    match = re.search(r"Class (\d+)", race_type_data)
    if match:
        return int(match.group(1))
    return None

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%y")
    except:
        return None

def last_ran_factor(last_ran_str, distance_yards):
    try:
        last_ran = float(last_ran_str)
    except:
        return 1.0
    if distance_yards <= 0:
        return 1.0
    baseline = 10 * (distance_yards / 5000)
    if last_ran >= baseline:
        return math.exp(-(last_ran - baseline) / baseline)
    else:
        return 1 + ((baseline - last_ran) / baseline) * 0.5

def weight_factor(horse_weight_str, avg_weight):
    weight_lbs = parse_weight_to_lbs(horse_weight_str)
    if weight_lbs and avg_weight > 0:
        return math.pow(avg_weight / weight_lbs, 0.5)
    return 0.5

def recent_form_factor(form_str):
    if not isinstance(form_str, str) or form_str.lower().strip() in ["", "no form available"]:
        return 0.5
    tokens = re.split(r'[\s,-]+', form_str.strip())
    scores = []
    for i, token in enumerate(reversed(tokens)):
        if token.isdigit():
            pos = int(token)
            if pos == 1:
                score = 1.0
            elif pos <= 3:
                score = 0.5
            elif pos <= 8:
                score = 0.25
            else:
                score = -0.5
        elif token.upper() in ["F", "U", "P"]:
            score = -2.0
        else:
            continue
        weight = 1 / (i + 1)
        scores.append(score * weight)
    if scores:
        total_score = sum(scores)
        total_weight = sum(1 / (i + 1) for i in range(len(scores)))
        weighted_avg = total_score / total_weight if total_weight > 0 else 0
        return 1 + 0.2 * weighted_avg
    else:
        return 0.5

def comments_sentiment_factor(comments):
    try:
        from textblob import TextBlob
        blob = TextBlob(comments)
        polarity = blob.sentiment.polarity
        return 1 + polarity
    except ImportError:
        score = simple_sentiment(comments)
        return 1 + 0.1 * score
    except:
        return 1.0

def simple_sentiment(comments):
    if not isinstance(comments, str):
        return 0
    text = comments.lower()
    score = 0
    positive_words = [
        "win", "favour", "good", "strong", "excellent", "headway", "ran on", "stayed on", "kept on", 
        "quickened", "challenge", "led", "cosily", "comfortable", "impressive", "dominant", "fluent", 
        "powerful", "smart", "game", "brave", "battled", "eased", "burst", "cruised", "relished", 
        "promising", "progressed", "nearest finish"
    ]
    negative_words = [
        "loss", "poor", "unlucky", "weak", "weakened", "no impression", "not quite pace", "hung left", 
        "same pace", "regressed", "no extra", "faded", "struggled", "outpaced", "laboured", "tailed off", 
        "never involved", "disappointing", "found little", "flat", "dropped away", "beaten", "hampered", 
        "awkward", "slow"
    ]
    for word in positive_words:
        if word in text:
            score += 1.5
    for word in negative_words:
        if word in text:
            score -= 1.5
    return score

def course_factor(past_history, race_location, race_date):
    if not isinstance(past_history, str) or not past_history.strip():
        return 0.5
    today = parse_date(race_date) or datetime.now()
    races = re.split(r"\|\|\|\|", past_history)
    scores = []
    for race in races:
        date_match = re.search(r"Date:\s*([^|]+)", race)
        course_match = re.search(r"Course:\s*([^|]+)", race)
        pos_match = re.search(r"Position:\s*(\d+)\s*/\s*(\d+)", race)
        if date_match and course_match and pos_match:
            past_date_str = date_match.group(1).strip()
            past_course = course_match.group(1).strip().lower()
            pos = float(pos_match.group(1))
            total = float(pos_match.group(2))
            past_date = parse_date(past_date_str)
            if past_course == race_location.lower() and past_date:
                days_ago = (today - past_date).days
                decay = math.exp(-days_ago / 180)
                if total > 1:
                    score = (1 - (pos - 1) / (total - 1)) * decay
                else:
                    score = (1 if pos == 1 else 0) * decay
                scores.append(score)
    if scores:
        return sum(scores) / len(scores)
    return 0.5

def parse_fractional_odds(odds_str):
    try:
        odds_str = odds_str.strip().strip("'").lower()
        if odds_str in ['evs', 'evens']:
            odds_str = '1/1'
        num, denom = odds_str.split("/")
        return float(num) / float(denom)
    except:
        return np.nan

def parse_fractional_odds_to_decimal(odds_str):
    try:
        odds_str = odds_str.strip().strip("'").lower()
        if odds_str in ['evs', 'evens']:
            odds_str = '1/1'
        num, denom = odds_str.split("/")
        fractional_odds = float(num) / float(denom)
        return fractional_odds + 1  # Convert to decimal odds
    except:
        return np.nan


def parse_past_performance(past_history, race_date):
    if not isinstance(past_history, str) or not past_history.strip():
        return 0.5
    today = parse_date(race_date) or datetime.now()
    races = re.split(r"\|\|\|\|", past_history)
    scores = []
    for race in races:
        date_match = re.search(r"Date:\s*([^|]+)", race)
        pos_match = re.search(r"Position:\s*(\d+)\s*/\s*(\d+)", race)
        if date_match and pos_match:
            past_date_str = date_match.group(1).strip()
            pos = float(pos_match.group(1))
            total = float(pos_match.group(2))
            past_date = parse_date(past_date_str)
            if past_date:
                days_ago = (today - past_date).days
                decay = math.exp(-days_ago / 180)
                if total > 1:
                    score = (1 - (pos - 1) / (total - 1)) * decay
                else:
                    score = (1 if pos == 1 else 0) * decay
                scores.append(score)
    if scores:
        return sum(scores) / len(scores)
    return 0.5

def parse_similar_performance(past_history, todays_course, todays_distance, todays_going, todays_class, race_date):
    if not past_history or not todays_course or not todays_distance or not todays_going or not todays_class:
        return 0.5
    parse_date(race_date)
    races = re.split(r"\|\|\|\|", past_history)
    scores = []
    for race in races:
        date_match = re.search(r"Date:\s*([^|]+)", race)
        course_match = re.search(r"Course:\s*([^|]+)", race)
        distance_match = re.search(r"Distance:\s*([^|]+)", race)
        going_match = re.search(r"Going:\s*([^|]+)", race)
        class_match = re.search(r"Class:\s*(\d+)", race)
        pos_match = re.search(r"Position:\s*(\d+)\s*/\s*(\d+)", race)
        if date_match and course_match and distance_match and going_match and class_match and pos_match:
            past_date_str = date_match.group(1).strip()
            past_course = course_match.group(1).strip().lower()
            past_distance_str = distance_match.group(1).strip()
            past_going = going_match.group(1).strip().lower()
            past_class = int(class_match.group(1))
            pos = float(pos_match.group(1))
            total = float(pos_match.group(2))
            past_date = parse_date(past_date_str)
            past_distance = parse_distance(past_distance_str)
            if past_date and past_course == todays_course.lower() and abs(past_distance - todays_distance) / todays_distance <= 0.1 and past_going == todays_going and past_class == todays_class:
                days_ago = (today - past_date).days
                decay = math.exp(-days_ago / 180)
                if total > 1:
                    score = (1 - (pos - 1) / (total - 1)) * decay
                else:
                    score = (1 if pos == 1 else 0) * decay
                scores.append(score)
    if scores:
        return sum(scores) / len(scores)
    return 0.5

def going_suitability(past_history, todays_going, race_date):
    if not past_history or not todays_going:
        return 0.5
    today = parse_date(race_date) or datetime.now()
    races = re.split(r"\|\|\|\|", past_history)
    scores = []
    for race in races:
        date_match = re.search(r"Date:\s*([^|]+)", race)
        going_match = re.search(r"Going:\s*([^|]+)", race)
        pos_match = re.search(r"Position:\s*(\d+)\s*/\s*(\d+)", race)
        if date_match and going_match and pos_match:
            past_date_str = date_match.group(1).strip()
            past_going = going_match.group(1).strip().lower()
            pos = float(pos_match.group(1))
            total = float(pos_match.group(2))
            past_date = parse_date(past_date_str)
            if past_date and past_going == todays_going:
                days_ago = (today - past_date).days
                decay = math.exp(-days_ago / 180)
                if total > 1:
                    score = (1 - (pos - 1) / (total - 1)) * decay
                else:
                    score = (1 if pos == 1 else 0) * decay
                scores.append(score)
    if scores:
        return sum(scores) / len(scores)
    return 0.5

def distance_suitability(past_history, todays_distance, race_date):
    if not past_history or not todays_distance:
        return 0.5
    today = parse_date(race_date) or datetime.now()
    races = re.split(r"\|\|\|\|", past_history)
    scores = []
    for race in races:
        date_match = re.search(r"Date:\s*([^|]+)", race)
        distance_match = re.search(r"Distance:\s*([^|]+)", race)
        pos_match = re.search(r"Position:\s*(\d+)\s*/\s*(\d+)", race)
        if date_match and distance_match and pos_match:
            past_date_str = date_match.group(1).strip()
            past_distance_str = distance_match.group(1).strip()
            pos = float(pos_match.group(1))
            total = float(pos_match.group(2))
            past_date = parse_date(past_date_str)
            past_distance = parse_distance(past_distance_str)
            if past_date and past_distance and abs(past_distance - todays_distance) / todays_distance <= 0.1:
                days_ago = (today - past_date).days
                decay = math.exp(-days_ago / 180)
                if total > 1:
                    score = (1 - (pos - 1) / (total - 1)) * decay
                else:
                    score = (1 if pos == 1 else 0) * decay
                scores.append(score)
    if scores:
        return sum(scores) / len(scores)
    return 0.5

def jockey_trainer_factor(past_history, race_date):
    if not past_history:
        return 0.5
    today = parse_date(race_date) or datetime.now()
    races = re.split(r"\|\|\|\|", past_history)
    scores = []
    for race in races:
        date_match = re.search(r"Date:\s*([^|]+)", race)
        pos_match = re.search(r"Position:\s*(\d+)\s*/\s*(\d+)", race)
        if date_match and pos_match:
            past_date_str = date_match.group(1).strip()
            pos = float(pos_match.group(1))
            total = float(pos_match.group(2))
            past_date = parse_date(past_date_str)
            if past_date:
                days_ago = (today - past_date).days
                decay = math.exp(-days_ago / 180)
                if total > 1:
                    score = (1 - (pos - 1) / (total - 1)) * decay
                else:
                    score = (1 if pos == 1 else 0) * decay
                scores.append(score)
    if scores:
        return sum(scores) / len(scores)
    return 0.5

def extract_stall(stall_str, total_runners):
    if not isinstance(stall_str, str) or stall_str.strip() == "" or stall_str == "Unknown":
        return 0.5  # Default for missing/invalid stall data
    stall_str = stall_str.strip().lstrip("(").rstrip(")")
    try:
        stall = float(stall_str)
        return 1 - (stall - 1) / (total_runners - 1) if total_runners > 1 else 0.5
    except:
        return 0.5  # Fallback for any parsing errors

def class_factor(past_history, todays_class, race_date):
    if not past_history or not todays_class:
        return 0.5
    today = parse_date(race_date) or datetime.now()
    races = re.split(r"\|\|\|\|", past_history)
    same_class_scores = []
    higher_class_scores = []
    lower_class_scores = []

    for race in races:
        date_match = re.search(r"Date:\s*([^|]+)", race)
        class_match = re.search(r"Class:\s*(\d+)", race)
        pos_match = re.search(r"Position:\s*(\d+)\s*/\s*(\d+)", race)
        if date_match and class_match and pos_match:
            past_date_str = date_match.group(1).strip()
            past_class = int(class_match.group(1))
            pos = float(pos_match.group(1))
            total = float(pos_match.group(2))
            past_date = parse_date(past_date_str)
            if past_date and total > 1:
                days_ago = (today - past_date).days
                decay = math.exp(-days_ago / 180)
                score = (1 - (pos - 1) / (total - 1)) * decay  # Normalized position with recency decay
                if past_class == todays_class:
                    same_class_scores.append(score)
                elif past_class < todays_class:  # Higher class (lower number)
                    higher_class_scores.append(score)
                elif past_class > todays_class:  # Lower class (higher number)
                    lower_class_scores.append(score)

    # Base score: Performance in same class
    base_score = sum(same_class_scores) / len(same_class_scores) if same_class_scores else 0.5

    # Adjustment for class differential
    adjustment = 0
    if higher_class_scores:  # Dropping down in class
        avg_higher = sum(higher_class_scores) / len(higher_class_scores)
        adjustment += 0.5 * avg_higher  # Bonus for proven success in tougher races
    if lower_class_scores:  # Moving up in class
        avg_lower = sum(lower_class_scores) / len(lower_class_scores)
        adjustment -= 0.25 * (1 - avg_lower)  # Penalty if struggled in easier races, reduced if did well

    final_score = base_score + adjustment
    return max(0.0, min(1.0, final_score))  # Clamp between 0 and 1

##############################
# Composite Scoring Function
##############################
def calculate_composite_score(row, weights, field_stats, todays_course, todays_distance, todays_going, todays_class, total_runners):
    odds_fractional = str(row["Odds"]).strip().strip("'")
    odds_numeric = parse_fractional_odds(odds_fractional)
    odds_factor = 1 / odds_numeric if odds_numeric and odds_numeric > 0 else 0
    try:
        official_rating = float(row["Official Rating"])
        official_rating_factor = official_rating / 100
    except:
        official_rating_factor = 0

    past_perf = parse_past_performance(row["Past Race History"], row["Race Date"])
    similar_perf = parse_similar_performance(row["Past Race History"], todays_course, todays_distance, todays_going, todays_class, row["Race Date"])
    stall_factor_val = extract_stall(row["Stall"], total_runners)
    headgear_factor_val = parse_headgear_factor(row["Headgear"], row["Comments"])
    age_factor_val = age_factor(row["Age"], optimal=7, std=3)
    race_distance = field_stats.get("race_distance", 5000)
    last_ran_factor_val = last_ran_factor(row["Last Ran (Days)"], race_distance)
    avg_weight = field_stats.get("avg_weight", 0)
    weight_field_factor_val = weight_factor(row["Weight"], avg_weight)
    recent_form_factor_val = recent_form_factor(row["Recent Form"])
    comments_factor_val = comments_sentiment_factor(row["Comments"])
    course_factor_val = course_factor(row["Past Race History"], row["Race Location"], row["Race Date"])
    going_suit = going_suitability(row["Past Race History"], todays_going, row["Race Date"])
    distance_suit = distance_suitability(row["Past Race History"], todays_distance, row["Race Date"])
    jt_factor = jockey_trainer_factor(row["Past Race History"], row["Race Date"])
    class_factor_val = class_factor(row["Past Race History"], todays_class, row["Race Date"])

    score = (weights["odds"] * odds_factor) + \
            (weights["official_rating"] * official_rating_factor) + \
            (weights["past_performance"] * past_perf) + \
            (weights["similar_conditions"] * similar_perf) + \
            (weights["stall"] * stall_factor_val) + \
            (weights["headgear"] * headgear_factor_val) + \
            (weights["age"] * age_factor_val) + \
            (weights["last_ran"] * last_ran_factor_val) + \
            (weights["weight_field"] * weight_field_factor_val) + \
            (weights["recent_form"] * recent_form_factor_val) + \
            (weights["comments"] * comments_factor_val) + \
            (weights["course"] * course_factor_val) + \
            (weights["going_suitability"] * going_suit) + \
            (weights["distance_suitability"] * distance_suit) + \
            (weights["jockey_trainer"] * jt_factor) + \
            (weights["class"] * class_factor_val)  # New class factor term
    return score

def calculate_predicted_margin(score_prev, score_curr, scale=5.0):
    gap = (score_prev - score_curr) / scale
    rounded = round(gap / 0.25) * 0.25
    if rounded == 0 and (score_prev > score_curr):
        return 0.25
    return rounded

##############################
# Custom Weight Input
##############################
def input_custom_weights():
    default_weights = {
        "odds": 10, "official_rating": 10, "past_performance": 30, "similar_conditions": 40,
        "stall": 5, "headgear": 10, "age": 10, "last_ran": 20, "weight_field": 20,
        "recent_form": 20, "comments": 30, "course": 30, "going_suitability": 50,
        "distance_suitability": 50, "jockey_trainer": 25, "class": 50  # Added class weight
    }
    custom_weights = {}
    for key, default in default_weights.items():
        user_input = input(f"Enter weight for '{key}' (default {default}): ").strip()
        try:
            custom_weights[key] = float(user_input) if user_input else default
        except ValueError:
            print("Invalid input; using default.")
            custom_weights[key] = default
    return custom_weights

##############################
# Additional Helper Functions
##############################
def compute_field_stats(df):
    weights = []
    ages = []
    for idx, row in df.iterrows():
        w = parse_weight_to_lbs(row["Weight"])
        if w and not np.isnan(w):
            weights.append(w)
        try:
            a = float(row["Age"])
            ages.append(a)
        except:
            pass
    avg_weight = sum(weights) / len(weights) if weights else 0
    avg_age = sum(ages) / len(ages) if ages else 0
    race_distance = get_todays_distance(df.iloc[0]["Race Type Data"])
    if race_distance is None or race_distance <= 0:
        race_distance = 5000
    return {"avg_weight": avg_weight, "avg_age": avg_age, "race_distance": race_distance}

def get_race_type(race_name):
    race_name_lower = race_name.lower()
    if "classified" in race_name_lower:
        return "Classified Stakes"
    elif "handicap" in race_name_lower:
        return "Handicap"
    elif "maiden" in race_name_lower:
        return "Maiden"
    else:
        return "Other"

##############################
# Main Modeling Functions
##############################
def model_race(csv_filename, weights):
    import pandas as pd
    from fractions import Fraction
    from streamlitmodel import calculate_composite_score, compute_field_stats, get_todays_distance, get_todays_going, parse_class_from_race_type, parse_fractional_odds_to_decimal

    odds_ladder = [
        '1/1000', '1/500', '1/200', '1/100', '1/66', '1/50', '1/40', '1/33', '1/25', '1/20',
        '1/16', '1/14', '1/12', '1/10', '1/9', '1/8', '1/7', '1/6', '1/5', '2/9',
        '1/4', '2/7', '3/10', '1/3', '4/11', '2/5', '4/9', '1/2', '8/15', '4/7',
        '8/13', '4/6', '8/11', '4/5', '5/6', '10/11', 'Evs', '11/10', '6/5', '5/4',
        '11/8', '7/5', '6/4', '13/8', '15/8', '7/4', '2/1', '9/4', '5/2', '11/4',
        '3/1', '10/3', '7/2', '4/1', '9/2', '5/1', '11/2', '6/1', '13/2', '7/1',
        '15/2', '8/1', '9/1', '10/1', '12/1', '14/1', '16/1', '18/1', '20/1', '25/1',
        '33/1', '40/1', '50/1', '66/1', '100/1', '150/1', '200/1', '250/1', '500/1', '1000/1'
    ]

    def find_closest_odds(prob):
        if prob <= 0:
            return "1000/1"
        def odds_to_fraction(o):
            o = o.lower()
            if o in ['evs', 'evens']:
                o = '1/1'
            try:
                return Fraction(o)
            except:
                return Fraction(1000, 1)
        best_odds = min(odds_ladder, key=lambda o: abs((1 / (odds_to_fraction(o) + 1)) - prob))
        return best_odds

    df = pd.read_csv(csv_filename)
    df.columns = df.columns.str.strip().str.title()

    if "Composite Score" not in df.columns:
        df_sorted = df.copy().reset_index(drop=True)
        total_runners = len(df_sorted)
        todays_course = df_sorted.loc[0, "Race Location"]
        todays_race_type_data = df_sorted.loc[0, "Race Type Data"]
        todays_distance = get_todays_distance(todays_race_type_data)
        todays_going = get_todays_going(todays_race_type_data)
        todays_class = parse_class_from_race_type(todays_race_type_data)
        field_stats = compute_field_stats(df_sorted)

        df_sorted["Composite Score"] = df_sorted.apply(
            lambda row: calculate_composite_score(row, weights, field_stats, todays_course, todays_distance, todays_going, todays_class, total_runners),
            axis=1
        )
    else:
        df_sorted = df.copy().reset_index(drop=True)

    df_sorted = df_sorted.sort_values(by="Composite Score", ascending=False).reset_index(drop=True)
    df_sorted["MV"] = df_sorted["Composite Score"].round(0).astype(int)

    # Setup for odds conversion and calibration
    ladder_decimal = [parse_fractional_odds_to_decimal(odds) for odds in odds_ladder]
    real_odds = df_sorted["Odds"].apply(lambda x: x.strip("'"))
    bookie_probs = [1 / parse_fractional_odds_to_decimal(odd) for odd in real_odds]
    bookie_overround = sum(bookie_probs)

    mv_ranks = df_sorted["Composite Score"].rank(ascending=False, method='min')
    total_horses = len(df_sorted)
    max_steps = 8

    modeled_odds_decimal = []
    modeled_odds_fractional = []
    real_odds_indices = []
    modeled_odds_indices = []
    for idx, row in df_sorted.iterrows():
        real_odd = row["Odds"].strip("'")
        real_odd_decimal = parse_fractional_odds_to_decimal(real_odd)
        closest_idx = min(range(len(ladder_decimal)), key=lambda i: abs(ladder_decimal[i] - real_odd_decimal))
        real_odds_indices.append(closest_idx)

        rank = mv_ranks[idx]
        relative_position = (total_horses - rank + 2) / total_horses
        steps = int(round((relative_position - 0.5) * 2 * max_steps))
        new_idx = closest_idx - steps
        new_idx = max(0, min(len(odds_ladder) - 2, new_idx))

        modeled_odd_decimal = ladder_decimal[new_idx]
        modeled_odd_fractional = odds_ladder[new_idx]
        modeled_odds_decimal.append(modeled_odd_decimal)
        modeled_odds_fractional.append(modeled_odd_fractional)
        modeled_odds_indices.append(new_idx)

    df_sorted["Modelled Odds"] = modeled_odds_decimal
    df_sorted["Modelled Odds Fraction"] = modeled_odds_fractional

    modeled_probs = [1 / odd for odd in modeled_odds_decimal]
    modeled_overround = sum(modeled_probs)
    calibration_factor = bookie_overround / modeled_overround
    calibrated_probs = [prob * calibration_factor for prob in modeled_probs]
    calibrated_modeled_odds = [1 / prob for prob in calibrated_probs]
    df_sorted["Calibrated Modelled Odds"] = calibrated_modeled_odds

    calibrated_fraction_odds = []
    calibrated_fraction_indices = []
    for calibrated_odd in calibrated_modeled_odds:
        closest_idx = min(range(len(ladder_decimal)), key=lambda i: abs(ladder_decimal[i] - calibrated_odd))
        calibrated_fraction_odds.append(odds_ladder[closest_idx])
        calibrated_fraction_indices.append(closest_idx)
    df_sorted["Calibrated Fraction Odds"] = calibrated_fraction_odds

    output_df = df_sorted[["Horse Name", "Odds", "Composite Score"]].copy()
    output_df["Composite Score"] = output_df["Composite Score"].round(0).astype(int)
    output_df = output_df.rename(columns={"Composite Score": "MV"})
    output_df["CFO"] = df_sorted["Calibrated Fraction Odds"]

    def flag_value(row, real_idx, calibrated_idx):
        steps_shortened = real_idx - calibrated_idx
        steps_worsened = calibrated_idx - real_idx
        if steps_shortened >= 4:
            return "💰"
        elif steps_worsened >= 4:
            return "✖️"
        return ""

    output_df["Value"] = [
        flag_value(row, real_odds_indices[i], calibrated_fraction_indices[i])
        for i, row in output_df.iterrows()
    ]

    output_df = output_df[["Horse Name", "Odds", "CFO", "MV", "Value"]]

    # Print results to console
    print("\n=== Modelled Predictions ===")
    print("-" * 62)
    print(f"{'Horse Name':<25} {'Odds':<10} {'CFO':<10} {'MV':<6} {'Value':<6}")
    print("-" * 62)
    for _, row in output_df.iterrows():
        print(f"{row['Horse Name']:<25} {row['Odds']:<10} {row['CFO']:<10} {row['MV']:<6} {row['Value']:<6}")
    print("\n" * 2)
    print(f"Bookmaker Overround: {bookie_overround * 100:.2f}%")
    print(f"Calibrated Modelled Overround: {sum(1 / odd for odd in calibrated_modeled_odds) * 100:.2f}%")
    print("=============================================\n")

    return output_df



##############################
# Main Execution
##############################
if __name__ == "__main__":
    race_urls = []
    print("\n📌 Enter race URLs (one per line). Type 'done' when finished.")
    while True:
        url = input("Enter URL: ").strip()
        if url.lower() == "done":
            break
        elif url.startswith("http"):
            race_urls.append(url)
        else:
            print("Please enter a valid URL or 'done' to finish.")

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

    if race_urls:
        for url in race_urls:
            csv_file = fetch_race_card_data(url)
            if csv_file:
                model_race(csv_file, default_weights)
    else:
        print("No valid URLs were provided.")