import joblib
import os
from dataclasses import dataclass
from typing import Literal

ViolationLevel = Literal["SEVERE", "MODERATE", "MINOR", "OK"]

@dataclass
class AnalysisResult:
    """Result of ML analysis"""
    level: ViolationLevel
    reason: str
    suggested_action: str

class MLAnalyzer:
    """Analyzes text using local ML model for PP2 rule violations"""
    
    def __init__(self, model_path: str = "models/violation_model.joblib"):
        """
        Initialize the ML analyzer
        
        Args:
            model_path: Path to the trained joblib model
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}. Run train_model.py first.")
        
        self.model = joblib.load(model_path)
    
    def analyze_message(self, player_name: str, message: str) -> AnalysisResult:
        """
        Analyze a chat message for rule violations
        """
        prediction = self.model.predict([message])[0]
        
        reasons = {
            "SEVERE": "Vakava sääntörikkomus havaittu (esim. vihapuhe tai suora solvaus).",
            "MODERATE": "Keskivakava rikkomus havaittu (esim. kiroilu tai epäkohtelias käytös).",
            "MINOR": "Lievä huomautus sääntöjen noudattamisesta.",
            "OK": "Viesti on asiallinen."
        }
        
        actions = {
            "SEVERE": "/banaddress {ip} 9999999 {full_name}",
            "MODERATE": "/kick {index}",
            "MINOR": "Varoitus",
            "OK": "Ei toimenpiteitä"
        }
        
        return AnalysisResult(
            level=prediction,
            reason=reasons.get(prediction, "Tuntematon rikkomus"),
            suggested_action=actions.get(prediction, "Ei toimenpiteitä")
        )

    def analyze_nickname(self, nickname: str) -> AnalysisResult:
        """
        Analyze a player nickname for rule violations
        """
        prediction = self.model.predict([nickname])[0]
        
        reasons = {
            "SEVERE": "Sopimaton tai sääntöjen vastainen nimimerkki.",
            "MODERATE": "Huomautus nimimerkistä (sisältää mahdollisesti kirosanoja tms).",
            "MINOR": "Nimimerkki saattaa vaatia tarkistusta.",
            "OK": "Nimimerkki on asiallinen."
        }
        
        actions = {
            "SEVERE": "/banaddress {ip} 9999999 {full_name}",
            "MODERATE": "/kick {index}",
            "MINOR": "Varoitus",
            "OK": "Ei toimenpiteitä"
        }
        
        return AnalysisResult(
            level=prediction,
            reason=reasons.get(prediction, "Tuntematon rikkomus"),
            suggested_action=actions.get(prediction, "Ei toimenpiteitä")
        )
