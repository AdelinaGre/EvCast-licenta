import tkinter as tk
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
from authentification_config import db
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import unicodedata
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import util

# Importuri relative sau absolute în funcție de context
try:
    from .users_signing import UserSigning
    from .vehicle_profile import VehicleProfile
except ImportError:
    from users_signing import UserSigning
    from vehicle_profile import VehicleProfile

# Constante pentru stilizare
COLORS = {
    "BACKGROUND": "#0D0D0D",
    "SECONDARY_BG": "#1A1C1A",
    "ACCENT": "#B9EF17",
    "TEXT": "white",
    "HOVER": "#D4FF3F"
}

FONTS = {
    "TITLE": ("Roboto", 20, "bold"),
    "APP_NAME": ("Roboto", 24, "bold"),
    "USER": ("Roboto", 12),
    "BUTTON": ("Roboto", 12),
    "INFO": ("Roboto", 10)
}

class MenuInterface:
    def __init__(self, root, current_user,id_token):
        self.root = root
        self.current_user = current_user
        self.id_token = id_token
        self.root.title("Menu")
        self.root.geometry("1100x700")
        
        # Inițializăm variabilele pentru imagini
        self.background_image = None
        self.logo_image = None
        self.power_image = None
        
        # Inițializare client OpenAI pentru comenzi vocale
        load_dotenv()
        openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=openai_api_key)
        
        # Variabile pentru înregistrare vocală
        self.is_recording = False
        self.recording_thread = None
        
        # Frame pentru grafic
        self.plot_frame = tk.Frame(self.root, bg=COLORS["BACKGROUND"])
        self.plot_frame.place(x=400, y=220, width=650, height=400)
        
        # Obține calea către directorul rădăcină al proiectului
        self.current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.images_dir = os.path.join(self.current_dir, "images")
        
        # Inițializăm datele curente
        self.current_data = {
            "time": None,
            "date": None,
            "time_of_day": None,
            "day_of_week": None,
            "temperature": None
        }
        
        # Încărcăm datele salvate dacă există
        self.load_saved_data()
        
        # Actualizăm datele curente
        # self.update_current_data()
        
        # Configurăm actualizarea automată a datelor
        self.root.after(60000, self.update_current_data)  # Actualizare la fiecare minut
        
        self.user_signing = UserSigning()
        self.create_widgets()             # <- APELĂM ÎNTÂI widgets
        self.update_current_data() 
        # Dropdown pentru selectarea vehiculului și afișarea imaginii
        self.create_vehicle_selector()
        # Afișează imaginea primului vehicul pentru utilizatorul logat
        first_vehicle = self.get_first_vehicle_for_user()
        self.show_vehicle_image(first_vehicle)

    def update_current_data(self):
        """Actualizează datele curente"""
        now = datetime.now()
        
        # Actualizăm datele curente
        self.current_data.update({
            "time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%d/%m/%Y"),
            "time_of_day": now.hour // 6,  # 0=noapte, 1=dimineață, 2=zi, 3=seară
            "day_of_week": now.weekday(),  # 0=Luni, 6=Duminică
        })
        
        # Actualizăm temperatura
        self.update_temperature()
        
        # Actualizăm interfața
        self.update_info_display()
        
        # Salvăm datele curente
        self.save_current_data()
        
        # Programăm următoarea actualizare
        self.root.after(60000, self.update_current_data)

    def update_temperature(self):
        """Actualizează temperatura folosind OpenWeatherMap API"""
        try:
            # print("\n=== Începere actualizare temperatură ===")
            lat = 44.4268
            lon = 26.1025
            openweather_api_key = os.getenv("OPENWEATHER_API_KEY")
            api_key = openweather_api_key
            url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
            # print(f"URL API: {url}")
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
        # print("=== Finalizare actualizare temperatură ===\n")

    def save_current_data(self):
        """Salvează datele curente în fișier"""
        try:
            data_file = os.path.join(self.current_dir, "current_data.json")
            with open(data_file, 'w') as f:
                json.dump(self.current_data, f)
        except Exception as e:
            print(f"Eroare la salvarea datelor: {str(e)}")

    def load_saved_data(self):
        """Încarcă datele salvate din fișier"""
        try:
            data_file = os.path.join(self.current_dir, "current_data.json")
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    self.current_data = json.load(f)
        except Exception as e:
            print(f"Eroare la încărcarea datelor: {str(e)}")

    def create_info_display(self):
        """Creează afișajul pentru informații curente, fiecare în container separat, sub logo, aliniate la stânga ca butoanele"""
        # Container orizontal pentru toate info-box-urile
        self.top_info_row = tk.Frame(self.root, bg=COLORS["BACKGROUND"])
        self.top_info_row.place(x=50, y=100, height=80)  # x=50 ca butoanele, fără relwidth

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
                fg=COLORS["ACCENT"],
                bg=COLORS["SECONDARY_BG"]
            )
            title.pack(pady=(5, 0))

            value_label = tk.Label(
                container,
                text="",
                font=("Roboto", 13, "bold"),
                fg=COLORS["TEXT"],
                bg=COLORS["SECONDARY_BG"]
            )
            value_label.pack()
            self.info_labels[key] = value_label


    def update_info_display(self):
        """Actualizează afișajul cu informațiile curente, cu verificare robustă a existenței label-urilor"""
        if hasattr(self, 'info_labels'):
            # Actualizăm ora și data
            if "time" in self.info_labels and self.info_labels["time"].winfo_exists():
                self.info_labels["time"].config(text=self.current_data["time"])
            if "date" in self.info_labels and self.info_labels["date"].winfo_exists():
                self.info_labels["date"].config(text=self.current_data["date"])
            # Actualizăm perioada zilei
            time_of_day_map = {0: "Noapte", 1: "Dimineață", 2: "Zi", 3: "Seară"}
            if "time_of_day" in self.info_labels and self.info_labels["time_of_day"].winfo_exists():
                self.info_labels["time_of_day"].config(
                    text=time_of_day_map.get(self.current_data["time_of_day"], "Necunoscut")
                )
            # Actualizăm ziua săptămânii
            day_of_week_map = {
                0: "Luni", 1: "Marți", 2: "Miercuri", 3: "Joi",
                4: "Vineri", 5: "Sâmbătă", 6: "Duminică"
            }
            if "day_of_week" in self.info_labels and self.info_labels["day_of_week"].winfo_exists():
                self.info_labels["day_of_week"].config(
                    text=day_of_week_map.get(self.current_data["day_of_week"], "Necunoscut")
                )
            # Actualizăm temperatura
            temp = self.current_data["temperature"]
            temp_text = f"{temp}°C" if temp is not None else "N/A"
            if "temperature" in self.info_labels and self.info_labels["temperature"].winfo_exists():
                self.info_labels["temperature"].config(text=temp_text)

    def setup_background(self):
        """Configurează imaginea de fundal"""
        try:
            bg_path = os.path.join(self.images_dir, "green_wave.jpeg")
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
        """Creează header-ul aplicației"""
        try:
            logo_path = os.path.join(self.images_dir, "plugin.png")
            if os.path.exists(logo_path):
                logo_image = Image.open(logo_path)
                self.logo_image = ImageTk.PhotoImage(logo_image)
                logo_label = tk.Label(self.root, image=self.logo_image, bg=COLORS["BACKGROUND"])
                logo_label.place(x=30, y=30)
            else:
                print(f"Nu s-a găsit logo-ul la calea {logo_path}")
        except Exception as e:
            print(f"Eroare la încărcarea logo-ului: {str(e)}")

        # Numele aplicației
        self.label_app_name = tk.Label(
            self.root, 
            text="EVcast", 
            font=FONTS["APP_NAME"], 
            bg=COLORS["BACKGROUND"], 
            fg=COLORS["TEXT"]
        )
        self.label_app_name.place(x=110, y=41)

        # Utilizator curent
        self.label_user = tk.Label(
            self.root, 
            text=f"Utilizator: {self.current_user}", 
            font=FONTS["USER"],
            bg=COLORS["BACKGROUND"], 
            fg=COLORS["TEXT"]
        )
        self.label_user.place(x=700, y=30)

    def create_buttons(self):
        """Creează butoanele"""
        def on_enter(e): e.widget['background'] = COLORS["HOVER"]
        def on_leave(e): e.widget['background'] = COLORS["ACCENT"]

        buttons = [
            ("🚗 Profil Vehicul", self.profil_vehicul, 220),
            ("💰 Estimare Cost Încărcare", self.estimare_cost, 260),
            ("💰 Estimare Durata Încărcare", self.estimare_durata_incarcare, 300),
            ("⏱️ Estimare Km si H ramase", self.estimare_h_km_ramase, 340)
        ]

        for text, command, y_pos in buttons:
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
            button.place(x=50, y=y_pos, width=270, height=30)
            button.bind("<Enter>", on_enter)
            button.bind("<Leave>", on_leave)

    def create_widgets(self):
        """Creează toate widget-urile interfeței"""
        # Setăm fundalul
        self.setup_background()
        
        # Titlu
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
        self.update_info_display()  # Actualizăm afișajul inițial
        self.update_time_label()    # Pornește actualizarea orei în timp real
        
        # Adăugăm butonul pentru comandă vocală
        voice_button = tk.Button(
            self.root,
            text="🎤 Comandă Vocală",
            font=FONTS["BUTTON"],
            bg=COLORS["ACCENT"],
            fg=COLORS["BACKGROUND"],
            command=self.toggle_voice_command
        )
        voice_button.place(x=935, y=70)

    def update_time_label(self):
        """Actualizează doar ora în timp real (secundă cu secundă), cu verificare robustă"""
        if "time" in self.info_labels and self.info_labels["time"].winfo_exists():
            from datetime import datetime
            now = datetime.now()
            time_str = now.strftime("%H:%M:%S")
            self.info_labels["time"].config(text=time_str)
        self.root.after(1000, self.update_time_label)

    def profil_vehicul(self):
        """Deschide fereastra de profil vehicul"""
        # Ascundem toate widget-urile curente
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Creăm interfața de profil vehicul în aceeași fereastră
        VehicleProfile(self.root, self.current_user, self.id_token)

    def estimare_durata_incarcare(self):
        """Deschide fereastra de estimare durată încărcare"""
        # Ascundem toate widget-urile curente
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Creăm interfața de estimare durată în aceeași fereastră
        from charging_duration import ChargingDuration
        ChargingDuration(self.root, self.current_user, self.id_token)

    def estimare_cost(self):
        """Deschide fereastra de estimare cost încărcare"""
        for widget in self.root.winfo_children():
            widget.destroy()
        from charging_cost import ChargingCost
        ChargingCost(self.root, self.current_user, self.id_token)

    def estimare_h_km_ramase(self):
        """Deschide fereastra de estimare km și ore rămase"""
        # Ascundem toate widget-urile curente
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Creăm interfața de estimare km și ore rămase în aceeași fereastră
        from estimate_km_hours_ramase import create_estimation_interface
        create_estimation_interface(self.root)

    def toggle_voice_command(self):
        """Comută între pornirea și oprirea înregistrării pentru comandă vocală"""
        if not self.is_recording:
            self.start_voice_recording()
        else:
            self.stop_voice_recording()

    def start_voice_recording(self):
        """Pornește înregistrarea pentru comandă vocală"""
        self.is_recording = True
        self.recording_thread = threading.Thread(target=self.record_voice_command)
        self.recording_thread.daemon = True
        self.recording_thread.start()

    def stop_voice_recording(self):
        """Oprește înregistrarea pentru comandă vocală"""
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
                features = session.val().get('features', {})
                derived = session.val().get('derived_features', {})
                predictii = session.val().get('predictii', {})
                row.update(features)
                row.update(derived)
                row.update(predictii)
                data.append(row)
        else:
            print("Nu există sesiuni pentru acest model și utilizator.")
        return pd.DataFrame(data)

    def show_plot_in_tkinter(self, fig, df=None, f1=None, f2=None, model=None):
        # Creează o fereastră nouă pentru grafic
        plot_window = tk.Toplevel(self.root)
        plot_window.title("Grafic generat")
        canvas = FigureCanvasTkAgg(fig, master=plot_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        # Stare pentru axele curente
        swap_state = {'swapped': False}

        def recreate_plot():
            import matplotlib.pyplot as plt
            plt.style.use('dark_background')
            fig2, ax2 = plt.subplots(figsize=(8, 4))
            fig2.patch.set_facecolor('#0D0D0D')
            ax2.set_facecolor('#0D0D0D')
            if swap_state['swapped']:
                x, y = df[f2], df[f1]
                xlabel, ylabel = f2, f1
                title = f"{f1} vs {f2} pentru {model}"
            else:
                x, y = df[f1], df[f2]
                xlabel, ylabel = f1, f2
                title = f"{f2} vs {f1} pentru {model}"
            ax2.scatter(x, y, color='#B9EF17', s=50)
            ax2.plot(x, y, color='white', alpha=0.5, linestyle='-')
            ax2.set_xlabel(xlabel, color='white')
            ax2.set_ylabel(ylabel, color='white')
            ax2.set_title(title, color='white')
            ax2.grid(True, color='gray', alpha=0.2)
            for spine in ax2.spines.values():
                spine.set_color('white')
            ax2.tick_params(colors='white')
            plt.tight_layout()
            canvas.figure = fig2
            canvas._tkcanvas.pack_forget()
            canvas.get_tk_widget().pack_forget()
            canvas.__init__(fig2, master=plot_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

        # Adaugă buton de inversare axe
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

        # Adaugă un buton de închidere
        close_button = tk.Button(
            plot_window,
            text="Închide",
            command=plot_window.destroy,
            bg=COLORS["ACCENT"],
            fg=COLORS["BACKGROUND"],
            font=FONTS["BUTTON"]
        )
        close_button.pack(pady=10)
        # Setează dimensiunea ferestrei
        plot_window.geometry("900x600")
        # Centrează fereastra
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
                # Normalizează spațiile
                normalized_text = re.sub(r'\s+', ' ', text)
                print("Text normalizat:", normalized_text)
                patterns = [
                    r"cre[aă]ză\s+graf\w*\s+între\s+([\w\s]+?)\s+(?:și|si)\s+([\w\s]+?)\s+pentru\s+([\w\s]+)",
                    # Variante mai permisive
                    r"grafic.*?([\w\s]+).*?(?:si|și)\s*([\w\s]+).*?pentru\s*([\w\s]+)",
                    r"grafic.*?pentru\s*([\w\s]+).*?(?:cu|între)\s*([\w\s]+)\s*(?:si|și)\s*([\w\s]+)",
                    r"cre[aă]ză.*?grafic.*?([\w\s]+).*?(?:si|și)\s*([\w\s]+).*?pentru\s*([\w\s]+)",
                    r"grafic.*?([\w\s]+).*?(?:si|și)\s*([\w\s]+).*?([\w\s]+)",
                    # Variantele vechi
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
                        
                        # === Embedding semantic în loc de mapping fix ===
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
                            plt.style.use('dark_background')
                            fig, ax = plt.subplots(figsize=(8, 4))
                            fig.patch.set_facecolor('#0D0D0D')
                            ax.set_facecolor('#0D0D0D')

                            scatter = ax.scatter(df[f1], df[f2], color='#B9EF17', s=50)
                            ax.plot(df[f1], df[f2], color='white', alpha=0.5, linestyle='-')

                            ax.set_xlabel(f1, color='white')
                            ax.set_ylabel(f2, color='white')
                            ax.set_title(f"{f2} vs {f1} pentru {model}", color='white')
                            ax.grid(True, color='gray', alpha=0.2)

                            for spine in ax.spines.values():
                                spine.set_color('white')
                            ax.tick_params(colors='white')
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
            
            # Executăm procesarea comenzii în thread-ul principal
            self.root.after(0, process_command)
            
        except Exception as e:
            print(f"Eroare la procesarea comenzii vocale: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Eroare", f"Nu s-a putut procesa comanda vocală: {str(e)}"))
        finally:
            self.is_recording = False

    def on_child_close(self, child_window):
        """Gestionează închiderea ferestrei copil"""
        child_window.destroy()
        self.root.deiconify()  # Arată din nou fereastra meniului

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
        vehicle_menu = tk.OptionMenu(self.root, self.selected_vehicle, *vehicles, command=self.show_vehicle_image)
        vehicle_menu.config(font=FONTS["BUTTON"], bg=COLORS["ACCENT"], fg=COLORS["BACKGROUND"], width=20)
        vehicle_menu.place(x=600, y=180)

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
                self.vehicle_img_label.place(x=600, y=220)
        else:
            print(f"Imaginea pentru {model} nu a fost găsită la {img_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MenuInterface(root, "test@example.com", "password123")
    root.mainloop()
