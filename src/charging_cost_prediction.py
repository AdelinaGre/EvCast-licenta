import pandas as pd
import numpy as np
import joblib
import tkinter as tk
from tkinter import messagebox
from sklearn.preprocessing import StandardScaler



model = joblib.load("charging_cost_model.h5")
scaler = joblib.load("scaler.pkl")


features = ["Battery Capacity (kWh)", "Energy Consumed (kWh)", "Charging Duration (hours)",
            "Charging Rate (kW)", "Time of Day", "Day of Week", "State of Charge (Start %)",
            "State of Charge (End %)", "Distance Driven (since last charge) (km)", "Temperature (°C)",
            "Vehicle Age (years)", "Vehicle Model_Chevy Bolt", "Vehicle Model_Hyundai Kona",
            "Vehicle Model_Nissan Leaf", "Vehicle Model_Tesla Model 3",
            "Charging Station Location_Houston", "Charging Station Location_Los Angeles",
            "Charging Station Location_New York", "Charging Station Location_San Francisco",
            "Charger Type_Level 1", "Charger Type_Level 2", "User Type_Commuter", "User Type_Long-Distance Traveler"]

# Funcție pentru estimarea costului
def estimate_cost():
    try:
        input_values = [float(entries[feature].get()) for feature in features]
        input_df = pd.DataFrame([input_values], columns=features)
        input_scaled = scaler.transform(input_df)
        predicted_cost = model.predict(input_scaled)[0]

        result_label.config(text=f"Cost estimat: {round(predicted_cost, 2)} USD")

    except ValueError:
        messagebox.showerror("Eroare", "Introduceți valori numerice valide pentru toate câmpurile!")


root = tk.Tk()
root.title("Estimare Cost Încărcare EV")
canvas = tk.Canvas(root)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar = tk.Scrollbar(root, orient=tk.VERTICAL, command=canvas.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
canvas.configure(yscrollcommand=scrollbar.set)
frame = tk.Frame(canvas)
canvas.create_window((0, 0), window=frame, anchor="nw")

entries = {}
for i, feature in enumerate(features):
    tk.Label(frame, text=feature).grid(row=i, column=0, sticky="w")
    entry = tk.Entry(frame)
    entry.grid(row=i, column=1)
    entries[feature] = entry

submit_button = tk.Button(frame, text="Estimează Costul", command=estimate_cost)
submit_button.grid(row=len(features), column=0, columnspan=2, pady=10)

result_label = tk.Label(frame, text="", font=("Arial", 12, "bold"))
result_label.grid(row=len(features) + 1, column=0, columnspan=2)

frame.update_idletasks()
canvas.config(scrollregion=canvas.bbox("all"))
root.mainloop()
