import tkinter as tk
import pandas as pd
from tkinter import messagebox
from tkinter import PhotoImage
from PIL import Image, ImageTk
import subprocess
import os
from datetime import datetime
import requests
import json
from pathlib import Path
import threading
from openai import OpenAI
from dotenv import load_dotenv
from graph_generator import plot_features
import pandas as pd
from authentification_config import db, auth
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import unicodedata
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import util
import csv


try:
    from .users_signing import UserSigning
    from .vehicle_profile import VehicleProfile
except ImportError:
    from users_signing import UserSigning
    from vehicle_profile import VehicleProfile


COLORS = {
    "BACKGROUND": "#FFFFFF",
    "SECONDARY_BG": "#9dbf9d",
    "ACCENT": "#39753c",
    "TEXT": "black",
    "HOVER": "#D4FF3F",
    "INPUT_BG": "#FFFFFF"
}

FONTS = {
    "TITLE": ("Roboto", 20, "bold"),
    "APP_NAME": ("Roboto", 24, "bold"),
    "USER": ("Roboto", 12),
    "BUTTON": ("Roboto", 12),
    "INFO": ("Roboto", 10)
}

class MenuInterface:
    def __init__(self, root, current_user, id_token):
        self.root = root
        self.current_user = current_user
        self.id_token = id_token
        self.root.title("Menu")
        self.root.geometry("1100x700")
        
        
        self.background_image = None
        self.logo_image = None
        self.power_image = None
        
        
        load_dotenv()
        openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=openai_api_key)
        
        
        self.is_recording = False
        self.recording_thread = None
        
        
        self.plot_frame = tk.Frame(self.root, bg=COLORS["BACKGROUND"])
        self.plot_frame.place(x=400, y=220, width=650, height=400)
        
        
        self.current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.images_dir = os.path.join(self.current_dir, "images")
        
        
        self.current_data = {
            "time": None,
            "date": None,
            "time_of_day": None,
            "day_of_week": None,
            "temperature": None
        }
        
        
        self.load_saved_data()
        
       
        self.root.after(60000, self.update_current_data) 
        
        self.user_signing = UserSigning()
        self.create_widgets()             
        self.update_current_data() 
        
        self.create_vehicle_selector()
        
        first_vehicle = self.get_first_vehicle_for_user()
        self.show_vehicle_image(first_vehicle)

    def refresh_token(self):
       
        try:
           
            user = auth.refresh(self.id_token)
            self.id_token = user['idToken']
            return True
        except Exception as e:
            print(f"Eroare la reînnoirea token-ului: {str(e)}")
            messagebox.showerror("Eroare de autentificare", 
                "Sesiunea a expirat. Vă rugăm să vă autentificați din nou.")
           
            self.root.destroy()
            root_login = tk.Tk()
            from login_interface import LoginInterface
            app = LoginInterface(root_login, self.current_user, "")  
            root_login.mainloop()
            return False

    def safe_firebase_operation(self, operation, *args, **kwargs):
       
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            if "401" in str(e) or "Permission denied" in str(e):
                if self.refresh_token():
                    
                    kwargs['token'] = self.id_token
                    return operation(*args, **kwargs)
            raise e

    def update_current_data(self):
        """Actualizează datele curente"""
        now = datetime.now()
        
        
        self.current_data.update({
            "time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%d/%m/%Y"),
            "time_of_day": now.hour // 6,  # 0=noapte, 1=dimineață, 2=zi, 3=seară
            "day_of_week": now.weekday(),  # 0=Luni, 6=Duminică
        })
        
       
        self.update_temperature()
        
       
        self.update_info_display()
        
        
        self.save_current_data()
        
       
        self.root.after(60000, self.update_current_data)

    def update_temperature(self):
       
        try:
          
            lat = 44.4268
            lon = 26.1025
            openweather_api_key = os.getenv("OPENWEATHER_API_KEY")
            api_key = openweather_api_key
            url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
          
            response = requests.get(url)
            # print(f"Status code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                # print(f"Răspuns API: {data}")
                if "main" in data and "temp" in data["main"]:
                    self.current_data["temperature"] = round(data["main"]["temp"])
                    # print(f"Temperatură actualizată: {self.current_data['temperature']}°C")
                # else:
                #     print("Eroare: Nu s-a găsit temperatura în răspunsul API")
            # else:
            #     print(f"Eroare API: {response.text}")
            #     print(f"Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            # print(f"Eroare de conexiune: {str(e)}")
            pass
        except Exception as e:
            # print(f"Eroare neașteptată: {str(e)}")
            pass
    

    def save_current_data(self):
       
        try:
            data_file = os.path.join(self.current_dir, "current_data.json")
            with open(data_file, 'w') as f:
                json.dump(self.current_data, f)
        except Exception as e:
            print(f"Eroare la salvarea datelor: {str(e)}")

    def load_saved_data(self):
       
        try:
            data_file = os.path.join(self.current_dir, "current_data.json")
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    self.current_data = json.load(f)
        except Exception as e:
            print(f"Eroare la încărcarea datelor: {str(e)}")

    def create_info_display(self):
       
        
        self.top_info_row = tk.Frame(self.root, bg=COLORS["BACKGROUND"])
        self.top_info_row.place(x=50, y=100, height=80) 

        self.info_labels = {}
        info_items = [
            ("time", "Ora"),
            ("date", "Data"),
            ("time_of_day", "Perioada"),
            ("day_of_week", "Ziua"),
            ("temperature", "Temperatura")
        ]

        box_width = 180
        box_height = 65
        box_padx = 12
        box_pady = 5
        for idx, (key, label) in enumerate(info_items):
            container = tk.Frame(
                self.top_info_row,
                width=box_width,
                height=box_height,
                bg=COLORS["SECONDARY_BG"],
                highlightbackground=COLORS["ACCENT"],
                highlightthickness=2
            )
            container.pack_propagate(False)
            container.pack(side="left", padx=box_padx, pady=box_pady)

            title = tk.Label(
                container,
                text=label,
                font=FONTS["INFO"],
                fg=COLORS["TEXT"],
                bg=COLORS["SECONDARY_BG"]
            )
            title.pack(pady=(5, 0))

            value_label = tk.Label(
                container,
                text="",
                font=("Roboto", 13, "bold"),
                #fg=COLORS["TEXT"],
                fg=COLORS["INPUT_BG"],
                bg=COLORS["SECONDARY_BG"]
            )
            value_label.pack()
            self.info_labels[key] = value_label


    def update_info_display(self):
        
        if hasattr(self, 'info_labels'):
           
            if "time" in self.info_labels and self.info_labels["time"].winfo_exists():
                self.info_labels["time"].config(text=self.current_data["time"])
            if "date" in self.info_labels and self.info_labels["date"].winfo_exists():
                self.info_labels["date"].config(text=self.current_data["date"])
           
            time_of_day_map = {0: "Noapte", 1: "Dimineață", 2: "Zi", 3: "Seară"}
            if "time_of_day" in self.info_labels and self.info_labels["time_of_day"].winfo_exists():
                self.info_labels["time_of_day"].config(
                    text=time_of_day_map.get(self.current_data["time_of_day"], "Necunoscut")
                )
           
            day_of_week_map = {
                0: "Luni", 1: "Marți", 2: "Miercuri", 3: "Joi",
                4: "Vineri", 5: "Sâmbătă", 6: "Duminică"
            }
            if "day_of_week" in self.info_labels and self.info_labels["day_of_week"].winfo_exists():
                self.info_labels["day_of_week"].config(
                    text=day_of_week_map.get(self.current_data["day_of_week"], "Necunoscut")
                )
           
            temp = self.current_data["temperature"]
            temp_text = f"{temp}°C" if temp is not None else "N/A"
            if "temperature" in self.info_labels and self.info_labels["temperature"].winfo_exists():
                self.info_labels["temperature"].config(text=temp_text)

    def setup_background(self):
       
        try:
            bg_path = os.path.join(self.images_dir, "white_green_wave.png")
            if os.path.exists(bg_path):
                bg_image = Image.open(bg_path)
                bg_image = bg_image.resize((1100, 700), Image.Resampling.LANCZOS)
                self.background_image = ImageTk.PhotoImage(bg_image)
                background_label = tk.Label(self.root, image=self.background_image)
                background_label.place(relwidth=1, relheight=1)
            else:
                print(f"Nu s-a găsit imaginea de fundal la calea {bg_path}")
                self.root.configure(bg=COLORS["BACKGROUND"])
        except Exception as e:
            print(f"Eroare la încărcarea imaginii de fundal: {str(e)}")
            self.root.configure(bg=COLORS["BACKGROUND"])

    def create_header(self):
       
        try:
            logo_path = os.path.join(self.images_dir, "plugin_1.png")
            if os.path.exists(logo_path):
                logo_image = Image.open(logo_path)
                self.logo_image = ImageTk.PhotoImage(logo_image)
                logo_label = tk.Label(self.root, image=self.logo_image, bg=COLORS["BACKGROUND"])
                logo_label.place(x=30, y=30)
            else:
                print(f"Nu s-a găsit logo-ul la calea {logo_path}")
        except Exception as e:
            print(f"Eroare la încărcarea logo-ului: {str(e)}")

       
        self.label_app_name = tk.Label(
            self.root, 
            text="EVcast", 
            font=FONTS["APP_NAME"], 
            bg=COLORS["BACKGROUND"], 
            fg=COLORS["TEXT"]
        )
        self.label_app_name.place(x=110, y=41)

        
        self.label_user = tk.Label(
            self.root, 
            text=f"Utilizator: {self.current_user}", 
            font=FONTS["USER"],
            bg=COLORS["BACKGROUND"], 
            fg=COLORS["TEXT"]
        )
        self.label_user.place(x=850, y=50)

    def create_buttons(self):
      
        def on_enter(e): e.widget['background'] = COLORS["HOVER"]
        def on_leave(e): e.widget['background'] = COLORS["ACCENT"]

       
        left_buttons = [
            ("🚗 Profil Vehicul", self.profil_vehicul, 220),
            ("💰 Estimare Cost Încărcare", self.estimare_cost, 260),
            ("💰 Estimare Durata Încărcare", self.estimare_durata_incarcare, 300),
            ("⏱️ Estimare Km si H ramase", self.estimare_h_km_ramase, 340),
        ]
        for text, command, y_pos in left_buttons:
            button = tk.Button(
                self.root, 
                text=text, 
                font=FONTS["BUTTON"], 
                bg=COLORS["ACCENT"],
                fg=COLORS["BACKGROUND"], 
                relief="flat", 
                command=command, 
                cursor="hand2"
            )
            button.place(x=60, y=y_pos, width=220, height=30)
            button.bind("<Enter>", on_enter)
            button.bind("<Leave>", on_leave)

       
        right_x = 830
        right_width = 225
      
        opt_y = 300
        prog_y = 340
        opt_button = tk.Button(
            self.root,
            text="⚡ Optimizare Încărcare",
            font=FONTS["BUTTON"],
            bg=COLORS["ACCENT"],
            fg=COLORS["BACKGROUND"],
            relief="flat",
            command=self.optimizare_incarcare,
            cursor="hand2"
        )
        opt_button.place(x=right_x, y=opt_y, width=right_width, height=30)
        opt_button.bind("<Enter>", on_enter)
        opt_button.bind("<Leave>", on_leave)

        prog_button = tk.Button(
            self.root,
            text="📅 Programează Încărcare",
            font=FONTS["BUTTON"],
            bg=COLORS["ACCENT"],
            fg=COLORS["BACKGROUND"],
            relief="flat",
            command=self.programare_incarcare_agent,
            cursor="hand2"
        )
        prog_button.place(x=right_x, y=prog_y, width=right_width, height=30)
        prog_button.bind("<Enter>", on_enter)
        prog_button.bind("<Leave>", on_leave)

    def create_widgets(self):
       
        self.setup_background()
        
     
        self.label_title = tk.Label(
            self.root, 
            text="MENU", 
            font=FONTS["TITLE"], 
            bg=COLORS["BACKGROUND"], 
            fg=COLORS["ACCENT"]
        )
        self.label_title.place(x=50, y=150)

        self.create_header()
        self.create_buttons()
        self.create_info_display()
        self.update_info_display()  
        self.update_time_label()   
        
       
        voice_button = tk.Button(
            self.root,
            text="🎤 Comandă Vocală",
            font=FONTS["BUTTON"],
            bg=COLORS["ACCENT"],
            fg=COLORS["BACKGROUND"],
            command=self.toggle_voice_command
        )
        voice_button.place(x=830, y=260, width=225)

       
        self.create_scheduled_charging_widget()

    def update_time_label(self):
       
        try:
            if "time" in self.info_labels and self.info_labels["time"].winfo_exists():
                from datetime import datetime
                now = datetime.now()
                time_str = now.strftime("%H:%M:%S")
                self.info_labels["time"].config(text=time_str)
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.after(1000, self.update_time_label)
        except Exception as e:
            print(f"Eroare la actualizarea timpului: {str(e)}")

    def profil_vehicul(self):
       
        for widget in self.root.winfo_children():
            widget.destroy()
            
        VehicleProfile(self.root, self.current_user, self.id_token)

    def estimare_durata_incarcare(self):
       
        for widget in self.root.winfo_children():
            widget.destroy()
            
       
        from charging_duration import ChargingDuration
        ChargingDuration(self.root, self.current_user, self.id_token)

    def estimare_cost(self):
       
        for widget in self.root.winfo_children():
            widget.destroy()
        from charging_cost import ChargingCost
        ChargingCost(self.root, self.current_user, self.id_token)

    def estimare_h_km_ramase(self):
      
        import tensorflow as tf
        import joblib
        model_km = tf.keras.models.load_model("modele/seq_layers_km_model.h5", custom_objects={'mse': tf.keras.losses.MeanSquaredError()})
        model_hours = tf.keras.models.load_model("modele/seq_layers_hours_model.h5", custom_objects={'mse': tf.keras.losses.MeanSquaredError()})
        scaler_km_hours = joblib.load("modele/scaler_km_h.pkl")

        from estimate_km_hours_ramase import create_estimation_interface
        top=tk.Toplevel(self.root)
        create_estimation_interface(top)

    def toggle_voice_command(self):
       
        if not self.is_recording:
            self.start_voice_recording()
        else:
            self.stop_voice_recording()

    def start_voice_recording(self):
       
        self.is_recording = True
        self.recording_thread = threading.Thread(target=self.record_voice_command)
        self.recording_thread.daemon = True
        self.recording_thread.start()

    def stop_voice_recording(self):
       
        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join()

    def get_data_for_vehicle(self, user_email, model, token):
        sanitized_email = user_email.replace('.', '_')
        sessions = db.child("istoric_date").child(sanitized_email).child(model).get(token=token)
        data = []
        if sessions.each() is not None:
            for session in sessions.each():
                row = {}
                session_data = session.val()
                features = session_data.get('features', {})
                derived = session_data.get('derived_features', {})
                predictii = session_data.get('predictii', {})
                row.update(features)
                row.update(derived)
                row.update(predictii)
               
                for k, v in session_data.items():
                    if k not in ['features', 'derived_features', 'predictii']:
                        row[k] = v
                data.append(row)
        else:
            print("Nu există sesiuni pentru acest model și utilizator.")
        return pd.DataFrame(data)

    def show_plot_in_tkinter(self, fig, df=None, f1=None, f2=None, model=None):
       
        plot_window = tk.Toplevel(self.root)
        plot_window.title("Grafic generat")
        canvas = FigureCanvasTkAgg(fig, master=plot_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

       
        swap_state = {'swapped': False}

        def recreate_plot():
            import matplotlib.pyplot as plt
            fig2, ax2 = plt.subplots(figsize=(8, 4))
            fig2.patch.set_facecolor('white')
            ax2.set_facecolor('white')
            if swap_state['swapped']:
                x, y = df[f2], df[f1]
                xlabel, ylabel = f2, f1
                title = f"{f1} vs {f2} pentru {model}"
            else:
                x, y = df[f1], df[f2]
                xlabel, ylabel = f1, f2
                title = f"{f2} vs {f1} pentru {model}"
            ax2.scatter(x, y, color='black', s=50)
            ax2.plot(x, y, color='black', alpha=0.5, linestyle='-')
            ax2.set_xlabel(xlabel, color='black')
            ax2.set_ylabel(ylabel, color='black')
            ax2.set_title(title, color='black')
            ax2.grid(True, color='gray', alpha=0.2)
            for spine in ax2.spines.values():
                spine.set_color('black')
            ax2.tick_params(colors='black')
            plt.tight_layout()
            canvas.figure = fig2
            canvas._tkcanvas.pack_forget()
            canvas.get_tk_widget().pack_forget()
            canvas.__init__(fig2, master=plot_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

     
        if df is not None and f1 is not None and f2 is not None and model is not None:
            def toggle_swap():
                swap_state['swapped'] = not swap_state['swapped']
                recreate_plot()
            switch_button = tk.Button(
                plot_window,
                text="Inversează axe",
                command=toggle_swap,
                bg=COLORS["ACCENT"],
                fg=COLORS["BACKGROUND"],
                font=FONTS["BUTTON"]
            )
            switch_button.pack(pady=5)

     
        close_button = tk.Button(
            plot_window,
            text="Închide",
            command=plot_window.destroy,
            bg=COLORS["ACCENT"],
            fg=COLORS["BACKGROUND"],
            font=FONTS["BUTTON"]
        )
        close_button.pack(pady=10)
     
        plot_window.geometry("900x600")
    
        plot_window.update_idletasks()
        width = plot_window.winfo_width()
        height = plot_window.winfo_height()
        x = (plot_window.winfo_screenwidth() // 2) - (width // 2)
        y = (plot_window.winfo_screenheight() // 2) - (height // 2)
        plot_window.geometry(f'{width}x{height}+{x}+{y}')
        plot_window.focus_set()
        print("DEBUG: show_plot_in_tkinter a fost apelat și graficul ar trebui să fie vizibil într-o fereastră nouă.")

    def record_voice_command(self):
        try:
            import sounddevice as sd
            import numpy as np
            from scipy.io.wavfile import write
            import tempfile
            import os

            fs = 44100
            duration = 10
            print("Înregistrare comandă vocală...")
            audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
            sd.wait()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            write(temp_path, fs, audio)
            with open(temp_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ro"
                )
            text = transcription.text.lower()
            print(f"Comandă vocală detectată: {text}")

            def process_command():
                print("Text recunoscut pentru regex:", text)
           
                normalized_text = re.sub(r'\s+', ' ', text)
                print("Text normalizat:", normalized_text)
                patterns = [
                    r"cre[aă]ză\s+graf\w*\s+între\s+([\w\s]+?)\s+(?:și|si)\s+([\w\s]+?)\s+pentru\s+([\w\s]+)",
                    # variante mai permisive
                    r"grafic.*?([\w\s]+).*?(?:si|și)\s*([\w\s]+).*?pentru\s*([\w\s]+)",
                    r"grafic.*?pentru\s*([\w\s]+).*?(?:cu|între)\s*([\w\s]+)\s*(?:si|și)\s*([\w\s]+)",
                    r"cre[aă]ză.*?grafic.*?([\w\s]+).*?(?:si|și)\s*([\w\s]+).*?pentru\s*([\w\s]+)",
                    r"grafic.*?([\w\s]+).*?(?:si|și)\s*([\w\s]+).*?([\w\s]+)",
                    # variantele vechi
                    r"pentru ([\w\s]+) creeaza grafic cu ([\w\s]+) si ([\w\s]+)",
                    r"cre[aă]ză grafic (?:cu|între) ([\w\s]+) (?:și|si) ([\w\s]+) pentru ([\w\s]+)",
                    r"cre[aă]ză (?:un )?grafic (?:cu|între) ([\w\s]+) (?:și|si) ([\w\s]+) pentru ([\w\s]+)"
                ]
                found = False
                for pat in patterns:
                    print(f"Încerc pattern: {pat}")
                    match = re.search(pat, normalized_text)
                    if match:
                        print(f"Pattern potrivit: {pat}, grupuri: {match.groups()}")
                        if pat.startswith("pentru"):
                            model = match.group(1).strip().title()
                            feature1 = match.group(2).strip().replace(' ', '_').lower()
                            feature2 = match.group(3).strip().replace(' ', '_').lower()
                        else:
                            feature1 = match.group(1).strip().replace(' ', '_').lower()
                            feature2 = match.group(2).strip().replace(' ', '_').lower()
                            model = match.group(3).strip().title()
                        
                        feature_map = {
                            'energia_consumata': 'energy_consumed',
                            'energia_estimata': 'energy_consumed',
                            'energy_consumed': 'energy_consumed',
                            'durata_estimata_ore': 'durata_estimata_ore',
                            'durataestimataore': 'durata_estimata_ore',
                            'durataestimata_in_ore': 'durata_estimata_ore',
                            'durata_estimata_in_ore': 'durata_estimata_ore',
                            'durata_estimata_ori': 'durata_estimata_ore',
                            'cost_estimare': 'charging_cost',
                            'rata_incarcare': 'charging_rate',
                            'stare_incarcare_start': 'state_of_charge_start',
                            'stare_incarcare_end': 'state_of_charge_end',
                            'distanta': 'distance',
                        }
                        
                        def remove_diacritics(text):
                            return ''.join(
                                c for c in unicodedata.normalize('NFD', text)
                                if unicodedata.category(c) != 'Mn'
                            )
                        
                        def normalize_feature_name(text):
                            text = remove_diacritics(text)
                            for word in [' in ', ' între ', ' intre ', ' cu ', ' și ', ' si ', ' de ', ' la ', ' pe ', 'in_', 'în_', '_in_', '_în_', 'intre_', 'cu_', 'si_', 'și_']:
                                text = text.replace(word, ' ')
                            text = text.replace(' ', '_').replace('-', '_').lower()
                            while '__' in text:
                                text = text.replace('__', '_')
                            text = text.strip('_')
                            return text
                        
                        feature1 = normalize_feature_name(feature1)
                        feature2 = normalize_feature_name(feature2)
                        f1 = feature_map.get(feature1, feature1)
                        f2 = feature_map.get(feature2, feature2)
                        
                        print(f"Feature1 detectat (după normalizare și mapping): {f1}")
                        print(f"Feature2 detectat (după normalizare și mapping): {f2}")
                        
                        model_map = {
                            'bmw i3': 'BMW i3',
                            'pmw i3': 'BMW i3',
                            'bni3': 'BMW i3',
                            'bnv i3': 'BMW i3',
                            'bmp i3': 'BMW i3',
                            'bmw13': 'BMW i3',
                            'bmwi3': 'BMW i3',
                            'tesla model 3': 'Tesla Model 3',
                        }
                        model_key = model_map.get(model.lower(), model)
                        df = self.get_data_for_vehicle(self.current_user, model_key, self.id_token)
                        
                        print("Coloane disponibile:", df.columns)
                        print("Primele date:", df.head())
                        print("Număr de rânduri:", len(df))
                        
                        # am incercat embedding semantic in loc de mapping fix
                        available_columns = df.columns.tolist()
                        model_embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                        col_embeddings = model_embedder.encode(available_columns, convert_to_tensor=True)

                        spoken_features = [feature1, feature2]
                        translated = []
                        for feature in spoken_features:
                            feature_emb = model_embedder.encode(feature, convert_to_tensor=True)
                            scores = util.pytorch_cos_sim(feature_emb, col_embeddings)[0]
                            best_idx = scores.argmax().item()
                            best_score = scores[best_idx].item()
                            if best_score > 0.65:
                                translated.append(available_columns[best_idx])
                            else:
                                translated.append(feature)  # fallback

                        f1, f2 = translated
                        print(f"F1 semantic: {f1}, F2 semantic: {f2}")

                        if f1 in df.columns and f2 in df.columns:
                            import matplotlib.pyplot as plt
                            fig, ax = plt.subplots(figsize=(8, 4))
                            fig.patch.set_facecolor('white')
                            ax.set_facecolor('white')

                            scatter = ax.scatter(df[f1], df[f2], color='#B9EF17', s=50)
                            ax.plot(df[f1], df[f2], color='black', alpha=0.5, linestyle='-')

                            ax.set_xlabel(f1, color='black')
                            ax.set_ylabel(f2, color='black')
                            ax.set_title(f"{f2} vs {f1} pentru {model}", color='black')
                            ax.grid(True, color='gray', alpha=0.2)

                            for spine in ax.spines.values():
                                spine.set_color('black')
                            ax.tick_params(colors='black')
                            plt.tight_layout()
                            self.show_plot_in_tkinter(fig, df, f1, f2, model)
                        else:
                            messagebox.showerror("Eroare", f"Nu s-au găsit coloanele {f1} și {f2} în datele pentru {model}.")
                        os.remove(temp_path)
                        found = True
                        return
                
                if not found:
                    messagebox.showerror("Eroare", "Nu am putut interpreta comanda vocală pentru generarea graficului.")
                
                if "deschide" in text and "durata" in text and "incarcare" in text:
                    self.estimare_durata_incarcare()
                elif "deschide" in text and "cost" in text and "incarcare" in text:
                    self.estimare_cost()
                elif "deschide" in text and "profil" in text and "vehicul" in text:
                    self.profil_vehicul()
                elif "deschide" in text and "km" in text and "ramase" in text:
                    self.estimare_h_km_ramase()
            
           
            self.root.after(0, process_command)
            
        except Exception as e:
            print(f"Eroare la procesarea comenzii vocale: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Eroare", f"Nu s-a putut procesa comanda vocală: {str(e)}"))
        finally:
            self.is_recording = False

    def on_child_close(self, child_window):
        """Gestionează închiderea ferestrei copil"""
        child_window.destroy()
        self.root.deiconify() 

    def get_first_vehicle_for_user(self):
        sanitized_email = self.current_user.replace('.', '_')
        vehicles_ref = db.child("istoric_date").child(sanitized_email)
        vehicles = vehicles_ref.get(token=self.id_token)
        if vehicles.each():
            return vehicles.each()[0].key()
        return None

    def get_user_vehicles(self):
        sanitized_email = self.current_user.replace('.', '_')
        try:
            vehicles_ref = db.child("vehicule").child(sanitized_email)
            vehicles = vehicles_ref.get(token=self.id_token)
            models = []
            if vehicles.each():
                for v in vehicles.each():
                    val = v.val()
                    if isinstance(val, dict) and 'model' in val:
                        models.append(val['model'])
            return models
        except Exception as e:
            print(f"Eroare la extragerea vehiculelor: {e}")
        return []

    def create_vehicle_selector(self):
        vehicles = self.get_user_vehicles()
        if not vehicles:
            return
        self.selected_vehicle = tk.StringVar()
        self.selected_vehicle.set(vehicles[0])
        def on_vehicle_change(*args):
            self.show_vehicle_image(self.selected_vehicle.get())
            self.update_scheduled_charging_widget()
        vehicle_menu = tk.OptionMenu(self.root, self.selected_vehicle, *vehicles, command=lambda _: on_vehicle_change())
        vehicle_menu.config(font=FONTS["BUTTON"], bg=COLORS["ACCENT"], fg=COLORS["BACKGROUND"], width=20)
        vehicle_menu.place(x=830, y=220)
        
        self.selected_vehicle.trace_add('write', lambda *args: on_vehicle_change())

    def show_vehicle_image(self, model):
        if not model:
            return
        img_name = f"vehicul_{model.lower().replace(' ', '_').replace('-', '_')}.png"
        img_path = os.path.join(self.images_dir, img_name)
        if os.path.exists(img_path):
            img = Image.open(img_path)
            img = img.resize((350, 350), Image.Resampling.LANCZOS)
            self.vehicle_img = ImageTk.PhotoImage(img)
            if hasattr(self, 'vehicle_img_label'):
                self.vehicle_img_label.config(image=self.vehicle_img)
            else:
                self.vehicle_img_label = tk.Label(self.root, image=self.vehicle_img, bg=COLORS["BACKGROUND"])
                self.vehicle_img_label.place(x=385, y=220)
        else:
            print(f"Imaginea pentru {model} nu a fost găsită la {img_path}")

    def analyze_charging_patterns(self, user_email, model, token):
        """Analizează pattern-urile de încărcare pentru un vehicul specific"""
        try:
            df = self.get_data_for_vehicle(user_email, model, token)
            if df.empty:
                return None

           
            if 'timestamp' not in df.columns:
                print(f"Nu există coloana 'timestamp' în datele pentru {model}")
                return None
           
            df = df[df['timestamp'].notnull()]
            if df.empty:
                print(f"Nu există rânduri cu timestamp valid pentru {model}")
                return None

            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
           
            df['hour'] = df['timestamp'].dt.hour
            
            
            charging_frequency = df['hour'].value_counts().sort_index()
            
           
            peak_hours = range(8, 21)
            off_peak_hours = list(range(22, 24)) + list(range(0, 7))
            
            
            peak_charging = charging_frequency[charging_frequency.index.isin(peak_hours)].sum()
            total_charging = charging_frequency.sum()
            peak_percentage = (peak_charging / total_charging) * 100 if total_charging > 0 else 0
            
            return {
                'peak_percentage': peak_percentage,
                'charging_frequency': charging_frequency,
                'peak_hours': peak_hours,
                'off_peak_hours': off_peak_hours
            }
        except Exception as e:
            print(f"Eroare la analiza pattern-urilor de încărcare: {str(e)}")
            return None

    def get_optimal_charging_time(self, patterns):
        """Determină ora optimă de încărcare bazată pe pattern-uri"""
        if not patterns:
            return None
            
        
        off_peak_frequency = patterns['charging_frequency'][patterns['charging_frequency'].index.isin(patterns['off_peak_hours'])]
        if not off_peak_frequency.empty:
            optimal_hour = off_peak_frequency.idxmin()
            return optimal_hour
        return 22  

    def get_cheapest_available_location(self, scheduled, date_str, hour):
        
        import pandas as pd
        csv_path = os.path.join(self.current_dir, 'ev_charging_synthetic_data.csv')
        df = pd.read_csv(csv_path)
        location_cols = [col for col in df.columns if col.startswith("Charging Station Location_")]
        df['Location'] = df[location_cols].idxmax(axis=1).str.replace("Charging Station Location_", "")
        cost_mediu_pe_locatie = df.groupby("Location")["Charging Cost (USD)"].mean().to_dict()
        
        occupied = set()
        for p in scheduled:
            if p.get('data') == date_str and p.get('ora', '').startswith(f"{hour:02d}"):
                occupied.add(p.get('locatie'))
        available = [loc for loc in cost_mediu_pe_locatie if loc not in occupied]
        if not available:
            return None, None
        cheapest_loc = min(available, key=lambda loc: cost_mediu_pe_locatie[loc] if not pd.isna(cost_mediu_pe_locatie[loc]) else float('inf'))
        return cheapest_loc, cost_mediu_pe_locatie[cheapest_loc]

    def save_station_booking(self, locatie, data, ora, programare_id, programare, token):
       
        def operation():
            db.child("programari_statii").child(locatie).child(data).child(ora).child(programare_id).set(programare, token=token)
        self.safe_firebase_operation(operation)

    def update_station_booking_status(self, locatie, data, ora, programare_id, status, token):
       
        def operation():
            db.child("programari_statii").child(locatie).child(data).child(ora).child(programare_id).update({'status': status}, token=token)
        self.safe_firebase_operation(operation)

    def is_station_slot_free(self, locatie, data, ora, token):
       
        def operation():
            bookings = db.child("programari_statii").child(locatie).child(data).child(ora).get(token=token)
            if bookings.each():
                for b in bookings.each():
                    val = b.val()
                    if val.get('status') not in ['anulata']:
                        return False
            return True
        return self.safe_firebase_operation(operation)

    def optimizare_incarcare(self):
        import pandas as pd
       
        try:
            selected_model = self.selected_vehicle.get()
            if not selected_model:
                messagebox.showerror("Eroare", "Vă rugăm să selectați un vehicul.")
                return
            patterns = self.analyze_charging_patterns(self.current_user, selected_model, self.id_token)
            if not patterns:
                messagebox.showerror("Eroare", "Nu s-au găsit date suficiente pentru analiză.")
                return
            optimal_hour = self.get_optimal_charging_time(patterns)
            from datetime import datetime, timedelta
            now = datetime.now()
            if now.hour < optimal_hour:
                date_str = now.strftime("%Y-%m-%d")
            else:
                date_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
            scheduled = self.get_scheduled_charging(self.current_user, selected_model, self.id_token)

            
            found = False
            for offset in range(24):
                hour = (optimal_hour + offset) % 24
                location, cost = self.get_cheapest_available_location(scheduled, date_str, hour)
                if location and self.is_station_slot_free(location, date_str, f"{hour:02d}:00", self.id_token):
                    found = True
                    chosen_hour = hour
                    chosen_location = location
                    chosen_cost = cost
                    break
            if not found:
                messagebox.showerror("Eroare", "Nu există nicio locație disponibilă la nicio oră pentru ziua selectată.")
                return

           
            import uuid
            try:
               
                existing = [
                    p for p in self.get_scheduled_charging(self.current_user, selected_model, self.id_token)
                    if p.get('data') == date_str and p.get('ora') == f"{chosen_hour:02d}:00" and p.get('status') != 'anulata' and p.get('status') != 'confirmat'
                ]
                if existing:
                    messagebox.showerror(
                        "Programare existentă",
                        "Există deja o programare pentru acest vehicul la această dată și oră!"
                    )
                    return
                programare = {
                    'data': date_str,
                    'ora': f"{chosen_hour:02d}:00",
                    'locatie': chosen_location,
                    'status': 'programata',
                    'created_at': now.strftime("%Y-%m-%d %H:%M:%S")
                }
                sanitized_email = self.current_user.replace('.', '_')
                programari_ref = db.child("programari_incarcare").child(sanitized_email).child(selected_model)
                programare_id = str(uuid.uuid4())
                programari_ref.child(programare_id).set(programare, token=self.id_token)
              
                self.save_station_booking(chosen_location, date_str, f"{chosen_hour:02d}:00", programare_id, programare, self.id_token)
                self.update_scheduled_charging_widget()
            except Exception as e:
                messagebox.showerror("Eroare la salvare", str(e))
                return
            
            df_hist = self.get_data_for_vehicle(self.current_user, selected_model, self.id_token)
            if 'timestamp' in df_hist.columns:
                df_hist['timestamp'] = pd.to_datetime(df_hist['timestamp'])
                df_hist['hour'] = df_hist['timestamp'].dt.hour
                most_freq_hour = df_hist['hour'].mode()[0] if not df_hist['hour'].empty else None
            else:
                most_freq_hour = None
            total_cost = 0.0
            if 'hour' in df_hist.columns and 'Charging Cost (USD)' in df_hist.columns:
                total_cost += df_hist[df_hist['hour'] == most_freq_hour]['Charging Cost (USD)'].sum()
            programari = self.get_scheduled_charging(self.current_user, selected_model, self.id_token)
            for p in programari:
                if p.get('status') == 'confirmat' and p.get('ora') and p.get('data') and p.get('locatie'):
                    try:
                        ora_int = int(p.get('ora').split(':')[0])
                        if ora_int == most_freq_hour:
                            avg_cost = self.get_avg_cost_per_location().get(p.get('locatie'), 0)
                            if avg_cost and not pd.isna(avg_cost):
                                total_cost += avg_cost
                    except Exception:
                        pass
            import pandas as pd
            explanation_window = tk.Toplevel(self.root)
            explanation_window.title("Optimizare Încărcare")
            explanation_window.geometry("600x400")
            explanation_window.configure(bg=COLORS["BACKGROUND"])
            explanation_window.transient(self.root)
            explanation_window.grab_set()
            title_label = tk.Label(
                explanation_window,
                text="Optimizare Încărcare",
                font=FONTS["TITLE"],
                bg=COLORS["BACKGROUND"],
                fg=COLORS["ACCENT"]
            )
            title_label.pack(pady=20)
            explanation_text = f"""
Locație selectată: {chosen_location}
Cost mediu: ${chosen_cost:.2f} per încărcare

Explicație:
• Ora selectată: {chosen_hour:02d}:00
• Data programării: {date_str}
• Locația a fost aleasă pentru că are cel mai mic cost mediu per încărcare disponibil
• Locația este disponibilă la ora și data selectată
• Costul mediu este calculat pe baza istoricului de încărcări

--- Statistici ---
Perioada cea mai frecventă de încărcare: {most_freq_hour if most_freq_hour is not None else 'N/A'}:00
Cost total cheltuit în acest interval (istoric + confirmate): ${total_cost:.2f}
"""
            explanation_label = tk.Label(
                explanation_window,
                text=explanation_text,
                font=FONTS["INFO"],
                bg=COLORS["BACKGROUND"],
                fg=COLORS["TEXT"],
                justify="left"
            )
            explanation_label.pack(pady=10, padx=20)
            close_button = tk.Button(
                explanation_window,
                text="OK",
                command=explanation_window.destroy,
                font=FONTS["BUTTON"],
                bg=COLORS["ACCENT"],
                fg=COLORS["BACKGROUND"]
            )
            close_button.pack(pady=20)
            explanation_window.update_idletasks()
            width = explanation_window.winfo_width()
            height = explanation_window.winfo_height()
            x = (explanation_window.winfo_screenwidth() // 2) - (width // 2)
            y = (explanation_window.winfo_screenheight() // 2) - (height // 2)
            explanation_window.geometry(f'{width}x{height}+{x}+{y}')
            explanation_window.lift()
            explanation_window.focus_force()
        except Exception as e:
            messagebox.showerror("Eroare", f"Nu s-a putut genera sugestia de optimizare: {str(e)}")

    def get_available_locations(self, user_email, model, token):
       
        df = self.get_data_for_vehicle(user_email, model, token)
        if 'tip_incarcator' in df.columns:
            return sorted(df['tip_incarcator'].dropna().unique().tolist())
        return []

    def get_station_locations_from_csv(self):
       
        csv_path = os.path.join(self.current_dir, 'ev_charging_synthetic_data.csv')
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
        locations = []
        for col in header:
            if col.startswith('Charging Station Location_'):
                loc = col.replace('Charging Station Location_', '').replace('_', ' ')
                locations.append(loc)
        return locations

    def schedule_charging(self, user_email, model, token, selected_location=None):
        """Agentul decide și programează automat o încărcare optimă, salvează în Firebase și notifică utilizatorul"""
        import uuid
        from datetime import datetime, timedelta
       
        patterns = self.analyze_charging_patterns(user_email, model, token)
        if not patterns:
            messagebox.showerror("Eroare", "Nu s-au găsit date suficiente pentru analiză.")
            return
        optimal_hour = self.get_optimal_charging_time(patterns)
       
        locations = self.get_station_locations_from_csv()
        if not locations:
            messagebox.showerror("Eroare", "Nu există locații disponibile pentru programare.")
            return
       
        location = selected_location if selected_location else locations[0]
       
        now = datetime.now()
        if now.hour < optimal_hour:
            date_str = now.strftime("%Y-%m-%d")
        else:
            date_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        programare = {
            'data': date_str,
            'ora': f"{optimal_hour:02d}:00",
            'locatie': location,
            'status': 'programata',
            'created_at': now.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        sanitized_email = user_email.replace('.', '_')
        programari_ref = db.child("programari_incarcare").child(sanitized_email).child(model)
        programare_id = str(uuid.uuid4())
        programari_ref.child(programare_id).set(programare, token=token)
        
        self.update_scheduled_charging_widget()
        messagebox.showinfo(
            "Programare creată",
            f"Încărcarea a fost programată automat pentru {date_str}, ora {programare['ora']}, locație: {location}."
        )
       
        self.update_scheduled_charging_widget()

    def get_scheduled_charging(self, user_email, model, token):
        
        def operation():
            sanitized_email = user_email.replace('.', '_')
            programari_ref = db.child("programari_incarcare").child(sanitized_email).child(model)
            programari = programari_ref.get(token=token)
            result = []
            if programari.each():
                for p in programari.each():
                    val = p.val()
                    val['id'] = p.key()
                    result.append(val)
            # Sortează după dată și oră
            result.sort(key=lambda x: (x.get('data', ''), x.get('ora', '')))
            print(f"[DEBUG] get_scheduled_charging pentru {user_email}, {model}: {result}")
            return result
        return self.safe_firebase_operation(operation)

    def create_scheduled_charging_widget(self):
       
        if hasattr(self, 'scheduled_charging_frame'):
            self.scheduled_charging_frame.destroy()
        self.scheduled_charging_frame = tk.Frame(self.root, bg=COLORS["SECONDARY_BG"])
        self.scheduled_charging_frame.place(x=250, y=600, width=650, height=60)
        title = tk.Label(
            self.scheduled_charging_frame,
            text="Programări încărcare viitoare:",
            font=FONTS["INFO"],
            bg=COLORS["INPUT_BG"],
            fg=COLORS["TEXT"]
        )
        title.pack(anchor="w", padx=10, pady=2)
        
      
        list_frame = tk.Frame(self.scheduled_charging_frame, bg=COLORS["SECONDARY_BG"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=2)
        
        self.scheduled_charging_list = tk.Listbox(
            list_frame,
            font=FONTS["USER"],
            bg=COLORS["BACKGROUND"],
            fg=COLORS["TEXT"],
            height=2,
            width=50
        )
        self.scheduled_charging_list.pack(side="left", fill="both", expand=True)
        
      
        self.cancel_button = tk.Button(
            list_frame,
            text="Anulează",
            font=FONTS["BUTTON"],
            bg=COLORS["ACCENT"],
            fg=COLORS["BACKGROUND"],
            command=self.cancel_scheduled_charging
        )
        self.cancel_button.pack(side="right", padx=5)
        
        self.update_scheduled_charging_widget()

    def update_scheduled_charging_widget(self):
        import pandas as pd
        
        if not hasattr(self, 'scheduled_charging_list'):
            return
        if not hasattr(self, 'selected_vehicle') or not self.selected_vehicle.get():
            vehicles = self.get_user_vehicles()
            if vehicles:
                self.selected_vehicle = tk.StringVar()
                self.selected_vehicle.set(vehicles[0])
                print(f"[DEBUG] Setez model implicit: {vehicles[0]}")
            else:
                print("[DEBUG] Nu există vehicule pentru utilizator!")
                return
        selected_model = self.selected_vehicle.get()
        if not selected_model:
            print("[DEBUG] Nu există model selectat după forțare!")
            return
        programari = self.get_scheduled_charging(self.current_user, selected_model, self.id_token)
        print(f"[DEBUG] update_scheduled_charging_widget programari: {programari}")
        self.scheduled_charging_list.delete(0, tk.END)
        if hasattr(self, 'confirm_button'):
            self.confirm_button.destroy()
        if programari:
            programari.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            p = programari[0]
            print(f"[DEBUG] Programare afișată: {p}")
            self.scheduled_charging_list.insert(
                tk.END,
                f"{p.get('data', '')} {p.get('ora', '')} | {p.get('locatie', '')} | {p.get('status', '')}"
            )
            print('Listbox size:', self.scheduled_charging_list.size())
            if p.get('status') == 'programata':
                def on_confirmed():
                    sanitized_email = self.current_user.replace('.', '_')
                    db.child("programari_incarcare").child(sanitized_email).child(selected_model).child(p['id']).update({'status': 'confirmat'}, token=self.id_token)
                    
                    self.update_station_booking_status(p['locatie'], p['data'], p['ora'], p['id'], 'confirmat', self.id_token)
                    self.update_scheduled_charging_widget()
                    messagebox.showinfo("Succes", "Încărcarea a fost confirmată!")
                self.confirm_button = tk.Button(
                    self.scheduled_charging_list.master,
                    text="Confirmat",
                    font=FONTS["BUTTON"],
                    bg=COLORS["ACCENT"],
                    fg=COLORS["BACKGROUND"],
                    command=on_confirmed
                )
                self.confirm_button.pack(side="right", padx=5)
        else:
            print("[DEBUG] Nu există programări de afișat!")

    def cancel_scheduled_charging(self):
        
        selected_model = self.selected_vehicle.get() if hasattr(self, 'selected_vehicle') else None
        if not selected_model:
            return
        programari = self.get_scheduled_charging(self.current_user, selected_model, self.id_token)
        if not programari:
            return
        programari.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        ultima_programare = programari[0]
        if messagebox.askyesno("Confirmare anulare", "Sigur doriți să anulați această programare?"):
            sanitized_email = self.current_user.replace('.', '_')
            db.child("programari_incarcare").child(sanitized_email).child(selected_model).child(ultima_programare['id']).update({'status': 'anulata'}, token=self.id_token)
           
            self.update_station_booking_status(ultima_programare['locatie'], ultima_programare['data'], ultima_programare['ora'], ultima_programare['id'], 'anulata', self.id_token)
            self.update_scheduled_charging_widget()
            messagebox.showinfo("Succes", "Programarea a fost anulată cu succes (status schimbat în 'anulata').")

    def programare_incarcare_agent(self):
        
        selected_model = self.selected_vehicle.get() if hasattr(self, 'selected_vehicle') else None
        if not selected_model:
            messagebox.showerror("Eroare", "Vă rugăm să selectați un vehicul.")
            return
        locations = self.get_station_locations_from_csv()
        if not locations:
            messagebox.showerror("Eroare", "Nu există locații disponibile pentru programare.")
            return
        avg_cost = self.get_avg_cost_per_location()
        hours = [f"{h:02d}:00" for h in range(24)]
        top = tk.Toplevel(self.root)
        top.title("Programează încărcare")
        top.geometry("420x300")
        top.configure(bg=COLORS["BACKGROUND"])
        label = tk.Label(top, text="Alege locația de încărcare:", font=FONTS["INFO"], bg=COLORS["BACKGROUND"], fg=COLORS["ACCENT"])
        label.pack(pady=(20, 5))
        location_var = tk.StringVar(value=locations[0])
        dropdown = tk.OptionMenu(top, location_var, *locations)
        dropdown.config(font=FONTS["BUTTON"], bg=COLORS["ACCENT"], fg=COLORS["BACKGROUND"], width=25)
        dropdown.pack(pady=5)
        hour_label = tk.Label(top, text="Alege ora de încărcare:", font=FONTS["INFO"], bg=COLORS["BACKGROUND"], fg=COLORS["ACCENT"])
        hour_label.pack(pady=(10, 5))
        hour_var = tk.StringVar(value=hours[22])
        hour_dropdown = tk.OptionMenu(top, hour_var, *hours)
        hour_dropdown.config(font=FONTS["BUTTON"], bg=COLORS["ACCENT"], fg=COLORS["BACKGROUND"], width=10)
        hour_dropdown.pack(pady=5)
        cost_label = tk.Label(top, text="", font=FONTS["INFO"], bg=COLORS["BACKGROUND"], fg=COLORS["TEXT"])
        cost_label.pack(pady=(10, 5))
        def update_cost_label(*args):
            loc = location_var.get()
            cost = avg_cost.get(loc, float('inf'))
            if pd.isna(cost) or cost == float('inf'):
                cost_label.config(text="Cost mediu: N/A")
            else:
                cost_label.config(text=f"Cost mediu: ${cost:.2f} per încărcare")
        location_var.trace_add('write', update_cost_label)
        update_cost_label()
        def on_confirm():
            loc = location_var.get()
            ora = hour_var.get()
            from datetime import datetime
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            
            existing = [
                p for p in self.get_scheduled_charging(self.current_user, selected_model, self.id_token)
                if p.get('data') == date_str and p.get('ora') == ora and p.get('status') != 'anulata'
            ]
            if existing:
                messagebox.showerror(
                    "Programare existentă",
                    "Există deja o programare pentru acest vehicul la această dată și oră!"
                )
                return
           
            if not self.is_station_slot_free(loc, date_str, ora, self.id_token):
                messagebox.showerror(
                    "Stație ocupată",
                    f"La stația {loc}, la data {date_str} ora {ora} există deja o programare!"
                )
                return
            import uuid
            try:
                programare = {
                    'data': date_str,
                    'ora': ora,
                    'locatie': loc,
                    'status': 'programata',
                    'created_at': now.strftime("%Y-%m-%d %H:%M:%S")
                }
                sanitized_email = self.current_user.replace('.', '_')
                programari_ref = db.child("programari_incarcare").child(sanitized_email).child(selected_model)
                programare_id = str(uuid.uuid4())
                programari_ref.child(programare_id).set(programare, token=self.id_token)
               
                self.save_station_booking(loc, date_str, ora, programare_id, programare, self.id_token)
                self.update_scheduled_charging_widget()
                messagebox.showinfo(
                    "Programare creată",
                    f"Încărcarea a fost programată pentru {date_str}, ora {ora}, locație: {loc}."
                )
                top.destroy()
            except Exception as e:
                messagebox.showerror("Eroare la salvare", str(e))
        confirm_btn = tk.Button(top, text="Programează", command=on_confirm, font=FONTS["BUTTON"], bg=COLORS["ACCENT"], fg=COLORS["BACKGROUND"])
        confirm_btn.pack(pady=15)
        top.update_idletasks()
        width = top.winfo_width()
        height = top.winfo_height()
        x = (top.winfo_screenwidth() // 2) - (width // 2)
        y = (top.winfo_screenheight() // 2) - (height // 2)
        top.geometry(f'{width}x{height}+{x}+{y}')

    def get_avg_cost_per_location(self):
        
        import pandas as pd
        csv_path = os.path.join(self.current_dir, 'ev_charging_synthetic_data.csv')
        df = pd.read_csv(csv_path)
        location_cols = [col for col in df.columns if col.startswith("Charging Station Location_")]
        df['Location'] = df[location_cols].idxmax(axis=1).str.replace("Charging Station Location_", "")
        cost_mediu_pe_locatie = df.groupby("Location")["Charging Cost (USD)"].mean().to_dict()
        return cost_mediu_pe_locatie

if __name__ == "__main__":
    root = tk.Tk()
    app = MenuInterface(root, "test@example.com", "password123")
    root.mainloop()
