from ml_analyzer import MLAnalyzer

def test_nsfw_detection():
    try:
        analyzer = MLAnalyzer("models/violation_model.joblib")
        
        test_cases = [
            ("Matti", "Mitä kuuluu?", "OK"),
            ("Pekka", "Ime munaa", "SEVERE"),
            ("Huora88", "Moi", "SEVERE"), # Nickname check
            ("Seksi-Seppo", "Täällä on kuuma", "SEVERE"), # Nickname check
            ("Jorma", "Haluisitko panna mun persettä?", "SEVERE"),
            ("Kalle", "Vittu mitä lutkia", "SEVERE"),
            ("Liisa", "Sulla on tiukka pillu", "SEVERE"),
            ("Admin", "Kaikki hyvin", "OK"),
            ("User123", "v1ttv m1ta 1vskv", "SEVERE") # Leetspeak test
        ]
        
        print(f"{'Source':<15} | {'Input':<30} | {'Expected':<10} | {'Actual':<10}")
        print("-" * 75)
        
        for name, text, expected in test_cases:
            # Check message
            res_msg = analyzer.analyze_message(name, text)
            print(f"{'Message':<15} | {text:<30} | {expected:<10} | {res_msg.level:<10}")
            
            # Check nickname
            res_nick = analyzer.analyze_nickname(name)
            if expected == "SEVERE" and name in ["Huora88", "Seksi-Seppo"]:
                print(f"{'Nickname':<15} | {name:<30} | {expected:<10} | {res_nick.level:<10}")

    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    test_nsfw_detection()
