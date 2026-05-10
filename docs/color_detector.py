from typing import Dict, Tuple
import math

class ColorDetector:
    """
    Utilitaire pour convertir des valeurs RGB brutes en noms de couleurs.
    Utilise la distance euclidienne dans l'espace RGB pour plus de précision.
    """
    
    # Couleurs de référence calibrées pour le projet
    KNOWN_COLORS = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "white": (250, 250, 250),
        "black": (10, 10, 10)
    }

    @staticmethod
    def identify(r: int, g: int, b: int, sensitivity: int = 150) -> str:
        min_dist = float('inf')
        detected = "unknown"

        for name, target in ColorDetector.KNOWN_COLORS.items():
            # Calcul de la distance 3D entre les couleurs
            dist = math.sqrt((r - target[0])**2 + (g - target[1])**2 + (b - target[2])**2)
            
            if dist < min_dist:
                min_dist = dist
                detected = name

        return detected if min_dist < sensitivity else "unknown"
