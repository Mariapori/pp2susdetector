import pandas as pd
import random
import os
import string

# VAROITUS: TÄMÄ TIEDOSTO SISÄLTÄÄ VIHAPUHETTA, KIROILUA JA LOUKKAAVAA TEKSTIÄ
# TARKOITUS ON OPEAA TEKOÄLYÄ TUNNISTAMAAN NÄMÄ, JOTTA NE VOIDAAN ESTÄÄ.

def get_leet_char(c):
    leet_map = {
        'a': ['4', '@'],
        'e': ['3'],
        'i': ['1', '!'],
        'o': ['0'],
        's': ['5', '$', 'z'],
        't': ['7', '+'],
        'b': ['8'],
        'g': ['6', '9'],
        'l': ['1', '|'],
        'k': ['|<', 'k'],
        'u': ['v']
    }
    if c.lower() in leet_map and random.random() < 0.5:
        return random.choice(leet_map[c.lower()])
    return c

def augment_text(text, intensity=0.3):
    """
    Applies variations to text: typos, leet speak, repeating characters, case changes.
    intensity: probability of applying a change per character/word
    """
    if random.random() > 0.8: # 20% chance to leave completely clean
        return text
        
    chars = list(text)
    new_chars = []
    
    for c in chars:
        # Randomly apply upper/lower case
        if random.random() < 0.1:
            if c.isupper():
                new_chars.append(c.lower())
            else:
                new_chars.append(c.upper())
            continue
            
        # Leet speak
        if random.random() < intensity:
            new_chars.append(get_leet_char(c))
            continue
            
        # Repetition (e.g. "miiiiitä")
        if c in "aeiouyäö!?" and random.random() < 0.05:
            new_chars.append(c * random.randint(2, 4))
            continue
            
        new_chars.append(c)
        
    result = "".join(new_chars)
    
    # Randomly append punctuation
    if random.random() < 0.3:
        result += random.choice(["!", "!!", "???", "!!!1!", "...", " :D", " :(", " xD"])
        
    return result

def generate_ok_data(count=500):
    data = []
    subjects = ["kuha", "ahven", "hauki", "siika", "made", "taimen", "lohi", "särki", "kiiski", "nieriä"]
    adjectives = ["iso", "pieni", "komea", "hyvä", "kaunis", "mahtava", "kiva", "huono", "hieno"]
    verbs = ["tuli", "nousi", "nappasi", "söi", "karkasi", "nykäisi"]
    places = ["pilkiltä", "järveltä", "jäältä", "syvänteestä", "matalasta", "kivikosta"]
    
    templates = [
        "Sain juuri {adj}n {sub}n.",
        "Onpa {adj} ilma {place}.",
        "Tuleeko muille {sub}a?",
        "Mistä löytyy {adj} {sub}?",
        "{sub} {verb} hyvin täällä.",
        "Olipa {adj} {sub}, joka {verb}!",
        "Kireitä siimoja kaikille.",
        "Moi, onko tässä kisassa sääntöjä?",
        "Tykkään tästä pelistä.",
        "Onko admin paikalla?",
        "Miten vaihdetaan pilkkiä?",
        "Mikä on paras syötti {sub}lle?",
        "Tänään on huono syönti.",
        "Huomenna uusi kisa.",
        "Onnea voittajalle!",
        "Kiitos pelistä.",
        "Nähdään huomenna."
    ]
    
    for _ in range(count):
        tmpl = random.choice(templates)
        msg = tmpl.format(
            sub=random.choice(subjects),
            adj=random.choice(adjectives),
            verb=random.choice(verbs),
            place=random.choice(places)
        )
        # Small chance of typo in OK messages too
        if random.random() < 0.05:
            msg = augment_text(msg, intensity=0.1)
        data.append({"text": msg, "label": "OK"})
        
    # Add nicks
    nicks = ["Kalamies", "PilkkiUkko", "IceFisher", "Sanna88", "Matti_M", "ProPilkkijä", "FishingMaster"]
    for _ in range(int(count/5)):
        nick = random.choice(nicks) + str(random.randint(1, 99))
        data.append({"text": nick, "label": "OK"})
        
    return data

def generate_minor_data(count=500):
    data = []
    complaints = ["lagii", "pätkii", "bugittaa", "ei toimi", "on hidas", "jumittaa", "kaatuu"]
    questions = ["missä admin", "mikä meininki", "miksi tämä ei toimi", "onko täällä ketään", "vastatkaa"]
    boring = ["tylsää", "hiljaista", "huoh", "zzzz", "blaablaa", "väsyttää", "ei jaksa"]
    
    for _ in range(count):
        r = random.random()
        if r < 0.4:
            msg = f"Tämä serveri {random.choice(complaints)}"
        elif r < 0.7:
            msg = random.choice(questions)
        else:
            msg = random.choice(boring)
            
        # Minor violations often have spammy characteristics or caps
        if random.random() < 0.3:
            msg = msg.upper()
        if random.random() < 0.4:
            msg = augment_text(msg, intensity=0.2)
            
        data.append({"text": msg, "label": "MINOR"})
        
    spam_phrases = ["liity tähän", "ilmainen nitro", "klikkaa tästä", "halpaa kultaa", "seuraa minua somessa"]
    for _ in range(int(count/5)):
        msg = random.choice(spam_phrases) + " " + "".join(random.choices(string.ascii_letters, k=5))
        data.append({"text": msg, "label": "MINOR"})

    return data

def generate_moderate_data(count=500):
    data = []
    insults = ["nuija", "idiootti", "tyhmä", "pelle", "luuseri", "urpo", "tonttu", "nolife", "bot", "noob", "jonne"]
    adjectives = ["surkea", "huono", "paska", "oksettava", "ärsyttävä", "ruma", "likainen"]
    targets = ["admin", "peli", "sinä", "kaikki", "serveri", "modet"]
    politics = ["äänestäkää puoluetta", "kommunistit", "persut", "vihreät", "kapitalismi", "sosialismi"]
    religions = ["jumala", "jeesus", "allah", "saatana", "kirkko", "uskonto", "helvetti", "taivas"]
    
    templates = [
        "Sä oot ihan {insult}.",
        "Tämä {target} on {adj}.",
        "Mene pois vitun {insult}.",
        "Haista paska {target}.",
        "{target} on täysi {insult}.",
        "Vittu mitä {adj} touhua.",
        "Painu helvettiin siitä.",
        "Kukaan ei tykkää susta {insult}.",
        "{pol} on paras, muut on {insult}a.",
        "{rel} pelastaa, te olette {adj}a.",
        "Tehkää parannus tai {rel} rankaisee.",
        "Älkää kuunnelko tota {insult}a.",
        "Oletko oikeasti noin {insult}?"
    ]
    
    for _ in range(count):
        tmpl = random.choice(templates)
        msg = tmpl.format(
            insult=random.choice(insults),
            adj=random.choice(adjectives),
            target=random.choice(targets),
            pol=random.choice(politics),
            rel=random.choice(religions)
        )
        
        # Moderate toxicity often involves cursing
        msg = augment_text(msg, intensity=0.3)
        data.append({"text": msg, "label": "MODERATE"})
        
    return data

def generate_severe_data(count=500):
    data = []
    # VERY TOXIC / ILLEGAL / HATE SPEECH / SEXUAL HARASSMENT
    # Keeping these procedural to avoid writing too much specific filth manually,
    # but enough to train the model.
    
    targets = ["neekeri", "ryssä", "huora", "homo", "transu", "jutku", "mamu", "mutakuono", "manne"]
    actions = ["tapan sut", "raiskaan sut", "vedän turpaan", "slit your throat", "kill you", "die", "nussin sua"]
    body_parts = ["pillu", "kyrpä", "perse", "tissit", "muna", "kulli"]
    sexual_acts = ["ime", "nuole", "pane", "runkkaa", "kiksauttaa", "nussia", "naida", "hoidella"]
    
    templates = [
        "Vitun {target}, {action}!",
        "{sexual} mun {part}a saatanan {target}.",
        "Sä oot likainen {target}.",
        "Kuole pois vitun {target}.",
        "Kaikki {target} pitäisi tappaa.",
        "{action} ja koko sun perhe.",
        "Laita kuva sun {part}sta.",
        "Haluan {sexual} sua.",
        "Ootko {target}? Painu vittuun.",
        "Heil Hitler, {target}t uuniin.",
        "White Power, vitun {target}.",
        "{target}t pilaa suomen."
    ]
    
    for _ in range(count):
        tmpl = random.choice(templates)
        msg = tmpl.format(
            target=random.choice(targets),
            action=random.choice(actions),
            part=random.choice(body_parts),
            sexual=random.choice(sexual_acts)
        )
        
        # Severe toxicity often tries to evade filters with heavy Leet Speak
        msg = augment_text(msg, intensity=0.5)
        data.append({"text": msg, "label": "SEVERE"})
        
    return data

def generate_dataset():
    print("Generating comprehensive dataset (10x scale)...")
    
    data = []
    
    # Generate larger base amounts to ensure variety
    print("- Generating OK samples...")
    data.extend(generate_ok_data(30000))
    
    print("- Generating MINOR samples...")
    data.extend(generate_minor_data(30000))
    
    print("- Generating MODERATE samples...")
    data.extend(generate_moderate_data(30000))
    
    print("- Generating SEVERE samples...")
    data.extend(generate_severe_data(30000))
    
    new_df = pd.DataFrame(data)
    
    # Load existing to append if available? 
    # Actually, for "more comprehensive", let's make sure we preserve old reliable data 
    # but the new generator is powerful enough that we might rely on it.
    # Let's keep the append logic but make sure we don't just drown in old data.
    
    os.makedirs("data", exist_ok=True)
    data_file = "data/training_data.csv"
    
    if os.path.exists(data_file):
        try:
            existing_df = pd.read_csv(data_file, on_bad_lines='skip')
            df = pd.concat([existing_df, new_df], ignore_index=True)
            print(f"Merged {len(new_df)} new samples with {len(existing_df)} existing samples.")
        except Exception as e:
            print(f"Could not read existing data: {e}. Starting fresh.")
            df = new_df
    else:
        df = new_df

    # Remove duplicates
    df = df.drop_duplicates(subset=['text', 'label'])
    
    # Balance
    print("Balancing dataset (25% split)...")
    counts = df['label'].value_counts()
    print("Distribution before balancing:")
    print(counts)
    
    target_count = counts.max()
    # Or set a reasonable cap if it gets too huge
    if target_count > 50000:
        target_count = 50000
        
    balanced_dfs = []
    for label in ["OK", "MINOR", "MODERATE", "SEVERE"]:
        label_df = df[df['label'] == label]
        if len(label_df) == 0:
            print(f"Warning: No data for {label}")
            continue
            
        if len(label_df) < target_count:
            resampled = label_df.sample(target_count, replace=True)
        else:
            resampled = label_df.sample(target_count)  # Downsample if above cap
            
        balanced_dfs.append(resampled)
        
    final_df = pd.concat(balanced_dfs).sample(frac=1).reset_index(drop=True)
    
    print("Distribution after balancing:")
    print(final_df['label'].value_counts())
    
    final_df.to_csv(data_file, index=False)
    print(f"Training data saved to {data_file}. Total rows: {len(final_df)}")

if __name__ == "__main__":
    generate_dataset()
