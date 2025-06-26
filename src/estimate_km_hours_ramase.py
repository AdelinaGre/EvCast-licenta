import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
import tkinter as tk
from tkinter import ttk
import joblib
import numpy as np


model_km = tf.keras.models.load_model("modele/seq_layers_km_model.h5", custom_objects={'mse': tf.keras.losses.MeanSquaredError()})
model_hours = tf.keras.models.load_model("modele/seq_layers_hours_model.h5", custom_objects={'mse': tf.keras.losses.MeanSquaredError()})
scaler_km_hours = joblib.load("modele/scaler_km_h.pkl")

def prepare_features_from_user_input(user_input):
    energy = user_input.get("Energy Consumed (kWh)", 20)
    rate = user_input["Charging Rate (kW)"]
    soc_start = user_input["State of Charge (Start %)"]
    soc_end = user_input["State of Charge (End %)"]
    dist = user_input["Distance Driven (since last charge) (km)"]
    temp = user_input["Temperature (°C)"]

    charge_diff = soc_end - soc_start if soc_end - soc_start != 0 else 1e-6

    features = user_input.copy()
    features["Charging Efficiency (kWh/h)"] = energy / rate if rate != 0 else 0
    features["Energy per Charge %"] = energy / charge_diff
    features["Distance per kWh"] = dist / energy if energy != 0 else 0
    features["Total Charge Gained"] = charge_diff
    features["Charger Efficiency"] = rate / charge_diff
    features["Temperature Adjusted Consumption"] = energy * (1 + abs(temp - 20) / 20)
    
    return features

def predict_km_and_hours_remaining(input_data):
    input_scaled = scaler_km_hours.transform(input_data)
    predicted_km = model_km.predict(input_scaled)[0, 0]
    predicted_hours = model_hours.predict(input_scaled)[0, 0]
    return round(predicted_km, 2), round(predicted_hours, 2)

def create_estimation_interface(root):
    """Creează interfața pentru estimarea km și ore rămase"""
    root.title("Estimare Km și Ore Rămase")
    root.geometry("500x400")
    root.configure(bg="#f0f0f0")

    frame = tk.Frame(root, bg="#f0f0f0")
    frame.pack(pady=20)

    tk.Label(frame, text="Starea bateriei (%):", font=("Arial", 12), bg="#f0f0f0").grid(row=0, column=0, padx=10, pady=5)
    entry_state_of_charge = tk.Entry(frame, font=("Arial", 12))
    entry_state_of_charge.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(frame, text="Capacitatea bateriei (kWh):", font=("Arial", 12), bg="#f0f0f0").grid(row=1, column=0, padx=10, pady=5)
    entry_battery_capacity = tk.Entry(frame, font=("Arial", 12))
    entry_battery_capacity.grid(row=1, column=1, padx=10, pady=5)

    tk.Label(frame, text="Vârsta vehiculului (ani):", font=("Arial", 12), bg="#f0f0f0").grid(row=2, column=0, padx=10, pady=5)
    entry_vehicle_age = tk.Entry(frame, font=("Arial", 12))
    entry_vehicle_age.grid(row=2, column=1, padx=10, pady=5)

    tk.Label(frame, text="Temperatura exterioară (°C):", font=("Arial", 12), bg="#f0f0f0").grid(row=3, column=0, padx=10, pady=5)
    entry_outside_temperature = tk.Entry(frame, font=("Arial", 12))
    entry_outside_temperature.grid(row=3, column=1, padx=10, pady=5)

    road_type_var = tk.StringVar(value='Autostrada')
    tk.Label(frame, text="Tipul de drum:", font=("Arial", 12), bg="#f0f0f0").grid(row=4, column=0, padx=10, pady=5)
    road_type_menu = ttk.Combobox(frame, textvariable=road_type_var, values=['Autostrada', 'Oras', 'Munti'], font=("Arial", 12))
    road_type_menu.grid(row=4, column=1, padx=10, pady=5)

    def predict_distance():
        
        state_of_charge = float(entry_state_of_charge.get())
        battery_capacity = float(entry_battery_capacity.get())
        vehicle_age = float(entry_vehicle_age.get())
        outside_temperature = float(entry_outside_temperature.get())
        road_type = road_type_var.get()

        
        user_input = {
            "Battery Capacity (kWh)": battery_capacity,
            "Energy Consumed (kWh)": 20,  
            "Charging Rate (kW)": 34,     
            "Time of Day": 14,            
            "Day of Week": 3,            
            "State of Charge (Start %)": state_of_charge - 10,  
            "State of Charge (End %)": state_of_charge,
            "Distance Driven (since last charge) (km)": 120,    
            "Temperature (°C)": outside_temperature,
            "Vehicle Age (years)": vehicle_age,
            "Vehicle Model_BMW i3": 0, "Vehicle Model_Chevy Bolt": 0, "Vehicle Model_Hyundai Kona": 0,
            "Vehicle Model_Nissan Leaf": 0, "Vehicle Model_Tesla Model 3": 1,
            "Charging Station Location_Chicago": 0, "Charging Station Location_Houston": 1,
            "Charging Station Location_Los Angeles": 0, "Charging Station Location_New York": 0,
            "Charging Station Location_San Francisco": 0,
            "User Type_Casual Driver": 1, "User Type_Commuter": 0, "User Type_Long-Distance Traveler": 0,
            "Charger Type_DC Fast Charger": 1, "Charger Type_Level 1": 0, "Charger Type_Level 2": 0
        }

        
        full_features = prepare_features_from_user_input(user_input)
        full_features_df = pd.DataFrame([full_features])
        required_order = scaler_km_hours.feature_names_in_.tolist()
        full_features_df = full_features_df.reindex(columns=required_order)
        
        ml_km, ml_hours = predict_km_and_hours_remaining(full_features_df)

      
        base_consumption_per_km = 0.1
        age_factor = 1 + (vehicle_age * 0.02)
        temp_factor = 1.2 if outside_temperature < 0 else (1.15 if outside_temperature > 30 else 1.0)
        road_factor = {"Autostrada": 0.9, "Oras": 1.2, "Munti": 1.5}.get(road_type, 1.0)
        avg_speed = {"Autostrada": 100, "Oras": 50, "Munti": 40}.get(road_type, 60)

        adjusted_consumption_per_km = base_consumption_per_km * age_factor * temp_factor * road_factor
        energy_left = (state_of_charge / 100) * battery_capacity

        estimated_distance = energy_left / adjusted_consumption_per_km
        total_distance = battery_capacity / adjusted_consumption_per_km
        estimated_duration = estimated_distance / avg_speed
        battery_drain_rate = energy_left / estimated_duration if estimated_duration > 0 else 0

       
        result_label.config(text=f"=== Estimări din modele ML ===\n"
                                f"Km rămași estimați (ML): {ml_km} km\n"
                                f"Ore rămase estimate (ML): {ml_hours} ore\n\n"
                                f"=== Estimări pe bază de logică ===\n"
                                f"Distanța estimată: {estimated_distance:.2f} km\n"
                                f"Distanța totală: {total_distance:.2f} km\n"
                                f"Durata estimată: {estimated_duration:.2f} ore\n"
                                f"Viteza de descărcare: {battery_drain_rate:.2f} kWh/oră")

    predict_button = tk.Button(root, text="Prezice", command=predict_distance, font=("Arial", 14), bg="lightblue", padx=20, pady=5)
    predict_button.pack(pady=10)
    
    result_label = tk.Label(root, text="", font=("Arial", 12), justify=tk.LEFT, bg="#f0f0f0")
    result_label.pack()

def predict_distance():
    """Funcție pentru compatibilitate cu codul existent"""
    root = tk.Tk()
    create_estimation_interface(root)
    root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    create_estimation_interface(root)
    root.mainloop()
