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
# 2. TOKEN-BASED MATCHING LOGIC
#    - Remove punctuation, lowercase, strip out stopwords ("of","the","and")
#    - For single-token titles, require exact match (so "ARKS" != "PARKS")
#    - For multi-token titles, allow subset overlap (e.g. "SETI" matches "SETI Search...")
###############################################################################

STOPWORDS = {"of", "the", "and"}

def normalize_and_tokenize(title: str):
    """
    1) Lowercase
    2) Remove punctuation
    3) Split on whitespace
    4) Remove stopwords
    5) Return list of tokens

    Example:
      "War of the Ring" -> ["war", "ring"]
      "ARKS" -> ["arks"]
      "PARKS" -> ["parks"]
    """
    s = title.lower()
    s = re.sub(r"[^\w\s]", "", s)  # remove punctuation
    tokens = s.split()
    tokens = [t for t in tokens if t not in STOPWORDS]  # remove "of","the","and"
    return tokens

def token_based_match(title_a: str, title_b: str) -> bool:
    """
    1) Convert both titles to tokens.
    2) If both sides end up with exactly one token each, we require EXACT match.
       e.g. "arks" == "arks" -> True, but "arks" != "parks".
    3) Otherwise, we do a "subset" check:
       - If all tokens in A are in B, OR all tokens in B are in A, it's a match.
    """
    tokens_a = normalize_and_tokenize(title_a)
    tokens_b = normalize_and_tokenize(title_b)

    # Special case: both single-token
    if len(tokens_a) == 1 and len(tokens_b) == 1:
        return tokens_a[0] == tokens_b[0]

    # Otherwise, do subset matching:
    # (for partial matching in multi-word titles, e.g. "SETI" -> ["seti"]
    # vs. "seti search for intelligence" -> ["seti", "search", "for", "intelligence"])
    subset_ab = all(t in tokens_b for t in tokens_a)
    subset_ba = all(t in tokens_a for t in tokens_b)
    return subset_ab or subset_ba

def compare_users(user_dict, other_dict):
    """
    Nested loop: for each user_game in user_dict, for each other_game in other_dict,
    check token_based_match. If match, add dot product of weights to 'score'.

    Returns:
      - similarity score (int)
      - overlap_details (list of dicts)
        Each overlap dict: {
            "game_user": str,
            "game_other": str,
            "your_rank": int,
            "their_rank": int
        }
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
    new_user_list = [(game_title, rank), ...] e.g. rank=1..10
    1) Build a dict for the new user
    2) Compare with each person in transformed_data
    3) Sort by descending score; return top N
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
    
    # sort by highest similarity
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]

###############################################################################
# 3. STREAMLIT APP
###############################################################################

DATA_FILE = "boardgame_data.csv"  # Make sure this file is present in the same folder
raw_data = load_data(DATA_FILE)
transformed_data = transform_data(raw_data)

st.title("Geek Match")
st.write("Based on the 2024 dataset compiled by BGG user vitus979 ")

st.write("Enter your **Top 10** board games in order of preference (1 = most favorite).")
st.write("We'll compare them against our dataset of almost 150  board game reviewers' and pundits 'Best of 2024' lists and show your best matches.")

user_games_input = []
for i in range(1, 11):
    game_name = st.text_input(f"Enter your number {i} game:", value="", key=f"game_{i}")
    if game_name.strip():
        user_games_input.append((game_name, i))

if st.button("Find Matches"):
    if not user_games_input:
        st.warning("Please enter at least one board game.")
    else:
        # Compare user input with the dataset
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
