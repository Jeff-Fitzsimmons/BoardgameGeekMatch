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
                "weight": 11 - rank
            }
    return transformed

###############################################################################
# 2. FLEXIBLE MATCHING LOGIC
###############################################################################

def normalize_title(s: str) -> str:
    """
    Convert to lowercase, remove punctuation, strip extra spaces.
    Example: "Endeavor: Deep Sea" => "endeavor deep sea"
    """
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s)  # remove punctuation
    s = s.strip()
    return s

def partial_match(title_a: str, title_b: str) -> bool:
    """
    Returns True if the normalized strings match by substring inclusion.
    Example:
      partial_match("SETI", "SETI Search...") => True
      partial_match("Endeavor Deep Sea", "Endeavor: Deep Sea") => True
    """
    norm_a = normalize_title(title_a)
    norm_b = normalize_title(title_b)
    return (norm_a in norm_b) or (norm_b in norm_a)

def compare_users(user_dict, other_dict):
    """
    user_dict and other_dict are dicts of form:
      {
        original_title: { "rank": r, "weight": w }
      }
    We do a nested loop to find partial matches, sum dot product of weights.
    Returns:
      - similarity score (int)
      - overlap_details (list of dicts)
    """
    overlap_details = []
    score = 0
    
    for user_game, user_info in user_dict.items():
        for other_game, other_info in other_dict.items():
            if partial_match(user_game, other_game):
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
    new_user_list = [(game, rank), ...] for up to 10 entries.
    We'll build a dict that matches transformed_data's structure, then compare.
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
    
    # sort by descending similarity
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]

###############################################################################
# 3. STREAMLIT APP
###############################################################################

DATA_FILE = "boardgame_data.csv"  # your main dataset
raw_data = load_data(DATA_FILE)
transformed_data = transform_data(raw_data)

# Updated Title
st.title("Geek Match")

st.write("Enter your top 10 board games in order of preference.")
st.write("(1 = most favorite, 10 = tenth favorite)")

user_games_input = []
for i in range(1, 11):
    game_name = st.text_input(f"Enter your number {i} game:", value="", key=f"game_{i}")
    if game_name.strip():
        user_games_input.append((game_name, i))

if st.button("Find Matches"):
    if not user_games_input:
        st.warning("Please enter at least one board game.")
    else:
        # Perform matching
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
