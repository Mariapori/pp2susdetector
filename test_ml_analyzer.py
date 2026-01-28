from ml_analyzer import MLAnalyzer

def test_analyzer():
    try:
        analyzer = MLAnalyzer("models/violation_model.joblib")
        
        test_cases = [
            ("Heikki", "Moi kaikille!", "OK"),
            ("Pekka", "Vitun idiootti!", "SEVERE"),
            ("Jorma", "Sain 50g särjen", "MINOR"),
            ("Putin_is_king", "Lussun lussun", "SEVERE"), # Nickname check
            ("Matti", "Perkule!", "MODERATE")
        ]
        
        print(f"{'Text':<20} | {'Expected':<10} | {'Predicted':<10}")
        print("-" * 45)
        
        for name, text, expected in test_cases:
            if expected == "SEVERE" and "check" in text: # Skip nick check for now or handle it
                pass
            
            # Message check
            res = analyzer.analyze_message(name, text)
            print(f"{text:<20} | {expected:<10} | {res.level:<10}")
            
            # Nickname check
            res_nick = analyzer.analyze_nickname(name)
            if name == "Putin_is_king":
                 print(f"{name:<20} | SEVERE     | {res_nick.level:<10} (NICK)")

    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    test_analyzer()
