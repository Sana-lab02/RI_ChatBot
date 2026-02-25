import numpy as np
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz, process
from bot.bot_utils import clean_text, safe_print
from bot.Keywords import exit_commands, column_aliases


# Creating helper functions
def mask_value_for_debug(user_input):
    s = str(user_input)
    if len(s) <= 4:
        return "*" * len(s)
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


def find_best_troubleshooting_answer(user_input, df_trouble, tfidf_trouble, vectorizer_trouble):
    # match user input to closest troubleshooting question in sheet
    try:
        clean_input = clean_text(user_input)
        user_vec = vectorizer_trouble.transform([clean_input])
        similarities = cosine_similarity(user_vec, tfidf_trouble).flatten()
        best_index = similarities.argmax()
        score = similarities[best_index]
        print(f"Debug.. Troubleshooting best match score: {score:.3f}")
        if score < 0.1:
            return None
        return df_trouble['Answer'].iloc[best_index]
    except Exception as e:
        # safe_print("Error in troubleshooting match", e)
        return None

def find_best_column(user_input, column_aliases, threshold=0.60, ):
    # Find which column best fits for user question
    try:
        # clean user input 
        clean_input = user_input.lower().strip()
        print(f"Debug.. find_best_column input; '{user_input}' - '{clean_input}'")
        print(f"Debug.. find_best_column: '{user_input}, cleaned: '{clean_input}")
        all_aliases = []
        alias_to_col = {}
        for real_col, alias_list in column_aliases.items():
            for alias in alias_list:
                alias_lower = alias.lower()
                all_aliases.append(alias_lower)
                alias_to_col[alias_lower] = real_col

        # TF-IDF cosine similarity
        vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform(all_aliases)            
        user_vec = vectorizer.transform([clean_input])
        cosine_scores = cosine_similarity(user_vec, tfidf_matrix).flatten()
        
        # Fuzzy matching
        fuzzy_scores = [fuzz.partial_ratio(clean_input, alias) / 100 for alias in all_aliases] 

        # combined_scores
        combined_scores = 0.5 * np.array(fuzzy_scores) + 0.5 * np.array(cosine_scores)

        best_index = combined_scores.argmax()
        best_alias = all_aliases[best_index]
        best_score = float(combined_scores[best_index])
        best_col = alias_to_col[best_alias]

        print(f"Debug.. Best column alias: '{best_alias}' - '{best_col}' (score={best_score:.2f})")

        if best_score < threshold:
            return None
        return best_col, best_score
    except Exception as e:
        return None

def find_best_row(user_input, df_customer_info, threshold=60):
    print("USING NEW FIND BEST ROW")
    # indentify the customer mentioned in user input
    try:
        #clean input and remove white space
        cleaned_input = user_input.lower().strip()
        words = cleaned_input.split()
        
        #normailze retailer name
        retailers = (
            df_customer_info['retailer']
            .dropna()
            .astype(str)
            .str.strip()
            .tolist()
        )

        best_score = 0
        best_retailer = None

        for retailer in retailers:
                score = fuzz.partial_ratio(
                    retailer.lower(),
                    cleaned_input
                )
                print(f"Debug... retailer '{retailer}' score: {score}")
                if score > best_score:
                    best_score = score
                    best_retailer = retailer

        if best_score < threshold:
            return None, None, best_score

        row_index = df_customer_info.index[df_customer_info["retailer"].str.strip() == best_retailer][0]
        row_id = int(df_customer_info.loc[row_index, "id"])
        print("Debug.. ", best_retailer, best_score)
        return row_index, best_retailer, best_score

    except Exception as e:
        return None, None, 0
    

def parse_requested_columns(user_input, column_aliases):
    user_input = user_input.lower()
    requested_cols = set()

    if "all" in user_input:
        return list(column_aliases.keys())
    
    for col, aliases in column_aliases.items():
        for alias in aliases:
            if alias.lower() in user_input:
                requested_cols.add(col)
                break
            
    return list(requested_cols)



def chat_bot_start_random():
    return None

def chat_bot_stop_commands(user_input):
    try:

        if str(user_input.lower()) in exit_commands:
            print("Bot: Goodbye!")
            return True
    except Exception as e:
        safe_print("Error processing stop command:", e)
    return False