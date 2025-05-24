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
            print("\n=== Începere actualizare temperatură ===")
            # Folosim coordonatele pentru București (poți modifica pentru alte orașe)
            lat = 44.4268
            lon = 26.1025
            openweather_api_key = os.getenv("OPENWEATHER_API_KEY")
            api_key = openweather_api_key
            
            url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
            print(f"URL API: {url}")
            
            response = requests.get(url)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Răspuns API: {data}")
                if "main" in data and "temp" in data["main"]:
                    self.current_data["temperature"] = round(data["main"]["temp"])
                    print(f"Temperatură actualizată: {self.current_data['temperature']}°C")
                else:
                    print("Eroare: Nu s-a găsit temperatura în răspunsul API")
            else:
                print(f"Eroare API: {response.text}")
                print(f"Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Eroare de conexiune: {str(e)}")
        except Exception as e:
            print(f"Eroare neașteptată: {str(e)}")
        print("=== Finalizare actualizare temperatură ===\n")

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

    def record_voice_command(self):
        """Înregistrează și procesează comanda vocală"""
        try:
            import sounddevice as sd
            import numpy as np
            from scipy.io.wavfile import write
            import tempfile
            import os

            # Configurare înregistrare
            fs = 44100
            duration = 5  # secunde
            print("Înregistrare comandă vocală...")

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
            text = str(transcription).lower()
            print(f"Comandă vocală detectată: {text}")

            # Procesare comandă
            if "deschide" in text and "durata" in text and "incarcare" in text:
                self.estimare_durata_incarcare()
            elif "deschide" in text and "cost" in text and "incarcare" in text:
                self.estimare_cost()
            elif "deschide" in text and "profil" in text and "vehicul" in text:
                self.profil_vehicul()
            elif "deschide" in text and "km" in text and "ramase" in text:
                self.estimare_h_km_ramase()

            # Curățare fișier temporar
            os.remove(temp_path)

        except Exception as e:
            print(f"Eroare la procesarea comenzii vocale: {str(e)}")
            messagebox.showerror("Eroare", f"Nu s-a putut procesa comanda vocală: {str(e)}")
        finally:
            self.is_recording = False

    def on_child_close(self, child_window):
        """Gestionează închiderea ferestrei copil"""
        child_window.destroy()
        self.root.deiconify()  # Arată din nou fereastra meniului

if __name__ == "__main__":
    root = tk.Tk()
    app = MenuInterface(root, "test@example.com", "password123")
    root.mainloop()
