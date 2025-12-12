
import pickle
from tensorflow.keras.models import load_model

model = load_model("app/models/LST_best_final.keras")

with open("app/models/lst_scalers.pkl", "rb") as f:
    scalers = pickle.load(f)

print(" LST model & scalers loaded!")

def get_scaler(xa):
    return scalers.get(xa)
