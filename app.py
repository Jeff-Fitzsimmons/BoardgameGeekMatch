import streamlit as st
import csv
import re

###############################################################################
# 1. LOAD & TRANSFORM DATA
###############################################################################

def load_data(csv_file):
    """
    Reads the CSV and returns a dictionary:
      {
         person_name: [(game1, rank1), (game2, rank2), ...],
         ...
      }
    """
    data = {}
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["name"]
            game = row["board_game"]
            rank = int(row["rank"])
            data.setdefault(name, []).append((game, rank))
    return data

def transform_data(data):
    """
    For each person, store a dict like:
      transformed_data[person][original_game_title] = {
          "rank": rank,
          "weight": 11 - rank
      }
    """
    transformed = {}
    for person, games_ranks in data.items():
        transformed[person] = {}
        for game, rank in games_ranks:
            transformed[person][game] = {
                "rank": rank,
                "weight": 11 - rank  # rank=1 => weight=10, rank=10 => weight=1
            }
    return transformed

###############################################################################
# 2. TOKEN-BASED MATCHING WITH STOPWORDS & NUMBER NORMALIZATION
###############################################################################

STOPWORDS = {"of", "the", "and"}

NUMBER_MAP = {
    "0": "zero",  "zero": "zero",
    "1": "one",   "one": "one",
    "2": "two",   "two": "two",
    "3": "three", "three": "three",
    "4": "four",  "four": "four",
    "5": "five",  "five": "five",
    "6": "six",   "six": "six",
    "7": "seven", "seven": "seven",
    "8": "eight", "eight": "eight",
    "9": "nine",  "nine": "nine",
    "10": "ten",  "ten": "ten",
    "11": "eleven", "eleven": "eleven",
    "12": "twelve", "twelve": "twelve",
    "13": "thirteen", "thirteen": "thirteen",
    "14": "fourteen", "fourteen": "fourteen",
    "15": "fifteen", "fifteen": "fifteen",
    "16": "sixteen", "sixteen": "sixteen",
    "17": "seventeen", "seventeen": "seventeen",
    "18": "eighteen", "eighteen": "eighteen",
    "19": "nineteen", "nineteen": "nineteen",
    "20": "twenty", "twenty": "twenty"
}

def normalize_and_tokenize(title: str):
    """
    1) Lowercase
    2) Remove punctuation
    3) Split on whitespace
    4) Remove stopwords ("of","the","and")
    5) Convert digits/spelled-out numbers => canonical form
    6) Return list of tokens
    """
    s = title.lower()
    s = re.sub(r"[^\w\s]", "", s)  # remove punctuation
    tokens = s.split()
    
    final_tokens = []
    for t in tokens:
        if t in STOPWORDS:
            continue
        if t in NUMBER_MAP:
            t = NUMBER_MAP[t]  # unify numeric/spelled tokens
        final_tokens.append(t)
    
    return final_tokens

def token_based_match(title_a: str, title_b: str) -> bool:
    """
    1) Tokenize both titles
    2) Single-token => exact match
    3) Multi-token => subset check
    """
    tokens_a = normalize_and_tokenize(title_a)
    tokens_b = normalize_and_tokenize(title_b)

    # Single-token exact match
    if len(tokens_a) == 1 and len(tokens_b) == 1:
        return tokens_a[0] == tokens_b[0]

    # Multi-token subset check
    subset_ab = all(t in tokens_b for t in tokens_a)
    subset_ba = all(t in tokens_a for t in tokens_b)
    return subset_ab or subset_ba

###############################################################################
# 3. COMPARISON LOGIC: SYNERGY_BASE=20, NO BONUS AFTER 10 OVERLAPS
###############################################################################

SYNERGY_BASE = 20  # fixed, no user input

def compare_users(user_dict, other_dict):
    """
    For each overlapping game:
      - Dot product: userWeight * otherWeight
      - difference = abs(your_rank - their_rank)
      - synergy = max(0, SYNERGY_BASE - difference)
      - overlap_count => 1..10
        => synergy * overlap_count
      - If overlap_count > 10 => no synergy added.
    """
    overlap_details = []
    score = 0
    overlap_count = 0

    for user_game, user_info in user_dict.items():
        for other_game, other_info in other_dict.items():
            if token_based_match(user_game, other_game):
                # 1) Dot product
                user_weight = user_info["weight"]
                other_weight = other_info["weight"]
                score += user_weight * other_weight

                # 2) Rank-based synergy
                difference = abs(user_info["rank"] - other_info["rank"])
                synergy = max(0, SYNERGY_BASE - difference)

                # 3) Incremental Overlap
                overlap_count += 1
                if overlap_count <= 10:
                    # Add synergy * overlap_count
                    score += synergy * overlap_count
                else:
                    # No synergy if overlap_count > 10
                    pass

                overlap_details.append({
                    "game_user": user_game,
                    "game_other": other_game,
                    "your_rank": user_info["rank"],
                    "their_rank": other_info["rank"]
                })

    return score, overlap_details

def find_top_matches(new_user_list, transformed_data, top_n=20):
    """
    1) Build a dict for the new user
    2) Compare with each person => compare_users
    3) Sort descending
    """
    new_user_dict = {}
    for (game, rank) in new_user_list:
        new_user_dict[game] = {
            "rank": rank,
            "weight": 11 - rank
        }

    results = []
    for person, person_dict in transformed_data.items():
        score, overlap_details = compare_users(new_user_dict, person_dict)
        results.append({
            "person": person,
            "score": score,
            "overlap": overlap_details
        })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]

###############################################################################
# 4. STREAMLIT APP
###############################################################################

DATA_FILE = "boardgame_data.csv"  # or "sample_boardgame_data.csv"
raw_data = load_data(DATA_FILE)
transformed_data = transform_data(raw_data)

st.title("Geek Match")
st.write("Based on the 2024 dataset compiled by BGG user vitus979 ")

st.write("Enter your **Top 10** board games of 2024 in order of preference (1 = most favorite).")
st.write("We'll compare them against our dataset of nearly 150 board game reviewers 'Best of 2024' lists and show the ones that most closely match your tastes.")

user_games_input = []
for i in range(1, 11):
    game_name = st.text_input(f"Enter your number {i} game:", value="", key=f"game_{i}")
    if game_name.strip():
        user_games_input.append((game_name, i))

if st.button("Find Matches"):
    if not user_games_input:
        st.warning("Please enter at least one board game.")
    else:
        # synergy_base=20 is fixed in compare_users, no user input
        top_matches = find_top_matches(user_games_input, transformed_data, top_n=20)
        
        st.subheader("Top 20 Matches")
        for match in top_matches:
            person_name = match["person"]
            score = match["score"]
            overlap = match["overlap"]
            
            st.markdown(f"**{person_name}** — Similarity Score: {score:.2f}")
            
            if overlap:
                with st.expander(f"Show overlapping games with {person_name}"):
                    for item in overlap:
                        st.write(
                            f"- **Your Game**: {item['game_user']} (Rank {item['your_rank']})  \n"
                            f"  **Their Game**: {item['game_other']} (Rank {item['their_rank']})"
                        )
            else:
                st.write("No overlapping games.")
