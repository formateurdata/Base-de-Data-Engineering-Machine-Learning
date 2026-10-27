"""Point d'entrée de la démo.

Usage :
  python run.py train       # entraîne, évalue et déploie si accuracy > 0.70
  python run.py predict     # prédit avec le modèle en production
"""

# mouaad@datagourram.com
import sys

from pipelines import inference_pipeline, training_pipeline

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "train"
    if command == "train":
        training_pipeline()
    elif command == "predict":
        inference_pipeline()
    else:
        sys.exit(f"Commande inconnue : {command} (train ou predict)")
