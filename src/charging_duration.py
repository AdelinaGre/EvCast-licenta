import tkinter as tk
from tkinter import messagebox, PhotoImage, StringVar, OptionMenu
from PIL import Image, ImageTk
import pandas as pd
import os
from datetime import datetime
from authentification_config import db, auth
from openai import OpenAI
from dotenv import load_dotenv

# Încercăm să importăm joblib și sklearn
try:
    import joblib
    from sklearn.ensemble import RandomForestRegressor
except ImportError:
    import subprocess
    import sys
    
    def install_requirements():
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "scikit-learn"])
            messagebox.showinfo("Instalare", "Dependențe instalate cu succes. Vă rugăm reporniți aplicația.")
        except Exception as e:
            messagebox.showerror("Eroare", f"Nu s-a putut instala scikit-learn: {str(e)}")
        sys.exit(1)
    
    install_requirements()

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

class ChargingDuration:
    def __init__(self, root, current_user, id_token):
        self.root = root
        self.current_user = current_user
        self.id_token = id_token
        self.root.title("Estimare Durată Încărcare")
        self.root.geometry("1100x700")
        
        # Inițializare client OpenAI pentru comenzi vocale
        self.client = OpenAI(api_key=openai_api_key)
        
        try:
            self.model = joblib.load("modele/rf_charging_duration_model.joblib")
        except Exception as e:
            messagebox.showerror("Eroare", f"Nu s-a putut încărca modelul: {str(e)}")
            self.back_to_menu()
            return
        
        # Fundal
        try:
            self.bg_image_pil = Image.open("images/green_wave.jpeg").resize((1100, 700), Image.Resampling.LANCZOS)
            self.background_image = ImageTk.PhotoImage(self.bg_image_pil)
            self.background_label = tk.Label(self.root, image=self.background_image)
            self.background_label.place(relwidth=1, relheight=1)
        except Exception as e:
            print(f"Eroare la încărcarea imaginii de fundal: {str(e)}")
            self.root.configure(bg="#0D0D0D")

        # Buton înapoi la meniu
        back_button = tk.Button(
            self.root,
            text="↩ Înapoi la Meniu",
            font=("Roboto", 12),
            bg="#B9EF17",
            fg="#0D0D0D",
            command=self.back_to_menu
        )
        back_button.place(x=935, y=30)

        self.create_widgets()
        self.load_vehicles()
        
    def create_widgets(self):
        # Titlu
        tk.Label(self.root, text="Estimare Durată Încărcare", font=("Roboto", 20, "bold"),
                 bg="#0D0D0D", fg="#B9EF17").place(x=50, y=150)

        # Logo și nume aplicație
        self.logo_image = PhotoImage(file="images/plugin.png")
        tk.Label(self.root, image=self.logo_image, bg="#0D0D0D").place(x=30, y=30)
        tk.Label(self.root, text="EVcast", font=("Roboto", 24, "bold"),
                 bg="#0D0D0D", fg="white").place(x=110, y=41)
        tk.Label(self.root, text=f"Utilizator: {self.current_user}", font=("Roboto", 12),
                 bg="#0D0D0D", fg="white").place(x=700, y=30)

        # Frame pentru formular
        form_frame = tk.Frame(self.root, bg="#1A1C1A", bd=2, relief="solid")
        form_frame.place(x=50, y=200, width=400, height=400)

        # Câmpuri de introducere
        self.entries = {}
        fields = [
            "Energy Consumed (kWh)",
            "Charging Rate (kWh)",
            "Charging Cost (USD)",
            "State of Charge (Start %)",
            "State of Charge (End %)",
            "Distance Driven (km)"
        ]

        for i, field in enumerate(fields):
            field_frame = tk.Frame(form_frame, bg="#1A1C1A")
            field_frame.place(x=20, y=20 + i*50, width=360)
            
            tk.Label(field_frame, text=field, bg="#1A1C1A", fg="white",
                    font=("Roboto", 10)).pack(side="left")
            
            entry = tk.Entry(field_frame, bg="#262626", fg="white",
                           font=("Roboto", 10))
            entry.pack(side="left", padx=5)
            
            voice_button = tk.Button(field_frame, text="🎤", bg="#B9EF17",
                                   fg="#0D0D0D", command=lambda f=field: self.record_field_value(f))
            voice_button.pack(side="left", padx=5)
            
            self.entries[field] = entry

        # Buton estimare
        estimate_button = tk.Button(
            form_frame,
            text="Estimează Durata",
            font=("Roboto", 12, "bold"),
            bg="#B9EF17",
            fg="#0D0D0D",
            command=self.estimate_duration
        )
        estimate_button.place(x=20, y=320, width=360)

        # Buton pentru introducere vocală a tuturor câmpurilor
        voice_all_button = tk.Button(
            form_frame,
            text="🎤 Introducere Vocală Toate Câmpurile",
            font=("Roboto", 12, "bold"),
            bg="#B9EF17",
            fg="#0D0D0D",
            command=self.record_all_fields
        )
        voice_all_button.place(x=20, y=360, width=360)

        info_frame = tk.Frame(self.root, bg="#1A1C1A", bd=2, relief="solid")
        info_frame.place(x=500, y=200, width=500, height=400)

        self.info_label = tk.Label(
            info_frame,
            text="Date vehicul și mediu:",
            bg="#1A1C1A",
            fg="white",
            font=("Roboto", 12),
            justify="left",
            anchor="w"
        )
        self.info_label.place(x=20, y=20)

        # Label pentru rezultat
        self.result_label = tk.Label(
            info_frame,
            text="",
            bg="#1A1C1A",
            fg="#B9EF17",
            font=("Roboto", 16, "bold"),
            justify="center"
        )
        self.result_label.place(x=20, y=200)

    def load_vehicles(self):
        """Încarcă vehiculele din Firebase"""
        sanitized_email = self.current_user.replace('.', '_')
        try:
            if self.id_token:
                vehicles = db.child("vehicule").child(sanitized_email).get(token=self.id_token)
                if vehicles.each():
                    # Creăm dropdown pentru selectarea vehiculului
                    self.vehicle_var = StringVar()
                    vehicle_frame = tk.Frame(self.root, bg="#1A1C1A")
                    vehicle_frame.place(x=50, y=620, width=400, height=50)
                    
                    tk.Label(vehicle_frame, text="Selectează vehicul:",
                            bg="#1A1C1A", fg="white").pack(side="left", padx=10)
                    
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
        """Actualizează informațiile despre vehiculul selectat"""
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
                        
                        # Adăugăm informații despre timp și temperatură
                        now = datetime.now()
                        time_of_day = now.hour // 6  # 0=noapte, 1=dimineață, 2=zi, 3=seară
                        day_of_week = now.weekday()
                        
                        time_of_day_map = {0: "Noapte", 1: "Dimineață", 2: "Zi", 3: "Seară"}
                        day_of_week_map = {
                            0: "Luni", 1: "Marți", 2: "Miercuri", 3: "Joi",
                            4: "Vineri", 5: "Sâmbătă", 6: "Duminică"
                        }
                        
                        info_text += f"Perioada zilei: {time_of_day_map[time_of_day]}\n"
                        info_text += f"Ziua săptămânii: {day_of_week_map[day_of_week]}\n"
                        
                     
                        info_text += f"Temperatură: 20°C\n"
                        
                        self.info_label.config(text=info_text)
                        break
        except Exception as e:
            print("Eroare la actualizarea informațiilor vehicul:", str(e))

    def compute_derived_features(self, input_data):
        energy = input_data["Energy Consumed (kWh)"]
        rate = input_data["Charging Rate (kW)"]
        soc_start = input_data["State of Charge (Start %)"]
        soc_end = input_data["State of Charge (End %)"]
        dist = input_data["Distance Driven (since last charge) (km)"]
        temp = input_data["Temperature (°C)"]

        charge_diff = soc_end - soc_start if (soc_end - soc_start) != 0 else 1e-6  # evită divizare la zero

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

    def estimate_duration(self):
        """Estimează durata de încărcare folosind modelul, cu one-hot encoding corect și mapping explicit pentru denumiri."""
        try:
            # Mapping explicit între label-urile din interfață și cheile din model
            field_mapping = {
                "Energy Consumed (kWh)": "Energy Consumed (kWh)",
                "Charging Rate (kWh)": "Charging Rate (kW)",
                "Charging Rate (kW)": "Charging Rate (kW)",
                "Charging Cost (USD)": "Charging Cost (USD)",
                "State of Charge (Start %)": "State of Charge (Start %)",
                "State of Charge (End %)": "State of Charge (End %)",
                "Distance Driven (km)": "Distance Driven (since last charge) (km)",
                "Distance Driven (since last charge) (km)": "Distance Driven (since last charge) (km)",
                "Battery Capacity (kWh)": "Battery Capacity (kWh)",
                "Vehicle Age (years)": "Vehicle Age (years)",
                "Temperature (°C)": "Temperature (°C)",
                "Time of Day": "Time of Day",
                "Day of Week": "Day of Week"
            }
            # Colectăm datele din formular cu mapping corect
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

            # Extragem info vehicul și mediu cu mapping corect
            vehicle_info = self.info_label.cget("text").split("\n")
            vehicul = {}
            for line in vehicle_info:
                if ":" in line:
                    key, value = line.split(":", 1)
                    mapped_key = field_mapping.get(key.strip(), key.strip())
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
                    elif "Perioada" in key:
                        features["Time of Day"] = value.strip()
                    elif "Ziua" in key:
                        features["Day of Week"] = value.strip()
                    elif "Temperatură" in key:
                        features["Temperature (°C)"] = float(value.split()[0].replace("°C", ""))

            # Construim vectorul de input cu one-hot encoding
            input_dict = {col: 0 for col in self.model.feature_names_in_}

            # Setăm valorile numerice
            for k, v in features.items():
                if k in input_dict:
                    input_dict[k] = v

            # One-hot pentru Vehicle Model
            for col in input_dict:
                if col.startswith("Vehicle Model_") and vehicul.get("model") is not None:
                    model_name = col.replace("Vehicle Model_", "")
                    if model_name == vehicul["model"]:
                        input_dict[col] = 1
            # One-hot pentru User Type
            for col in input_dict:
                if col.startswith("User Type_") and vehicul.get("user_type") is not None:
                    user_type = col.replace("User Type_", "")
                    if user_type == vehicul["user_type"]:
                        input_dict[col] = 1
            # One-hot pentru Charger Type
            for col in input_dict:
                if col.startswith("Charger Type_") and vehicul.get("charger_type") is not None:
                    charger_type = col.replace("Charger Type_", "")
                    if charger_type == vehicul["charger_type"]:
                        input_dict[col] = 1
            # Setăm Time of Day ca float, doar ora întreagă (ex: 20 pentru 20:01)
            ora_curenta = float(datetime.now().hour)
            if "Time of Day" in input_dict:
                input_dict["Time of Day"] = ora_curenta
            # Setăm Day of Week ca float, 0=Luni ... 6=Duminica
            ziua_saptamanii = float(datetime.now().weekday())
            if "Day of Week" in input_dict:
                input_dict["Day of Week"] = ziua_saptamanii
            # Setăm doar Temperature dacă există
            for k in ["Temperature (°C)"]:
                if k in features and k in input_dict:
                    input_dict[k] = features[k]

            # --- Adaugă feature-uri derivate necesare ---
            input_dict = self.compute_derived_features(input_dict)
            # --- 8. Prezice durata ---
            # Reindexează inputul după ordinea corectă a coloanelor modelului
            X = pd.DataFrame([input_dict])
            X = X.reindex(columns=self.model.feature_names_in_, fill_value=0)
            print("[DEBUG] Input transmis modelului:")
            for col in X.columns:
                print(f"  {col}: {X.iloc[0][col]}")
            predicted_duration = self.model.predict(X)[0]
            # Calculează R^2 pe model (dacă există atributul score_ sau o metodă similară)
            r2 = getattr(self.model, 'score', None)
            r2_text = ''
            if hasattr(self.model, 'score_'):
                r2_text = f"R² model: {self.model.score_:.3f}"
            elif hasattr(self.model, 'best_score_'):
                r2_text = f"R² model: {self.model.best_score_:.3f}"
            elif r2 is not None and hasattr(self.model, 'X_train_') and hasattr(self.model, 'y_train_'):
                r2_val = self.model.score(self.model.X_train_, self.model.y_train_)
                r2_text = f"R² model: {r2_val:.3f}"
            if predicted_duration < 1:
                minutes = predicted_duration * 60
                rezultat = f"Durata estimată de încărcare:\n{minutes:.1f} minute"
            else:
                rezultat = f"Durata estimată de încărcare:\n{predicted_duration:.2f} ore"
            rezultat += f"\n{r2_text}"
            self.result_label.config(text=rezultat)

            # Salvare în Firebase
            try:
                if not self.id_token:
                    print("Nu există token de autentificare pentru salvare")
                    messagebox.showwarning("Avertisment", "Nu sunteți autentificat. Vă rugăm să vă autentificați din nou.")
                    return

                sanitized_email = self.current_user.replace('.', '_')
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                model_vehicul = vehicul.get("model", "Necunoscut")
                
                # Pregătim datele pentru salvare
                history_data = {
                    "timestamp": timestamp,
                    "utilizator": self.current_user,
                    "tip_utilizator": vehicul.get("user_type", "Necunoscut"),
                    "tip_incarcator": vehicul.get("charger_type", "Necunoscut"),
                    "features": {
                        "energy_consumed": features.get("Energy Consumed (kWh)", 0),
                        "charging_rate": features.get("Charging Rate (kW)", 0),
                        "state_of_charge_start": features.get("State of Charge (Start %)", 0),
                        "state_of_charge_end": features.get("State of Charge (End %)", 0),
                        "distance": features.get("Distance Driven (km)", 0),
                        "temperature": features.get("Temperature (°C)", 0),
                        "battery_capacity": features.get("Battery Capacity (kWh)", 0),
                        "vehicle_age": features.get("Vehicle Age (years)", 0),
                        "time_of_day": features.get("Time of Day", 0),
                        "day_of_week": features.get("Day of Week", 0)
                    },
                    "derived_features": {
                        "charging_efficiency": input_dict.get("Charging Efficiency (kWh/h)", 0),
                        "energy_per_charge": input_dict.get("Energy per Charge %", 0),
                        "distance_per_kwh": input_dict.get("Distance per kWh", 0),
                        "total_charge_gained": input_dict.get("Total Charge Gained", 0),
                        "charger_efficiency": input_dict.get("Charger Efficiency", 0),
                        "temperature_adjusted_consumption": input_dict.get("Temperature Adjusted Consumption", 0)
                    },
                    "predictii": {
                        "durata_estimata_ore": float(predicted_duration),
                        "durata_estimata_minute": float(predicted_duration * 60) if predicted_duration < 1 else 0,
                        "r2_score": float(r2_val) if 'r2_val' in locals() else 0
                    }
                }

                # Salvăm în Firebase sub istoric_date/{email_utilizator}/{model_vehicul}
                try:
                    db.child("istoric_date").child(sanitized_email).child(model_vehicul).push(history_data, token=self.id_token)
                    print(f"Date salvate cu succes în Firebase pentru utilizatorul {self.current_user} și modelul {model_vehicul}")
                    messagebox.showinfo("Succes", "Datele au fost salvate cu succes în istoric")
                except Exception as firebase_error:
                    error_message = str(firebase_error)
                    if "401" in error_message or "Permission denied" in error_message:
                        messagebox.showerror("Eroare de Permisiuni", 
                            "Nu aveți permisiunea de a salva date în baza de date. Vă rugăm să vă autentificați din nou sau contactați administratorul.")
                    else:
                        messagebox.showerror("Eroare", 
                            f"Nu s-au putut salva datele în istoric: {error_message}")
                    print(f"Eroare la salvarea în Firebase: {error_message}")

            except Exception as e:
                print(f"Eroare la pregătirea datelor pentru salvare: {str(e)}")
                messagebox.showerror("Eroare", 
                    "A apărut o eroare la pregătirea datelor pentru salvare. Vă rugăm încercați din nou.")

        except Exception as e:
            print("Eroare la estimare:", str(e))
            messagebox.showerror("Eroare", f"Eroare la estimarea duratei: {str(e)}")

    def back_to_menu(self):
        """Închide interfața curentă și revine la meniu"""
        for widget in self.root.winfo_children():
            widget.destroy()
            
        from Menu import MenuInterface
        MenuInterface(self.root, self.current_user, self.id_token)

    def record_field_value(self, field):
        """Înregistrează valoarea pentru un câmp specific"""
        try:
            import sounddevice as sd
            import numpy as np
            from scipy.io.wavfile import write
            import tempfile
            import os

            # Configurare înregistrare
            fs = 44100
            duration = 5  # secunde
            print(f"Înregistrare valoare pentru {field}...")

            # Înregistrare audio
            audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
            sd.wait()

            # Salvare temporară
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            write(temp_path, fs, audio)

            # Transcriere cu Whisper
            with open(temp_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ro"
                )
            text = str(transcription)
            print(f"Valoare detectată pentru {field}: {text}")

            # Extrage numărul din text
            import re
            numbers = re.findall(r'\d+\.?\d*', text)
            if numbers:
                value = numbers[0]
                self.entries[field].delete(0, tk.END)
                self.entries[field].insert(0, value)
                messagebox.showinfo("Succes", f"Valoare {value} introdusă pentru {field}")
            else:
                messagebox.showerror("Eroare", "Nu s-a putut detecta o valoare numerică")

            # Curățare fișier temporar
            os.remove(temp_path)

        except Exception as e:
            print(f"Eroare la înregistrarea valorii: {str(e)}")
            messagebox.showerror("Eroare", f"Nu s-a putut procesa înregistrarea: {str(e)}")

    def record_all_fields(self):
        """Înregistrează toate valorile câmpurilor într-o singură înregistrare"""
        try:
            import sounddevice as sd
            import numpy as np
            from scipy.io.wavfile import write
            import tempfile
            import os

            # Configurare înregistrare
            fs = 44100
            duration = 15  # secunde pentru toate câmpurile
            print("Înregistrare toate valorile...")

            # Înregistrare audio
            audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
            sd.wait()

            # Salvare temporară
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            write(temp_path, fs, audio)

            # Transcriere cu Whisper
            with open(temp_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ro"
                )
            text = str(transcription)
            print(f"Text detectat: {text}")

            # Procesare text pentru fiecare câmp
            import re
            for field in self.entries.keys():
                # Caută numere după cuvinte cheie specifice câmpului
                field_keywords = {
                    "Energy Consumed (kWh)": ["energie", "consum", "kwh"],
                    "Charging Rate (kWh)": ["rata", "incarcare", "kw"],
                    "Charging Cost (USD)": ["cost", "pret", "usd"],
                    "State of Charge (Start %)": ["start", "inceput", "procent"],
                    "State of Charge (End %)": ["final", "sfarsit", "procent"],
                    "Distance Driven (km)": ["distanta", "km"]
                }

                keywords = field_keywords.get(field, [])
                for keyword in keywords:
                    pattern = f"{keyword}\\s*(\\d+\\.?\\d*)"
                    match = re.search(pattern, text.lower())
                    if match:
                        value = match.group(1)
                        self.entries[field].delete(0, tk.END)
                        self.entries[field].insert(0, value)
                        break

            messagebox.showinfo("Succes", "Valorile au fost introduse. Verificați și ajustați dacă este necesar.")

            # Curățare fișier temporar
            os.remove(temp_path)

        except Exception as e:
            print(f"Eroare la înregistrarea valorilor: {str(e)}")
            messagebox.showerror("Eroare", f"Nu s-a putut procesa înregistrarea: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChargingDuration(root, "test@example.com", "test123")
    root.mainloop()
