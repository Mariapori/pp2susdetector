import pandas as pd
import random
import os

def generate_nsfw_dataset():
    data = []
    
    # Vocabulary for Finnish NSFW/Suggestive content
    body_parts = ["pillu", "kulli", "muna", "perse", "tissi", "pylly", "vittu", "kivekset", "peräreikä", "sääriväli"]
    verbs = ["panna", "naida", "runkkaa", "imeä", "nuolla", "kiksauttaa", "hoidella", "nussia", "kyykkiä"]
    adjectives = ["märkä", "iso", "tiukka", "karvainen", "kiimanen", "huorallinen", "limainen", "kuuma"]
    nouns = ["huora", "lutka", "portto", "runkkari", "nussija", "munanimejä", "pillunpäre", "siitinsankari"]
    
    templates = [
        "haista {v}",
        "ime mun {b}",
        "ootko {adj} {n}",
        "haluisitko {v} mun {b}?",
        "{adj} {b} täällä tarjolla",
        "mun {b} on niin {adj}",
        "painu {v} sen {b}n kanssa",
        "vitun {n}",
        "saatanan {adj} {n}",
        "kuka haluaa {v}?",
        "mennään {v} johonkin",
        "näytä sun {b}",
        "saako sun {b}a {v}?",
        "vittu kun tekee mieli {v}",
        "ootko koskaan {v}massa?"
    ]

    # Generate messages
    for _ in range(2500):
        t = random.choice(templates)
        b = random.choice(body_parts)
        v = random.choice(verbs)
        adj = random.choice(adjectives)
        n = random.choice(nouns)
        
        msg = t.format(b=b, v=v, adj=adj, n=n)
        
        # Randomly apply some variation (leetspeak/typos)
        if random.random() < 0.1:
            msg = msg.replace('u', 'v').replace('i', '1').replace('a', '4')
            
        # Sanitize: remove commas
        msg = msg.replace(",", "")
        data.append({"text": msg, "label": "SEVERE"})

    # Generate nicknames
    for _ in range(1500):
        b = random.choice(body_parts)
        adj = random.choice(adjectives)
        n = random.choice(nouns)
        
        # Nickname formats
        nick_types = [
            f"{adj}_{b}",
            f"{b}_{n}",
            f"{adj}{n}",
            f"{n}{random.randint(69, 99)}",
            f"Iso_{b}",
            f"{b}Master",
            f"Hot_{adj}_{b}",
            f"{n}_Official"
        ]
        
        nick = random.choice(nick_types)
        data.append({"text": nick.replace(",", ""), "label": "SEVERE"})

    # Load existing data to merge and keep balance
    if os.path.exists("data/training_data.csv"):
        try:
            # Use on_bad_lines='skip' to handle corrupted CSV entries
            existing_df = pd.read_csv("data/training_data.csv", on_bad_lines='skip')
            # Filter out any weirdly formatted labels if they slipped through
            valid_labels = ["OK", "MINOR", "MODERATE", "SEVERE"]
            existing_df = existing_df[existing_df['label'].isin(valid_labels)]
            
            other_data = existing_df[existing_df['label'] != 'SEVERE']
            # Balance by adding existing non-severe data 
            for _ in range(3):
                 data.extend(other_data.to_dict('records'))
                 
            # Add existing SEVERE data
            severe_existing = existing_df[existing_df['label'] == 'SEVERE']
            data.extend(severe_existing.to_dict('records'))
        except Exception as e:
            print(f"⚠️ Warning: Could not read existing training data: {e}")

    df = pd.DataFrame(data)
    df = df.sample(frac=1).reset_index(drop=True)
    
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/training_data.csv", index=False)
    print(f"Generated expanded dataset with {len(df)} samples saved to data/training_data.csv")

if __name__ == "__main__":
    generate_nsfw_dataset()
