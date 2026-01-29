# VAROITUS, TÄMÄ SISÄLTÖ ON OPETUSDATAA!!!
# TÄMÄN EI OLE TARKOITUS LOUKATA KETÄÄN

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

    new_df = pd.DataFrame(data)
    data_file = "data/training_data.csv"

    if os.path.exists(data_file):
        try:
            existing_df = pd.read_csv(data_file, on_bad_lines='skip')
            # Merge new data with existing
            df = pd.concat([existing_df, new_df], ignore_index=True)
            print(f"Merged {len(new_df)} new samples with {len(existing_df)} existing samples.")
        except Exception as e:
            print(f"⚠️ Warning: Could not read existing training data: {e}")
            df = new_df
    else:
        df = new_df

    # Remove duplicates - this is CRITICAL to fix previous exponential growth
    initial_count = len(df)
    df = df.drop_duplicates(subset=['text', 'label'])
    removed = initial_count - len(df)
    if removed > 0:
        print(f"🗑️ Removed {removed} duplicate rows.")

    df = df.sample(frac=1).reset_index(drop=True)
    
    os.makedirs("data", exist_ok=True)
    df.to_csv(data_file, index=False)
    print(f"Generated expanded dataset. Total samples: {len(df)} saved to {data_file}")

if __name__ == "__main__":
    generate_nsfw_dataset()
