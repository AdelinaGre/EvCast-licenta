import tkinter as tk
from tkinter import messagebox, StringVar, OptionMenu, PhotoImage
from PIL import Image, ImageTk
import pandas as pd
import numpy as np
import os
import joblib
from datetime import datetime
from .authentification_config import db, auth

def estimate_realistic_tariff(charger_type):
    """Estimează tariful realist în funcție de tipul de încărcător"""
    if charger_type == "Level 2":
        return 0.25
    elif charger_type == "DC Fast Charger":
        return 0.55
    elif charger_type == "Level 1":
        return 0.15
    return 0.30

def compute_derived_features(input_data):
    """Calculează feature-urile derivate pentru model"""
    energy = input_data["Energy Consumed (kWh)"]
    rate = input_data["Charging Rate (kW)"]
    soc_start = input_data["State of Charge (Start %)"]
    soc_end = input_data["State of Charge (End %)"]
    dist = input_data["Distance Driven (since last charge) (km)"]
    temp = input_data["Temperature (°C)"]

    charge_diff = soc_end - soc_start if (soc_end - soc_start) != 0 else 1e-6

    derived = {
        "Charging Efficiency (kWh/h)": energy / rate if rate != 0 else 0,
        "Energy per Charge %": energy / charge_diff,
        "Distance per kWh": dist / energy if energy != 0 else 0,
        "Total Charge Gained": charge_diff,
        "Charger Efficiency": rate / charge_diff,
        "Temperature Adjusted Consumption": energy * (1 + abs(temp - 20)/20)
    }
    input_data_updated = input_data.copy()
    input_data_updated.update(derived)
    return input_data_updated

class ChargingCost:
    def __init__(self, root, current_user, id_token):
        print("[DEBUG] ChargingCost window opened")
        self.root = root
        self.current_user = current_user
        self.id_token = id_token
        self.root.title("Estimare Cost Încărcare")
        self.root.geometry("1100x700")

      
        self.model = joblib.load("modele/mlpr_charging_cost_model/mlpr_model.pkl")
        self.scaler = joblib.load("modele/mlpr_charging_cost_model/scaler.pkl")

       
        self.features = [
            "Battery Capacity (kWh)", "Energy Consumed (kWh)", "Charging Rate (kW)", "Charging Duration (hours)", "Time of Day", "Day of Week",
            "State of Charge (Start %)", "State of Charge (End %)", "Distance Driven (since last charge) (km)",
            "Temperature (°C)", "Vehicle Age (years)",
            "Vehicle Model_BMW i3", "Vehicle Model_Chevy Bolt", "Vehicle Model_Hyundai Kona",
            "Vehicle Model_Nissan Leaf", "Vehicle Model_Tesla Model 3",
            "Charging Station Location_Chicago", "Charging Station Location_Houston",
            "Charging Station Location_Los Angeles", "Charging Station Location_New York",
            "Charging Station Location_San Francisco",
            "User Type_Casual Driver", "User Type_Commuter", "User Type_Long-Distance Traveler",
            "Charger Type_DC Fast Charger", "Charger Type_Level 1", "Charger Type_Level 2",
            "Charging Efficiency (kWh/h)", "Energy per Charge %", "Distance per kWh",
            "Total Charge Gained", "Charger Efficiency", "Temperature Adjusted Consumption"
        ]

       
        self.bg_image_pil = Image.open("images/white_green_wave.png").resize((1100, 700), Image.Resampling.LANCZOS)
        self.background_image = ImageTk.PhotoImage(self.bg_image_pil)
        self.background_label = tk.Label(self.root, image=self.background_image)
        self.background_label.place(relwidth=1, relheight=1)

        back_button = tk.Button(
            self.root,
            text="Înapoi la Meniu",
            font=("Roboto", 12),
            bg="#39753c",
            fg="white",
            command=self.back_to_menu
        )
        back_button.place(x=935, y=30)

        self.create_widgets()
        self.load_vehicles()

    def create_widgets(self):
        tk.Label(self.root, text="Estimare Cost Încărcare", font=("Roboto", 20, "bold"),
                 bg="white", fg="#39753c").place(x=50, y=150)
        self.logo_image = PhotoImage(file="images/plugin_1.png")
        tk.Label(self.root, image=self.logo_image, bg="white").place(x=30, y=30)
        tk.Label(self.root, text="EVcast", font=("Roboto", 24, "bold"),
                 bg="white", fg="#39753c").place(x=110, y=41)
        tk.Label(self.root, text=f"Utilizator: {self.current_user}", font=("Roboto", 12),
                 bg="white", fg="black").place(x=700, y=30)

        form_frame = tk.Frame(self.root, bg="white", bd=2, relief="solid")
        form_frame.place(x=50, y=200, width=400, height=500)

        self.entries = {}
        fields = [
            "Battery Capacity (kWh)",
            "Charging Rate (kW)",
            "Charging Duration (hours)",
            "State of Charge (Start %)",
            "Distance Driven (since last charge) (km)"
        ]
        for i, field in enumerate(fields):
            tk.Label(form_frame, text=field, bg="white", fg="black",
                    font=("Roboto", 10)).place(x=20, y=20 + i*45)
            entry = tk.Entry(form_frame, bg="white", fg="black",
                           font=("Roboto", 10))
            entry.place(x=20, y=45 + i*45, width=360)
            self.entries[field] = entry

        estimate_button = tk.Button(
            form_frame,
            text="Estimează Costul",
            font=("Roboto", 12, "bold"),
            bg="#39753c",
            fg="white",
            command=self.estimate_cost
        )
        estimate_button.place(x=20, y=370, width=360)

        info_frame = tk.Frame(self.root, bg="white", bd=2, relief="solid")
        info_frame.place(x=500, y=200, width=500, height=400)
        self.info_label = tk.Label(
            info_frame,
            text="Date vehicul și mediu:",
            bg="white",
            fg="black",
            font=("Roboto", 12),
            justify="left",
            anchor="w"
        )
        self.info_label.place(x=20, y=20)
        self.result_label = tk.Label(
            info_frame,
            text="",
            bg="white",
            fg="#39753c",
            font=("Roboto", 16, "bold"),
            justify="center"
        )
        self.result_label.place(x=20, y=200)

    def load_vehicles(self):
        sanitized_email = self.current_user.replace('.', '_')
        try:
            if self.id_token:
                vehicles = db.child("vehicule").child(sanitized_email).get(token=self.id_token)
                if vehicles.each():
                    self.vehicle_var = StringVar()
                    vehicle_frame = tk.Frame(self.root, bg="white")
                    vehicle_frame.place(x=70, y=500, width=350, height=50)
                    tk.Label(vehicle_frame, text="Selectează vehicul:",
                            bg="white", fg="black").pack(side="left", padx=10)
                    vehicle_names = [v.val()['model'] for v in vehicles.each()]
                    vehicle_dropdown = OptionMenu(vehicle_frame, self.vehicle_var,
                                                *vehicle_names,
                                                command=self.update_vehicle_info)
                    vehicle_dropdown.pack(side="left", padx=10)
                    self.vehicle_var.set(vehicle_names[0])
                    self.update_vehicle_info(vehicle_names[0])
        except Exception as e:
            print("Eroare la încărcarea vehiculelor:", str(e))

    def update_vehicle_info(self, selected_vehicle):
        sanitized_email = self.current_user.replace('.', '_')
        try:
            if self.id_token:
                vehicles = db.child("vehicule").child(sanitized_email).get(token=self.id_token)
                for v in vehicles.each():
                    if v.val()['model'] == selected_vehicle:
                        vehicle_info = v.val()
                        info_text = f"Model: {vehicle_info['model']}\n"
                        info_text += f"Baterie: {vehicle_info['baterie_kWh']} kWh\n"
                        info_text += f"Vechime: {vehicle_info['vechime_ani']} ani\n"
                        info_text += f"Tip încărcător: {vehicle_info['tip_incarcator']}\n"
                        info_text += f"Tip utilizator: {vehicle_info['user_type']}\n"
                        now = datetime.now()
                        time_of_day = now.hour
                        day_of_week = now.weekday()
                        info_text += f"Ora curentă: {time_of_day}\n"
                        info_text += f"Ziua săptămânii: {day_of_week}\n"
                        info_text += f"Temperatură: 20°C\n"
                        self.info_label.config(text=info_text)
                        break
        except Exception as e:
            print("Eroare la actualizarea informațiilor vehicul:", str(e))

    def estimate_cost(self):
        try:
           
            field_mapping = {
                "Battery Capacity (kWh)": "Battery Capacity (kWh)",
                "Charging Rate (kW)": "Charging Rate (kW)",
                "Charging Duration (hours)": "Charging Duration (hours)",
                "State of Charge (Start %)": "State of Charge (Start %)",
                "Distance Driven (since last charge) (km)": "Distance Driven (since last charge) (km)"
            }
            features = {}
            for field, entry in self.entries.items():
                key = field_mapping.get(field, field)
                value = entry.get()
                if not value:
                    messagebox.showerror("Eroare", f"Vă rugăm completați câmpul {field}")
                    return
                try:
                    features[key] = float(value)
                except ValueError:
                    messagebox.showerror("Eroare", f"Valoarea pentru {field} trebuie să fie un număr")
                    return

            # Info vehicul
            vehicle_info = self.info_label.cget("text").split("\n")
            vehicul = {}
            for line in vehicle_info:
                if ":" in line:
                    key, value = line.split(":", 1)
                    if "Model" in key:
                        vehicul["model"] = value.strip()
                    elif "Tip utilizator" in key:
                        vehicul["user_type"] = value.strip()
                    elif "Tip încărcător" in key:
                        vehicul["charger_type"] = value.strip()
                    elif "Baterie" in key:
                        features["Battery Capacity (kWh)"] = float(value.split()[0])
                    elif "Vechime" in key:
                        features["Vehicle Age (years)"] = float(value.split()[0])
                    elif "Ora curentă" in key:
                        features["Time of Day"] = float(value.strip())
                    elif "Ziua" in key:
                        features["Day of Week"] = float(value.strip())
                    elif "Temperatură" in key:
                        features["Temperature (°C)"] = float(value.split()[0].replace("°C", ""))

        
            rate = features["Charging Rate (kW)"]
            duration = features["Charging Duration (hours)"]
            capacity = features["Battery Capacity (kWh)"]
            soc_start = features["State of Charge (Start %)"]

            
            soc_diff_possible = 100.0 - soc_start
            max_possible_energy = (soc_diff_possible / 100) * capacity
            energy_consumed = min(rate * duration, max_possible_energy)
            soc_end = soc_start + (energy_consumed / capacity) * 100
            soc_end = min(soc_end, 100.0)

            features["Energy Consumed (kWh)"] = energy_consumed
            features["State of Charge (End %)"] = soc_end

          
            input_dict = {col: 0 for col in self.features}
            for k, v in features.items():
                if k in input_dict:
                    input_dict[k] = v

            
            for col in input_dict:
                if col.startswith("Vehicle Model_") and vehicul.get("model") is not None:
                    model_name = col.replace("Vehicle Model_", "")
                    if model_name == vehicul["model"]:
                        input_dict[col] = 1

          
            for col in input_dict:
                if col.startswith("User Type_") and vehicul.get("user_type") is not None:
                    user_type = col.replace("User Type_", "")
                    if user_type == vehicul["user_type"]:
                        input_dict[col] = 1

          
            for col in input_dict:
                if col.startswith("Charger Type_") and vehicul.get("charger_type") is not None:
                    charger_type = col.replace("Charger Type_", "")
                    if charger_type == vehicul["charger_type"]:
                        input_dict[col] = 1

          
            input_dict["Charging Station Location_Houston"] = 1

            input_dict = compute_derived_features(input_dict)

          
            X = pd.DataFrame([input_dict])
            X = X.reindex(columns=self.features, fill_value=0)
            print("[DEBUG] Input transmis modelului:")
            for col in X.columns:
                print(f"  {col}: {X.iloc[0][col]}")

            
            X_scaled = self.scaler.transform(X)
            predicted_cost = self.model.predict(X_scaled)[0]

          
            charger_type = vehicul.get("charger_type", "Level 2")
            tariff = estimate_realistic_tariff(charger_type)
            realistic_cost = energy_consumed * tariff

        
            result_text = f"Cost estimat încărcare:\n{predicted_cost:.2f} USD\n\n"
            result_text += f"Cost realist (tarif {tariff:.2f} USD/kWh):\n{realistic_cost:.2f} USD\n\n"
            result_text += f"Stare de încărcare estimată:\n{soc_end:.2f}%"
            
            self.result_label.config(text=result_text)

        except Exception as e:
            print("Eroare la estimare cost:", str(e))
            messagebox.showerror("Eroare", f"Eroare la estimarea costului: {str(e)}")

    def back_to_menu(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        from .Menu import MenuInterface
        MenuInterface(self.root, self.current_user, self.id_token)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChargingCost(root, "test@example.com", "test123")
    root.mainloop()
