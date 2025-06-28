import sys
print(sys.executable)
import tkinter as tk
from tkinter import messagebox, PhotoImage, StringVar, OptionMenu
from PIL import Image, ImageTk
from .users_signing import UserSigning
from .authentification_config import db, auth
import pandas as pd
import speech_recognition as sr
import re
import threading
import time
import sounddevice as sd
from scipy.io.wavfile import write
import tempfile
import numpy as np
import os
from openai import OpenAI
from dotenv import load_dotenv



class VehicleProfile:
    def __init__(self, root, current_user, id_token):
        self.root = root
        self.current_user = current_user
        self.id_token = id_token
        self.root.title("Profil Vehicul")
        self.root.geometry("1100x700")
        self.vehicule_box = None
        
       
        load_dotenv()
        openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=openai_api_key)
        
      
        self.bg_image_pil = Image.open("images/white_green_wave.png").resize((1100, 700), Image.Resampling.LANCZOS)
        self.background_image = ImageTk.PhotoImage(self.bg_image_pil)
        self.background_label = tk.Label(self.root, image=self.background_image)
        self.background_label.place(relwidth=1, relheight=1)

       
        back_button = tk.Button(
            self.root,
            text="↩ Înapoi la Meniu",
            font=("Roboto", 12),
            bg="#39753c",
            fg="white",
            command=self.back_to_menu
        )
        back_button.place(x=935, y=30)

        self.user_signing = UserSigning()
        self.load_dropdown_data()
        self.create_widgets()
        
        
        self.is_recording = False
        self.recording_thread = None
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 300

    def load_dropdown_data(self):
        df = pd.read_csv("ev_charging_patterns_filled.csv")
        self.vehicle_models = sorted(df['Vehicle Model'].dropna().unique().tolist())
        self.charger_types = sorted(df['Charger Type'].dropna().unique().tolist())

        battery_vals = df['Battery Capacity (kWh)'].dropna().unique().tolist()
        self.battery_kwh_list = sorted([str(int(v)) if float(v).is_integer() else str(v) for v in battery_vals])

        age_vals = df['Vehicle Age (years)'].dropna().unique().tolist()
        self.vehicle_age_list = sorted([str(int(v)) if float(v).is_integer() else str(v) for v in age_vals])

    def create_widgets(self):
        tk.Label(self.root, text="Vehicul Profile", font=("Roboto", 20, "bold"),
                 bg="white", fg="#39753c").place(x=50, y=150)

        self.logo_image = PhotoImage(file="images/plugin_1.png")
        tk.Label(self.root, image=self.logo_image, bg="white").place(x=30, y=30)

        tk.Label(self.root, text="EVcast", font=("Roboto", 24, "bold"),
                 bg="white", fg="#39753c").place(x=110, y=41)

        tk.Label(self.root, text=f"Utilizator: {self.current_user}", font=("Roboto", 12),
                 bg="white", fg="black").place(x=700, y=30)

       
        tk.Button(self.root, text="Adaugă Profil Vehicul", font=("Roboto", 12),
                  bg="#39753c", fg="white", relief="flat", command=self.profil_vehicul).place(x=50, y=200, width=250)



        self.afiseaza_vehicule()  

    def back_to_menu(self):
        """Închide interfața curentă și revine la meniu"""
        for widget in self.root.winfo_children():
            widget.destroy()
        from .Menu import MenuInterface
        MenuInterface(self.root, self.current_user, self.id_token)

    def profil_vehicul(self):
        window = tk.Toplevel(self.root)
        window.title("Adaugă Vehicul")
        window.geometry("400x600")
        window.configure(bg="white")
        window.transient(self.root)
        window.grab_set()
        window.focus_set()
        window.lift()

        tk.Label(window, text="Adaugă Vehicul", font=("Roboto", 16, "bold"),
                 bg="white", fg="#39753c").pack(pady=20)

        
        self.recording_indicator = tk.Canvas(window, width=60, height=60, bg="white", highlightthickness=0)
        self.recording_indicator.pack(pady=10)
        self.recording_indicator.create_oval(10, 10, 50, 50, fill="gray", tags="indicator")

        self.text_display = tk.Text(window, height=10, width=40, bg="#262626", fg="white",
                                     font=("Roboto", 10), wrap=tk.WORD)
        self.text_display.pack(pady=10, padx=20)

        
        buttons_frame = tk.Frame(window, bg="white")
        buttons_frame.pack(pady=10)

        self.record_button = tk.Button(buttons_frame, text=" Începe Înregistrarea",
                                     font=("Roboto", 12), bg="#39753c", fg="#0D0D0D",
                                     command=lambda: self.toggle_recording(window))
        self.record_button.pack(side=tk.LEFT, padx=5)

        save_button = tk.Button(buttons_frame, text=" Salvează",
                              font=("Roboto", 12), bg="#39753c", fg="#0D0D0D",
                              command=lambda: self.save_voice_data(window))
        save_button.pack(side=tk.LEFT, padx=5)

       
        manual_button = tk.Button(buttons_frame, text=" Introducere Manuală",
                                  font=("Roboto", 12), bg="#39753c", fg="#0D0D0D",
                                  command=lambda: self.show_manual_input(window))
        manual_button.pack(side=tk.LEFT, padx=5)

    def toggle_recording(self, window):
       
        if not self.is_recording:
            self.start_recording(window)
            self.record_button.config(text=" Oprește Înregistrarea")
            self._animate_recording()
        else:
            self.stop_recording()
            self.record_button.config(text=" Începe Înregistrarea")
            self.recording_indicator.itemconfig("indicator", fill="gray")

    def _animate_recording(self):
       
        if self.is_recording:
            current_color = self.recording_indicator.itemcget("indicator", "fill")
            new_color = "#ff0000" if current_color == "gray" else "gray"
            self.recording_indicator.itemconfig("indicator", fill=new_color)
            self.root.after(500, self._animate_recording)

    def start_recording(self, window):
      
        if not self.is_recording:
            self.is_recording = True
            self.recording_thread = threading.Thread(target=lambda: self.record_audio(window))
            self.recording_thread.daemon = True
            self.recording_thread.start()

    def stop_recording(self):
       
        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join()

    def record_audio(self, window):
       
        try:
            print("=== Începere proces înregistrare audio ===")

            #  1. Găsește un dispozitiv valid de înregistrare
            devices = sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            print(f"Dispozitive audio găsite: {len(input_devices)}")
            
            default_input = None
            for device in input_devices:
                print(f"Verificare dispozitiv: {device['name']}")
                if 'Realtek' in device['name'] or 'Microphone' in device['name']:
                    default_input = device
                    break

            if default_input is None and input_devices:
                default_input = input_devices[0]

            if default_input is None:
                raise Exception(" Nu a fost detectat niciun microfon!")

            print(f"Folosim dispozitivul implicit: {default_input['name']}")

          
            fs = 44100
            duration = 15  # secunde
            print(f"Configurare înregistrare: {fs}Hz, {duration} secunde")

            sd.default.samplerate = fs
            sd.default.channels = 1
            sd.default.device = default_input['index']

            window.after(0, lambda: self.text_display.delete(1.0, tk.END))
            window.after(0, lambda: self.text_display.insert(tk.END, f" Microfon selectat: {default_input['name']}\n"))
            window.after(0, lambda: self.text_display.insert(tk.END, " Înregistrare în curs...\n"))
            window.after(0, lambda: self.text_display.insert(tk.END, " Vorbiți acum...\n"))

            
            audio = sd.rec(int(duration * fs))
            sd.wait()

            print("Înregistrare finalizată")

            if audio is None or not audio.any():
                raise Exception(" Nu s-a detectat niciun sunet în timpul înregistrării!")

           
            audio = audio / np.max(np.abs(audio))
            print(f"Audio înregistrat - Formă: {audio.shape}, Valoare maximă: {np.max(audio)}")

           
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            write(temp_path, fs, audio)
            print(f"Fișier audio salvat temporar la: {temp_path}")

            window.after(0, lambda: self.text_display.insert(tk.END, "Procesare cu OpenAI Whisper...\n"))

            
            with open(temp_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ro"
                )
            text = str(transcription)
            print(f"[DEBUG] Text obținut de Whisper: '{text}'")

            if not text.strip():
                raise Exception("Nu s-a putut detecta niciun text în înregistrare!")

           
            window.after(0, lambda: self.text_display.insert(tk.END, "\n=== Text recunoscut ===\n"))
            window.after(0, lambda: self.text_display.insert(tk.END, f"{text}\n"))
            window.after(0, lambda: self.text_display.insert(tk.END, "=====================\n"))
            window.after(0, lambda: self.text_display.insert(tk.END, "\nProcesare informații...\n"))
            window.after(0, lambda: self.update_text_display(text))

            
            os.remove(temp_path)
            print("Fișierul audio temporar a fost șters")

        except Exception as e:
            print("Eroare în record_audio():", str(e))
            window.after(0, lambda: self.text_display.insert(tk.END, f"\nEroare la înregistrare: {str(e)}\n"))


        finally:
            self.is_recording = False
            window.after(0, lambda: self.record_button.config(text=" Începe Înregistrarea"))
            window.after(0, lambda: self.recording_indicator.itemconfig("indicator", fill="gray"))


    def update_text_display(self, text):
       
        self.text_display.insert(tk.END, f"\nText recunoscut: {text}\n")

        vehicle_info = {
            "model": None,
            "baterie_kWh": None,
            "vechime_ani": None,
            "tip_incarcator": None,
            "user_type": None
        }

       
        numere_cuvinte = {
            "un": "1", "unu": "1", "doi": "2", "două": "2", "trei": "3",
            "patru": "4", "cinci": "5", "șase": "6", "șapte": "7",
            "opt": "8", "nouă": "9", "zece": "10"
        }

        text_lower = text.lower()

        
        for cuv, cifra in numere_cuvinte.items():
            text_lower = re.sub(rf'\b{cuv}\b', cifra, text_lower)

       
        for model in self.vehicle_models:
            if model.lower() in text_lower:
                vehicle_info["model"] = model
                self.text_display.insert(tk.END, f"Model detectat: {model}\n")
                break

       
        battery_match = re.search(r'(\d+)\s*(?:kwh|kw)', text_lower)
        if battery_match:
            vehicle_info["baterie_kWh"] = battery_match.group(1)
            self.text_display.insert(tk.END, f"Capacitate baterie detectată: {battery_match.group(1)} kWh\n")

        
        age_match = re.search(r'(\d+)\s*(?:ani|an)', text_lower)
        if age_match:
            vehicle_info["vechime_ani"] = age_match.group(1)
            self.text_display.insert(tk.END, f"Vechime detectată: {age_match.group(1)} ani\n")

       
        for charger in self.charger_types:
            if charger.lower() in text_lower:
                vehicle_info["tip_incarcator"] = charger
                self.text_display.insert(tk.END, f"Tip încărcător detectat: {charger}\n")
                break

        
        user_type_mapping = {
            "comuter": "Commuter",
            "commuter": "Commuter",
            "comutator": "Commuter",
            "long distance": "Long-Distance Traveler",
            "long-distance": "Long-Distance Traveler",
            "long distance traveler": "Long-Distance Traveler",
            "casual": "Casual Driver",
            "casual driver": "Casual Driver",
            "sofer casual": "Casual Driver"
        }

        
        for key, value in user_type_mapping.items():
            if key in text_lower:
                vehicle_info["user_type"] = value
                self.text_display.insert(tk.END, f"Tip utilizator detectat: {value}\n")
                break

        
        if vehicle_info["user_type"] is None:
            if "comut" in text_lower:
                vehicle_info["user_type"] = "Commuter"
                self.text_display.insert(tk.END, "Tip utilizator detectat: Commuter\n")
            elif "long" in text_lower and "distance" in text_lower:
                vehicle_info["user_type"] = "Long-Distance Traveler"
                self.text_display.insert(tk.END, "Tip utilizator detectat: Long-Distance Traveler\n")
            elif "casual" in text_lower:
                vehicle_info["user_type"] = "Casual Driver"
                self.text_display.insert(tk.END, "Tip utilizator detectat: Casual Driver\n")

        self.text_display.see(tk.END)
        return vehicle_info


    def handle_voice_input(self):
       
        if not hasattr(self, 'voice_window'):
            self.voice_window = tk.Toplevel(self.root)
            self.voice_window.title("Înregistrare Vocală")
            self.voice_window.geometry("500x600")
            self.voice_window.configure(bg="#1A1C1A")
            
            
            self.recording_indicator = tk.Canvas(self.voice_window, width=60, height=60, 
                                              bg="#1A1C1A", highlightthickness=0)
            self.recording_indicator.pack(pady=10)
            self.recording_indicator.create_oval(10, 10, 50, 50, fill="gray", tags="indicator")

           
            self.text_display = tk.Text(self.voice_window, height=20, width=50, 
                                      bg="#262626", fg="white", font=("Roboto", 10))
            self.text_display.pack(pady=10, padx=20)

            
            button_frame = tk.Frame(self.voice_window, bg="#1A1C1A")
            button_frame.pack(pady=10)

            self.record_button = tk.Button(button_frame, text=" Start Înregistrare",
                                         font=("Roboto", 12), bg="#39753c", fg="#0D0D0D",
                                         command=self.toggle_recording)
            self.record_button.pack(side=tk.LEFT, padx=5)

            save_button = tk.Button(button_frame, text=" Salvează",
                                  font=("Roboto", 12), bg="#39753c", fg="#0D0D0D",
                                  command=self.save_voice_data)
            save_button.pack(side=tk.LEFT, padx=5)

    def save_voice_data(self, window):
        
        text = self.text_display.get(1.0, tk.END)
        
       
        vehicle_info = {
            "model": None,
            "baterie_kWh": None,
            "vechime_ani": None,
            "tip_incarcator": None,
            "user_type": None
        }
        
        
        for line in text.split('\n'):
            if "Model detectat:" in line:
                vehicle_info["model"] = line.split(": ")[1].strip()
            elif "Capacitate baterie detectată:" in line:
                vehicle_info["baterie_kWh"] = line.split(": ")[1].split()[0].strip()
            elif "Vechime detectată:" in line:
                vehicle_info["vechime_ani"] = line.split(": ")[1].split()[0].strip()
            elif "Tip încărcător detectat:" in line:
                vehicle_info["tip_incarcator"] = line.split(": ")[1].strip()
            elif "Tip utilizator detectat:" in line:
                vehicle_info["user_type"] = line.split(": ")[1].strip()

       
        missing_info = []
        for key, value in vehicle_info.items():
            if value is None:
                if key == "model":
                    missing_info.append("modelul vehiculului")
                elif key == "baterie_kWh":
                    missing_info.append("capacitatea bateriei")
                elif key == "vechime_ani":
                    missing_info.append("vârsta vehiculului")
                elif key == "tip_incarcator":
                    missing_info.append("tipul de încărcător")
                elif key == "user_type":
                    missing_info.append("tipul de utilizator")

        if missing_info:
            messagebox.showwarning("Informații lipsă", 
                f"Nu au fost detectate următoarele informații: {', '.join(missing_info)}.\n"
                f"Vă rugăm să încercați din nou sau să folosiți introducerea manuală.")
            return

       
        sanitized_email = self.current_user.replace('.', '_')
        try:
            if self.id_token:
                db.child("vehicule").child(sanitized_email).push(vehicle_info, token=self.id_token)
                messagebox.showinfo("Succes", "Vehicul salvat cu succes!")
                window.destroy()  
                self.afiseaza_vehicule() 
            else:
                messagebox.showerror("Eroare", "Nu sunteți autentificat. Vă rugăm să vă autentificați din nou.")
        except Exception as e:
            print("Eroare Firebase:", e)
            error_message = "Nu s-a putut salva vehiculul din următoarele motive:\n"
            if "permission_denied" in str(e):
                error_message += "- Nu aveți permisiunea de a salva date\n"
            elif "network_error" in str(e):
                error_message += "- Eroare de conexiune la baza de date\n"
            elif "invalid_data" in str(e):
                error_message += "- Date invalide detectate\n"
            else:
                error_message += f"- Eroare neașteptată: {str(e)}\n"
            error_message += "\nVă rugăm să:\n"
            error_message += "1. Verificați conexiunea la internet\n"
            error_message += "2. Verificați dacă sunteți autentificat\n"
            error_message += "3. Încercați din nou sau folosiți introducerea manuală"
            messagebox.showerror("Eroare la salvare", error_message)

    def show_manual_input(self, window):
        
        for widget in window.winfo_children():
            widget.destroy()

        tk.Label(window, text="Profil Vehicul", font=("Roboto", 16, "bold"),
                 bg="white", fg="#39753c").pack(pady=20)

        
        def create_dropdown(label_text, options, variable):
            tk.Label(window, text=label_text, bg="white", fg="#39753c", 
                    font=("Roboto", 12)).pack(anchor="w", padx=40)
            tk.OptionMenu(window, variable, *options).pack(padx=40, pady=5, fill="x")

        selected_model = tk.StringVar(value=self.vehicle_models[0])
        selected_battery = tk.StringVar(value=self.battery_kwh_list[0])
        selected_age = tk.StringVar(value=self.vehicle_age_list[0])
        selected_charger = tk.StringVar(value=self.charger_types[0])
        user_types = [
            "Long-Distance Traveler", "Commuter", "Casual Driver"
        ]
        selected_user_type = tk.StringVar(value=user_types[0])

        create_dropdown("Model Vehicul:", self.vehicle_models, selected_model)
        create_dropdown("Capacitate Baterie (kWh):", self.battery_kwh_list, selected_battery)
        create_dropdown("Vechime Vehicul (ani):", self.vehicle_age_list, selected_age)
        create_dropdown("Tip Încărcător:", self.charger_types, selected_charger)
        create_dropdown("Tip Utilizator:", user_types, selected_user_type)

        def save_profile():
            model = selected_model.get()
            battery = selected_battery.get()
            age = selected_age.get()
            charger = selected_charger.get()
            user_type = selected_user_type.get()

            if not model or not battery or not age or not charger or not user_type:
                messagebox.showerror("Eroare", "Toate câmpurile sunt obligatorii.")
                return

            vehicle_data = {
                "model": model,
                "baterie_kWh": battery,
                "vechime_ani": age,
                "tip_incarcator": charger,
                "user_type": user_type
            }

            sanitized_email = self.current_user.replace('.', '_')
            try:
                if self.id_token:
                    db.child("vehicule").child(sanitized_email).push(vehicle_data, token=self.id_token)
                    messagebox.showinfo("Succes", "Vehicul salvat în Firebase.")
                    window.destroy()
                    self.afiseaza_vehicule()
                else:
                    messagebox.showerror("Eroare", "Nu sunteți autentificat. Vă rugăm să vă autentificați din nou.")
            except Exception as e:
                print("Eroare Firebase:", e)
                messagebox.showerror("Eroare", "Nu s-a putut salva vehiculul.")

        tk.Button(window, text="Salvează", font=("Roboto", 12, "bold"),
                  bg="#39753c", fg="white", command=save_profile).pack(pady=20)

    def afiseaza_vehicule(self):
        if hasattr(self, 'vehicule_frame'):
            self.vehicule_frame.destroy()

        self.vehicule_frame = tk.Frame(self.root, bg="white")
        self.vehicule_frame.place(x=10, y=250)

        sanitized_email = self.current_user.replace('.', '_')
        try:
            if self.id_token:
                vehicule = db.child("vehicule").child(sanitized_email).get(token=self.id_token)
                if vehicule.each():
                    for v in vehicule.each():
                        info = v.val()
                        vehicle_id = v.key() 

                        container = tk.Frame(self.vehicule_frame, bg="white", bd=1, relief="solid")
                        container.pack(fill="x", padx=30, pady=5)

                        expanded = tk.BooleanVar(value=False)

                       
                        header_frame = tk.Frame(container, bg="white")
                        header_frame.pack(fill="x", padx=10, pady=5)

                        def toggle(c=container, i=info, e=expanded):
                            e.set(not e.get())
                            if e.get():
                                d = tk.Frame(c, bg="white")
                                d.pack(fill="x", padx=20, pady=5)
                                tk.Label(d, text=f"Baterie: {i.get('baterie_kWh')} kWh", bg="white", fg="black").pack(anchor="w")
                                tk.Label(d, text=f"Vechime: {i.get('vechime_ani')} ani", bg="white", fg="black").pack(anchor="w")
                                tk.Label(d, text=f"Încărcător: {i.get('tip_incarcator')}", bg="white", fg="black").pack(anchor="w")
                                tk.Label(d, text=f"Tip Utilizator: {i.get('user_type')}", bg="white", fg="black").pack(anchor="w")
                                c.detail_frame = d
                            else:
                                if hasattr(c, 'detail_frame'):
                                    c.detail_frame.destroy()

                        
                        b = tk.Button(header_frame, text=f"{info.get('model')} ▼", anchor="w", bg="#39753c", fg="white",
                                    relief="flat", font=("Roboto", 12, "bold"), command=toggle)
                        b.pack(side="left", fill="x", expand=True)

                        
                        def edit_vehicle():
                            self.edit_vehicle_window(vehicle_id, info)

                        def delete_vehicle():
                            if messagebox.askyesno("Confirmare ștergere", 
                                f"Sunteți sigur că doriți să ștergeți vehiculul {info.get('model')}?"):
                                try:
                                    db.child("vehicule").child(sanitized_email).child(vehicle_id).remove(token=self.id_token)
                                    messagebox.showinfo("Succes", "Vehicul șters cu succes!")
                                    self.afiseaza_vehicule()  
                                except Exception as e:
                                    messagebox.showerror("Eroare", f"Nu s-a putut șterge vehiculul: {str(e)}")

                        edit_btn = tk.Button(header_frame, text="Editare", bg="#39753c", fg="white",
                                          command=edit_vehicle, font=("Roboto", 10))
                        edit_btn.pack(side="right", padx=5)

                        delete_btn = tk.Button(header_frame, text="Sterge", bg="#39753c", fg="white",
                                            command=delete_vehicle, font=("Roboto", 10))
                        delete_btn.pack(side="right", padx=5)

                else:
                    tk.Label(self.vehicule_frame, text="Niciun vehicul adăugat încă.",
                            bg="#39753c", fg="white", font=("Roboto", 12)).pack()
            else:
                messagebox.showerror("Eroare", "Nu sunteți autentificat. Vă rugăm să vă autentificați din nou.")
        except Exception as e:
            print("Eroare la afișare vehicule:", str(e))
            messagebox.showerror("Eroare", f"Eroare la încărcarea vehiculelor: {str(e)}")
            tk.Label(self.vehicule_frame, text=f"Eroare la încărcarea vehiculelor: {str(e)}",
                     bg="#39753c", fg="red", font=("Roboto", 12)).pack()

    def edit_vehicle_window(self, vehicle_id, current_info):
        """Deschide fereastra de editare pentru un vehicul"""
        window = tk.Toplevel(self.root)
        window.title("Editare Vehicul")
        window.geometry("400x600")
        window.configure(bg="white")
        window.transient(self.root)
        window.grab_set()

        tk.Label(window, text="Editare Vehicul", font=("Roboto", 16, "bold"),
                 bg="white", fg="#39753c").pack(pady=20)

       
        def create_dropdown(label_text, options, variable):
            tk.Label(window, text=label_text, bg="white", fg="#39753c", 
                    font=("Roboto", 12)).pack(anchor="w", padx=40)
            tk.OptionMenu(window, variable, *options).pack(padx=40, pady=5, fill="x")

        selected_model = tk.StringVar(value=current_info.get('model', self.vehicle_models[0]))
        selected_battery = tk.StringVar(value=current_info.get('baterie_kWh', self.battery_kwh_list[0]))
        selected_age = tk.StringVar(value=current_info.get('vechime_ani', self.vehicle_age_list[0]))
        selected_charger = tk.StringVar(value=current_info.get('tip_incarcator', self.charger_types[0]))
        user_types = ["Long-Distance Traveler", "Commuter", "Casual Driver"]
        selected_user_type = tk.StringVar(value=current_info.get('user_type', user_types[0]))

        create_dropdown("Model Vehicul:", self.vehicle_models, selected_model)
        create_dropdown("Capacitate Baterie (kWh):", self.battery_kwh_list, selected_battery)
        create_dropdown("Vechime Vehicul (ani):", self.vehicle_age_list, selected_age)
        create_dropdown("Tip Încărcător:", self.charger_types, selected_charger)
        create_dropdown("Tip Utilizator:", user_types, selected_user_type)

        def save_changes():
            new_data = {
                "model": selected_model.get(),
                "baterie_kWh": selected_battery.get(),
                "vechime_ani": selected_age.get(),
                "tip_incarcator": selected_charger.get(),
                "user_type": selected_user_type.get()
            }

            sanitized_email = self.current_user.replace('.', '_')
            try:
                if self.id_token:
                    db.child("vehicule").child(sanitized_email).child(vehicle_id).update(new_data, token=self.id_token)
                    messagebox.showinfo("Succes", "Vehicul actualizat cu succes!")
                    window.destroy()
                    self.afiseaza_vehicule()
                else:
                    messagebox.showerror("Eroare", "Nu sunteți autentificat.")
            except Exception as e:
                messagebox.showerror("Eroare", f"Nu s-a putut actualiza vehiculul: {str(e)}")

        tk.Button(window, text="Salvează Modificările", font=("Roboto", 12, "bold"),
                  bg="#39753c", fg="white", command=save_changes).pack(pady=20)


if __name__ == "__main__":
    root = tk.Tk()
   
    test_email = "test@example.com"
    test_password = "test123"
    app = VehicleProfile(root, test_email, test_password)
    root.mainloop()
