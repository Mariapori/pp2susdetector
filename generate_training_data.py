import pandas as pd
import random
import os

def generate_dataset():
    data = []
    
    # OK - Normal messages
    ok_messages = [
        "Moi kaikille!", "Kireitä siimoja!", "Onpa hieno ilma tänään.",
        "Mistä järvestä löytyy parhaiten ahventa?", "Sain juuri 1.2kg hauen!",
        "Kiitti pelistä.", "Tuleeko kenelläkään muulla mitään?", "Tämä on hyvä peli.",
        "Onko admin paikalla?", "Miten tätä pelataan?", "Moi, olen uusi täällä.",
        "Ketä on mukana?", "Pelasin eilenkin.", "Saako täällä jutella?",
        "Kiva järvi.", "Mitä pilkkiä suosittelette?", "Sain ison ahvenen!",
        "Moi taas.", "Onko tässä kisassa sääntöjä?", "Hyvin vedät!"
    ]
    
    ok_nicknames = [
        "-heikki-", "Pekka88", "Kalastaja_99", "Matti_Meikäläinen", "Sanna_S",
        "PilkkiMestari", "AhvenJorma", "KuhaKuningas", "SiikaSirkka", "TalviKala",
        "IceFisher", "NorthernLight", "Snowbound", "Frosty", "ColdWater"
    ]
    
    # MINOR
    minor_violations = [
        "Sain 50g särjen.", "Täällä ei tule mitään.", "Aika tylsää.",
        "Miksi kukaan ei vastaa?", "Ärsyttävää!", "Vähän hidas peli.",
        "Onko täällä ketään?", "Ei täältä tule mitään.", "Miksi mun pilkki ei toimi?",
        "Sain särjen", "Sain kiisken 20g", "Spämmiä1", "Spämmiä2", "Spämmiä3"
    ]
    
    # MODERATE
    moderate_violations = [
        "Voi prkl mitä touhua.", "Vittu kun ei tule kalaa.", "Hitto mikä peli.",
        "Älä nyt viitti.", "Ootpa sä huono.", "Mene pois siitä.",
        "Tämä on mun paikka!", "Jeesus on herra, katukaa syntejänne!",
        "Ääänestäkää Puoluetta X.", "Kaikki kirkkoon sunnuntaina!",
        "Paska peli.", "Saatanan tunarit.", "Perkule", "Helvetti", "Paska",
        "Huono peli", "Voi hitsi", "Älä tuu tähän", "Väistä", "Oot tyhmä",
        "Kunnioita sääntöjä!", "Admin on huono", "Persu", "Vassari",
        "Keskustalainen on rosvo", "Jumala rankaisee", "Usko tai kuole"
    ]
    
    moderate_nicknames = [
        "PaskaKala", "HittoVieköön", "Voi_Hemmetti", "[XX]Pelaaja", "[XYZ]Matti"
    ]
    
    # SEVERE
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
        "Idiootti", "Aivovammainen", "Kehitysvammainen (solvauksena)"
    ]
    
    severe_nicknames = [
        "Putin_is_king", "Z-Army", "Hitler1488", "Ryssä_Vihaaja", "N-word_Lover",
        "Seksi_Seppo", "Huoran_Poika", "Kullimies", "Pillu_Pekka"
    ]
    
    # Add to dataset with some replication to increase size and balance
    for _ in range(5):
        for msg in ok_messages: data.append({"text": msg.replace(",", ""), "label": "OK"})
        for nick in ok_nicknames: data.append({"text": nick.replace(",", ""), "label": "OK"})
        
    for _ in range(10):
        for msg in minor_violations: data.append({"text": msg.replace(",", ""), "label": "MINOR"})
        for msg in moderate_violations: data.append({"text": msg.replace(",", ""), "label": "MODERATE"})
        for nick in moderate_nicknames: data.append({"text": nick.replace(",", ""), "label": "MODERATE"})
        for msg in severe_violations: data.append({"text": msg.replace(",", ""), "label": "SEVERE"})
        for nick in severe_nicknames: data.append({"text": nick.replace(",", ""), "label": "SEVERE"})

    df = pd.DataFrame(data)
    df = df.sample(frac=1).reset_index(drop=True)
    
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/training_data.csv", index=False)
    print(f"Generated dataset with {len(df)} samples saved to data/training_data.csv")

if __name__ == "__main__":
    generate_dataset()
