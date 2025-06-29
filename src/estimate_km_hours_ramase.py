import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
import tensorflow as tf
from keras import layers, models
import tkinter as tk
from tkinter import ttk, StringVar, OptionMenu
import numpy as np
from .authentification_config import db

class KmHoursEstimatorApp:
    def __init__(self, root, current_user=None, id_token=None, temperatura=None):
        self.model = None
        self.scaler = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.model_trained = False
        self.current_user = current_user
        self.id_token = id_token
        self.selected_vehicle = None
        self.vehicle_battery = {}
        self.vehicle_age = {}
        self.temperatura = temperatura
        self.root = root
        self.create_estimation_interface(self.root)

    def load_vehicles(self):
        if not self.current_user or not self.id_token:
            return []
        sanitized_email = self.current_user.replace('.', '_')
        try:
            vehicles = db.child("vehicule").child(sanitized_email).get(token=self.id_token)
            vehicle_names = []
            if vehicles.each():
                for v in vehicles.each():
                    val = v.val()
                    if 'model' in val and 'baterie_kWh' in val and 'vechime_ani' in val:
                        vehicle_names.append(val['model'])
                        self.vehicle_battery[val['model']] = float(val['baterie_kWh'])
                        self.vehicle_age[val['model']] = float(val['vechime_ani'])
            return vehicle_names
        except Exception as e:
            print(f"Eroare la încărcarea vehiculelor: {str(e)}")
            return []

    def train_model(self):
        try:
            df = pd.read_csv("ev_charging_synthetic_data.csv")
            X = df.drop(columns=["Charging Cost (USD)", "State of Charge (Start %)", "State of Charge (End %)"])
            y = df["Charging Duration (hours)"]
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
         
            model = models.Sequential([
                layers.InputLayer(input_shape=(X_train_scaled.shape[1],)),
                layers.Dense(64, activation='relu'),
                layers.Dense(32, activation='relu'),
                layers.Dense(16, activation='relu'),
                layers.Dense(1)
            ])
            model.compile(optimizer='adam', loss='mse', metrics=['mae'])
            model.fit(X_train_scaled, y_train, epochs=50, batch_size=32, validation_data=(X_test_scaled, y_test), verbose=0)
            self.model = model
            self.scaler = scaler
            self.X_train = X_train
            self.X_test = X_test
            self.y_train = y_train
            self.y_test = y_test
            self.model_trained = True
            y_pred = model.predict(X_test_scaled)
            self.last_mae = mean_absolute_error(y_test, y_pred)
            return True
        except Exception as e:
            self.model = None
            self.scaler = None
            self.model_trained = False
            self.last_model_error = str(e)
            return False

    def predict_duration(self, input_features):
        if not self.model_trained:
            return None, "Modelul nu este antrenat."
        try:
            input_scaled = self.scaler.transform([input_features])
            pred = self.model.predict(input_scaled)[0, 0]
            return pred, None
        except Exception as e:
            return None, str(e)

    def logic_distance_estimation(self, state_of_charge_percent, battery_capacity_kWh, vehicle_age, outside_temperature, road_type):
        # Definirea consumului mediu pe kilometru (kWh/km)
        consumption_per_km = 1 / 10  # 1 kWh pentru 10 kilometri, adică 0.1 kWh/km
        # Ajustăm consumul pe kilometru în funcție de vârsta vehiculului
        age_factor = 1 + (vehicle_age * 0.02)
        # Ajustăm consumul pe kilometru în funcție de temperatura exterioară
        if outside_temperature < 0:
            temp_factor = 1.2
        elif outside_temperature > 30:
            temp_factor = 1.15
        else:
            temp_factor = 1
        # Ajustăm consumul pe kilometru în funcție de tipul de drum
        if road_type == 'Autostrada':
            road_factor = 0.9
        elif road_type == 'Oras':
            road_factor = 1.2
        elif road_type == 'Munti':
            road_factor = 1.5
        else:
            road_factor = 1
        # Calculăm energia rămasă în baterie
        energy_left_in_battery = (state_of_charge_percent / 100) * battery_capacity_kWh
        # Calculăm distanța estimată până la următoarea încărcare ajustată
        estimated_distance = energy_left_in_battery / (consumption_per_km * age_factor * temp_factor * road_factor)
        # Calculăm distanța totală pe care o poate parcurge vehiculul cu bateria complet încărcată
        total_distance = (battery_capacity_kWh / (consumption_per_km * age_factor * temp_factor * road_factor))
        # Estimăm o viteză medie
        if road_type == 'Autostrada':
            avg_speed = 100
        elif road_type == 'Oras':
            avg_speed = 50
        elif road_type == 'Munti':
            avg_speed = 40
        else:
            avg_speed = 60
        estimated_duration = estimated_distance / avg_speed
        battery_drain_rate = energy_left_in_battery / estimated_duration if estimated_duration > 0 else 0
        return estimated_distance, total_distance, estimated_duration, battery_drain_rate

    def create_estimation_interface(self, root):
        root.title("Estimare Durată Încărcare (MLP)")
        root.geometry("500x400")
        root.configure(bg="#f0f0f0")

        frame = tk.Frame(root, bg="#f0f0f0")
        frame.pack(pady=20)

        # Dropdown pentru vehicul
        tk.Label(frame, text="Selectează vehiculul:", font=("Arial", 12), bg="#f0f0f0").grid(row=0, column=0, padx=10, pady=5)
        self.vehicle_var = StringVar()
        vehicle_names = self.load_vehicles()
        if vehicle_names:
            self.vehicle_var.set(vehicle_names[0])
            vehicle_menu = OptionMenu(frame, self.vehicle_var, *vehicle_names)
        else:
            self.vehicle_var.set('Niciun vehicul')
            vehicle_menu = OptionMenu(frame, self.vehicle_var, 'Niciun vehicul')
        vehicle_menu.config(font=("Arial", 12))
        vehicle_menu.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(frame, text="Starea bateriei (%):", font=("Arial", 12), bg="#f0f0f0").grid(row=1, column=0, padx=10, pady=5)
        entry_state_of_charge = tk.Entry(frame, font=("Arial", 12))
        entry_state_of_charge.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(frame, text="Temperatura exterioară (°C):", font=("Arial", 12), bg="#f0f0f0").grid(row=2, column=0, padx=10, pady=5)
        tk.Label(frame, text=str(self.temperatura) + " °C", font=("Arial", 12), bg="#f0f0f0").grid(row=2, column=1, padx=10, pady=5)

        road_type_var = tk.StringVar(value='Autostrada')
        tk.Label(frame, text="Tipul de drum:", font=("Arial", 12), bg="#f0f0f0").grid(row=3, column=0, padx=10, pady=5)
        road_type_menu = ttk.Combobox(frame, textvariable=road_type_var, values=['Autostrada', 'Oras', 'Munti'], font=("Arial", 12))
        road_type_menu.grid(row=3, column=1, padx=10, pady=5)

        result_label = tk.Label(root, text="", font=("Arial", 12), justify=tk.LEFT, bg="#f0f0f0")
        result_label.pack()

        def on_predict():
            if not self.model_trained:
                ok = self.train_model()
                if not ok:
                    result_label.config(text=f"Eroare la antrenarea modelului: {getattr(self, 'last_model_error', 'necunoscută')}")
                    return
            try:
                state_of_charge = float(entry_state_of_charge.get())
                outside_temperature = float(self.temperatura)
                road_type = road_type_var.get()
                vehicul = self.vehicle_var.get()
                battery_capacity = self.vehicle_battery.get(vehicul, 50.0)
                vehicle_age = self.vehicle_age.get(vehicul, 1.0)
                est_dist, tot_dist, est_dur, drain_rate = self.logic_distance_estimation(
                    state_of_charge, battery_capacity, vehicle_age, outside_temperature, road_type)
                result_label.config(
                    text=(
                        f"Distanța estimată până la următoarea încărcare: {est_dist:.2f} km\n"
                        f"Distanța totală cu bateria complet încărcată: {tot_dist:.2f} km\n"
                        f"Durata estimată până la următoarea încărcare: {est_dur:.2f} ore\n"
                        f"Viteza de descărcare a bateriei: {drain_rate:.2f} kWh/oră"
                    )
                )
            except Exception as e:
                result_label.config(text=f"Eroare la estimare: {str(e)}")

        predict_button = tk.Button(root, text="Prezice", command=on_predict, font=("Arial", 14), bg="lightblue", padx=20, pady=5)
        predict_button.pack(pady=10)

# Compatibilitate cu codul existent

def predict_distance():
    app = KmHoursEstimatorApp()
    app.run()

if __name__ == "__main__":
    app = KmHoursEstimatorApp()
    app.run()