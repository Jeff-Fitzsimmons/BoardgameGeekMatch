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
# 2. TOKEN-BASED MATCHING + NUMBER NORMALIZATION
###############################################################################

STOPWORDS = {"of", "the", "and"}

# For demonstration, we'll map digits and spelled-out numbers up to 20
# to a canonical word form. You can expand this for higher numbers if needed.
NUMBER_MAP = {
    "0": "zero",    "zero": "zero",
    "1": "one",     "one": "one",
    "2": "two",     "two": "two",
    "3": "three",   "three": "three",
    "4": "four",    "four": "four",
    "5": "five",    "five": "five",
    "6": "six",     "six": "six",
    "7": "seven",   "seven": "seven",
    "8": "eight",   "eight": "eight",
    "9": "nine",    "nine": "nine",
    "10": "ten",    "ten": "ten",
    "11": "eleven", "eleven": "eleven",
    "12": "twelve", "twelve": "twelve",
    "13": "thirteen", "thirteen": "thirteen",
    "14": "fourteen", "fourteen": "fourteen",
    "15": "fifteen",  "fifteen": "fifteen",
    "16": "sixteen",  "sixteen": "sixteen",
    "17": "seventeen","seventeen": "seventeen",
    "18": "eighteen", "eighteen": "eighteen",
    "19": "nineteen", "nineteen": "nineteen",
    "20": "twenty",   "twenty": "twenty"
}

def normalize_and_tokenize(title: str):
    """
    1) Lowercase
    2) Remove punctuation
    3) Split on whitespace
    4) Remove stopwords ("of","the","and")
    5) Convert digits/spelled-out numbers to a canonical form 
       (e.g., "7" -> "seven", "ten" -> "ten")
    6) Return list of tokens
    """
    s = title.lower()
    s = re.sub(r"[^\w\s]", "", s)  # remove punctuation
    tokens = s.split()
    
    filtered_tokens = []
    for t in tokens:
        if t in STOPWORDS:
            # skip if it's a stopword
            continue
        
        # If t is in NUMBER_MAP (digit or spelled-out), unify it
        if t in NUMBER_MAP:
            t = NUMBER_MAP[t]  # e.g. "7" -> "seven"

        filtered_tokens.append(t)

    return filtered_tokens

def token_based_match(title_a: str, title_b: str) -> bool:
    """
    1) Tokenize both titles (lowercase, remove punctuation, unify numbers).
    2) If both are exactly one token each, require exact equality.
    3) Otherwise, do a subset check:
       - all tokens of A in B, or all tokens of B in A
    """
    tokens_a = normalize_and_tokenize(title_a)
    tokens_b = normalize_and_tokenize(title_b)

    # If both sides have exactly one token, require direct match
    if len(tokens_a) == 1 and len(tokens_b) == 1:
        return tokens_a[0] == tokens_b[0]

    # Otherwise, subset logic
    subset_ab = all(t in tokens_b for t in tokens_a)
    subset_ba = all(t in tokens_a for t in tokens_b)
    return subset_ab or subset_ba

def compare_users(user_dict, other_dict):
    """
    For each game in user_dict vs. other_dict, 
    use token_based_match to see if they match.
    Sum up the dot product of matching weights.
    """
    overlap_details = []
    score = 0
    
    for user_game, user_info in user_dict.items():
        for other_game, other_info in other_dict.items():
            if token_based_match(user_game, other_game):
                user_weight = user_info["weight"]
                other_weight = other_info["weight"]
                score += user_weight * other_weight
                
                overlap_details.append({
                    "game_user": user_game,
                    "game_other": other_game,
                    "your_rank": user_info["rank"],
                    "their_rank": other_info["rank"]
                })
    
    return score, overlap_details

def find_top_matches(new_user_list, transformed_data, top_n=20):
    """
    new_user_list = [(game_title, rank), ...]
    Build a dict for the new user, compare with each person, sort by similarity.
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
# 3. STREAMLIT APP
###############################################################################

DATA_FILE = "boardgame_data.csv"  # or "sample_boardgame_data.csv"
raw_data = load_data(DATA_FILE)
transformed_data = transform_data(raw_data)

st.title("Geek Match")
st.write("Based on the 2024 dataset compiled by BGG user vitus979 ")

st.info("Enter your **Top 10** board games in order of preference (1 = most favorite). We'll compare them against our dataset of nearly 150 board game reviewers 'Best of 2024' lists and show the ones that most closely match your tastes.")
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
        top_matches = find_top_matches(user_games_input, transformed_data, top_n=20)
        
        st.subheader("Top 20 Matches")
        for match in top_matches:
            person_name = match["person"]
            score = match["score"]
            overlap = match["overlap"]
            
            st.markdown(f"**{person_name}** — Similarity Score: {score}")
            
            if overlap:
                with st.expander(f"Show overlapping games with {person_name}"):
                    for item in overlap:
                        st.write(
                            f"- **Your Game**: {item['game_user']} (Rank {item['your_rank']})\n"
                            f"  **Their Game**: {item['game_other']} (Rank {item['their_rank']})"
                        )
            else:
                st.write("No overlapping games.")
