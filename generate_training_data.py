# VAROITUS, TÄMÄ SISÄLTÖ ON OPETUSDATAA!!!
# TÄMÄN EI OLE TARKOITUS LOUKATA KETÄÄN
import pandas as pd
import random
import os

def generate_dataset():
    data = []
    
    # OK - Normal messages (Expanding variety)
    ok_messages = [
        "Moi kaikille!", "Kireitä siimoja!", "Onpa hieno ilma tänään.",
        "Mistä järvestä löytyy parhaiten ahventa?", "Sain juuri 1.2kg hauen!",
        "Kiitti pelistä.", "Tuleeko kenelläkään muulla mitään?", "Tämä on hyvä peli.",
        "Onko admin paikalla?", "Miten tätä pelataan?", "Moi, olen uusi täällä.",
        "Ketä on mukana?", "Pelasin eilenkin.", "Saako täällä jutella?",
        "Kiva järvi.", "Mitä pilkkiä suosittelette?", "Sain ison ahvenen!",
        "Moi taas.", "Onko tässä kisassa sääntöjä?", "Hyvin vedät!",
        "Kiva kala!", "Onko kukaan saanut kuhaa?", "Täällä on hiljaista.",
        "Pilkki vaihtoon.", "Mikä kello on?", "Mennäänkö seuraavalle järvelle?",
        "Hyvää huomenta!", "Hyvää iltaa kaikille.", "Onpa kylmä tuuli.",
        "Sain särjen.", "Ei oikein syö.", "Katsellaanpa tilannetta.",
        "Tsemppiä kisaan!", "Hyvä peli oli!", "Kiitos samoin.",
        "Onko tässä serverissä botteja?", "Miten chatti toimii?",
        "Katsoin ohjeet netistä.", "Pelaan ekaa kertaa.", "Olipa iso kala!"
    ]
    
    ok_nicknames = [
        "-heikki-", "Pekka88", "Kalastaja_99", "Matti_Meikäläinen", "Sanna_S",
        "PilkkiMestari", "AhvenJorma", "KuhaKuningas", "SiikaSirkka", "TalviKala",
        "IceFisher", "NorthernLight", "Snowbound", "Frosty", "ColdWater",
        "Kalamies92", "Pilkki-Pate", "Ahven-Antero", "Siika-Simo", "Made-Matti",
        "Taimen-Timo", "Lohi-Lasse", "Kuha-Kalle", "Särki-Saku", "Kiiski-Kimi"
    ]
    
    # MINOR (Expanding variety)
    minor_violations = [
        "Sain 50g särjen.", "Täällä ei tule mitään.", "Aika tylsää.",
        "Miksi kukaan ei vastaa?", "Ärsyttävää!", "Vähän hidas peli.",
        "Onko täällä ketään?", "Ei täältä tule mitään.", "Miksi mun pilkki ei toimi?",
        "Sain särjen", "Sain kiisken 20g", "Spämmiä1", "Spämmiä2", "Spämmiä3",
        "Blaablaablaa", "Moi moi moi moi moi", "Hohhoijaa", "Tämä kestää",
        "Onpa hidasta", "Miksi peli lagii?", "Lagi", "Lagittaa",
        "Älä spämmi", "Lopeta tuo", "Mitä sä teet?", "Älä tönöä",
        "Aika huono tuuri", "Ei näin", "Vähän tylsää on", "Kuka voittaa?",
        "Onko admin unessa?", "Miksei nää säännöt toimi?", "Huoh", "Zzzzz"
    ]
    
    # MODERATE (Expanding variety)
    moderate_violations = [
        "Voi prkl mitä touhua.", "Vittu kun ei tule kalaa.", "Hitto mikä peli.",
        "Älä nyt viitti.", "Ootpa sä huono.", "Mene pois siitä.",
        "Tämä on mun paikka!", "Jeesus on herra, katukaa syntejänne!",
        "Ääänestäkää Puoluetta X.", "Kaikki kirkkoon sunnuntaina!",
        "Paska peli.", "Saatanan tunarit.", "Perkule", "Helvetti", "Paska",
        "Huono peli", "Voi hitsi", "Älä tuu tähän", "Väistä", "Oot tyhmä",
        "Kunnioita sääntöjä!", "Admin on huono", "Persu", "Vassari",
        "Keskustalainen on rosvo", "Jumala rankaisee", "Usko tai kuole",
        "Lopeta toi perhanan spämmi", "Voi hemmetti sun kanssas",
        "Painu muualle siitä vinkumasta", "Idiootti peli", "Surkea admin",
        "Paskaa tuuria", "Hiton tunari", "Älä valita koko ajan",
        "Kunnioita vähän muita", "Mee töihin", "Sä oot ihan surkee",
        "Lopeta se saarnaaminen", "Ei ketään kiinnosta sun politiikka",
        "Pysy siellä kirkossas", "Älä pakota tota uskontoa"
    ]
    
    moderate_nicknames = [
        "PaskaKala", "HittoVieköön", "Voi_Hemmetti", "[XX]Pelaaja", "[XYZ]Matti",
        "Admin_On_Paska", "Pelimies_Vittu", "Saatanan_Kala", "Perkeleen_Pirkko"
    ]
    
    # SEVERE (Keeping core, but balancing will happen later)
    severe_violations = [
        "Tapa itsesi.", "Vitun huora.", "Ryssät on parhaita, Putin voittaa!",
        "Sota on oikein.", "N***eri mene pois.", "Haista paska vitun idiootti.",
        "Tapan sut jos näen.", "Valkoinen ylivalta.", "Sieg Heil!",
        "Venäjä on paras maa, Ukraina pitää tuhota.",
        "Vittu mitä paskaa", "Haista kukkone", "Saatanan tunari", 
        "Kuole pois", "Painu helvettiin", "Imekää munaa",
        "Rasismi on oikein", "Tapa kaikki", "Verilöyly",
        "Vitun homo", "Vitun neekeri", "Vitun ryssä",
        "Slava Rossiya", "Putin on paras", "Z-kirjain rintaan",
        "Idiootti", "Aivovammainen", "Kehitysvammainen (solvauksena)",
        "Tapan sut", "Vedän turpaan", "Vitun huora", "N-sana", "R-sana"
    ]
    
    severe_nicknames = [
        "Putin_is_king", "Z-Army", "Hitler1488", "Ryssä_Vihaaja", "N-word_Lover",
        "Seksi_Seppo", "Huoran_Poika", "Kullimies", "Pillu_Pekka",
        "NiggerKiller", "Ryssävihan_Luoja", "NaziPlayer"
    ]
    
    # Add to dataset
    for msg in ok_messages: data.append({"text": msg.replace(",", ""), "label": "OK"})
    for nick in ok_nicknames: data.append({"text": nick.replace(",", ""), "label": "OK"})
    for msg in minor_violations: data.append({"text": msg.replace(",", ""), "label": "MINOR"})
    for msg in moderate_violations: data.append({"text": msg.replace(",", ""), "label": "MODERATE"})
    for nick in moderate_nicknames: data.append({"text": nick.replace(",", ""), "label": "MODERATE"})
    for msg in severe_violations: data.append({"text": msg.replace(",", ""), "label": "SEVERE"})
    for nick in severe_nicknames: data.append({"text": nick.replace(",", ""), "label": "SEVERE"})

    new_df = pd.DataFrame(data)
    
    os.makedirs("data", exist_ok=True)
    data_file = "data/training_data.csv"
    
    if os.path.exists(data_file):
        try:
            existing_df = pd.read_csv(data_file, on_bad_lines='skip')
            df = pd.concat([existing_df, new_df], ignore_index=True)
            print(f"Merged new samples with existing samples.")
        except Exception as e:
            print(f"⚠️ Warning: Could not read existing data, starting fresh: {e}")
            df = new_df
    else:
        df = new_df

    # Remove duplicates to avoid bloat
    df = df.drop_duplicates(subset=['text', 'label'])
    
    # --- BALANCING LOGIC (25% each) ---
    print("Balancing dataset to 25% for each category...")
    
    counts = df['label'].value_counts()
    print("Pre-balance distribution:")
    print(counts)
    
    # Target count is the maximum count of any category, or a minimum size
    # In this case, SEVERE is likely much larger. We will resample others to match.
    # To keep it efficient, let's pick a logical target count.
    target_count = counts.max()
    
    balanced_dfs = []
    for label in ["OK", "MINOR", "MODERATE", "SEVERE"]:
        label_df = df[df['label'] == label]
        if len(label_df) == 0:
            continue
            
        if len(label_df) < target_count:
            # Oversample smaller classes
            resampled = label_df.sample(target_count, replace=True)
        else:
            # Undersample larger classes (if we wanted to cap it, but here we just match max)
            resampled = label_df.sample(target_count)
            
        balanced_dfs.append(resampled)
    
    if balanced_dfs:
        df = pd.concat(balanced_dfs).sample(frac=1).reset_index(drop=True)
    
    print("Post-balance distribution:")
    print(df['label'].value_counts())
    
    df.to_csv(data_file, index=False)
    print(f"Dataset updated and balanced. Total samples: {len(df)} saved to {data_file}")

if __name__ == "__main__":
    generate_dataset()

