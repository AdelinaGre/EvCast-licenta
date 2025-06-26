import tkinter as tk
from tkinter import messagebox
from tkinter import PhotoImage
from PIL import Image, ImageTk
from users_signing import UserSigning

import os

import numpy as np


try:
    from .users_signing import UserSigning
    from .Menu import MenuInterface
except ImportError:
    from users_signing import UserSigning
    from Menu import MenuInterface


COLORS = {
    "BACKGROUND": "#0D0D0D",
    "INPUT_BG": "#FFFFFF",
    "SECONDARY_BG": "#1A1C1A",
    "ACCENT": "#39753c",
    "TEXT": "black",
    "INPUT_BG": "#FFFFFF"  
}

FONTS = {
    "TITLE": ("Roboto", 20, "bold"),
    "APP_NAME": ("Roboto", 24, "bold"),
    "LABEL": ("Roboto", 14),
    "BUTTON": ("Roboto", 14, "bold")
}

class LoginInterface:
    def __init__(self, root, current_user, password):
        self.root = root
        self.root.title("Login & Register")
        self.root.geometry("1100x700")
        
   
        self.current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.images_dir = os.path.join(self.current_dir, "images")
        
        self.setup_background()
        self.user_signing = UserSigning()
        self.create_widgets()
        

         

    def setup_background(self):
       
        bg_path = os.path.join(self.images_dir, "white_green_wave.png")
        self.bg_image_pil = Image.open(bg_path)
        self.bg_image_pil = self.bg_image_pil.resize((1100, 700), Image.Resampling.LANCZOS)
        self.background_image = ImageTk.PhotoImage(self.bg_image_pil)
        self.background_label = tk.Label(self.root, image=self.background_image)
        self.background_label.place(relwidth=1, relheight=1)

    def create_header(self):
       
        logo_path = os.path.join(self.images_dir, "plugin.png")
        image = Image.open(logo_path)
        icon_image = tk.PhotoImage(file=logo_path)
        self.logo_image = PhotoImage(file=logo_path)
        self.logo_label = tk.Label(self.root, image=self.logo_image, bg=COLORS["INPUT_BG"])
        self.logo_label.place(x=40, y=40)
        self.root.iconphoto(False, icon_image)
        ico_path = os.path.join(self.images_dir, "plugin.ico")
        self.root.iconbitmap(ico_path)

        
        self.icon_image = icon_image

        self.label_app_name = tk.Label(
            self.root, 
            text="EVcast", 
            font=FONTS["APP_NAME"], 
            bg=COLORS["INPUT_BG"], 
            fg=COLORS["ACCENT"]
        )
        self.label_app_name.place(x=490, y=41)

    def create_input_fields(self):
       
        fields = [
            ("Email:", "email"),
            ("Password:", "password", True),
            ("Username:", "username")
        ]

        for i, field in enumerate(fields):
            label_text, field_name, *args = field
            y_pos = 200 + i * 50
            
            label = tk.Label(
                self.root, 
                text=label_text, 
                font=FONTS["LABEL"], 
                bg=COLORS["INPUT_BG"],
                fg=COLORS["ACCENT"]
            )
            label.place(x=280, y=y_pos)

    
            entry_border = tk.Frame(
                self.root,
                bg=COLORS["ACCENT"],
                highlightthickness=0
            )
            entry_border.place(x=400, y=y_pos, width=300, height=30)

            
            entry = tk.Entry(
                entry_border,
                font=FONTS["LABEL"], 
                bg=COLORS["INPUT_BG"],
                fg=COLORS["BACKGROUND"],
                insertbackground=COLORS["BACKGROUND"],
                bd=0,  
                show="*" if args and args[0] else None
            )
            entry.place(x=2, y=2, width=296, height=26) 

           
            setattr(self, f"entry_{field_name}", entry)


    def create_buttons(self):
        """Creează butoanele"""
        self.button_register = tk.Button(
            self.root, 
            text="Register", 
            font=FONTS["BUTTON"], 
            bg=COLORS["ACCENT"],
            fg=COLORS["INPUT_BG"], 
            command=self.register_user
        )
        self.button_register.place(x=400, y=350, width=130, height=40)

        self.button_login = tk.Button(
            self.root, 
            text="Login", 
            font=FONTS["BUTTON"], 
            bg=COLORS["ACCENT"], 
            fg=COLORS["INPUT_BG"],
            command=self.login_user
        )
        self.button_login.place(x=570, y=350, width=130, height=40)

    def create_widgets(self):
        """Creează toate widget-urile interfeței"""
        # Titlu
        self.label_title = tk.Label(
            self.root, 
            text="LOGIN", 
            font=FONTS["TITLE"], 
            bg=COLORS["INPUT_BG"], 
            fg=COLORS["ACCENT"]
        )
        self.label_title.place(x=500, y=120)

        self.create_header()
        self.create_input_fields()
        self.create_buttons()



    def register_user(self):
        """Gestionează înregistrarea utilizatorului"""
        email = self.entry_email.get()
        password = self.entry_password.get()
        username = self.entry_username.get()

        if self.user_signing.register_user(email, password, username):
            messagebox.showinfo("Succes", "Utilizator înregistrat cu succes!")
        else:
            messagebox.showerror("Eroare", "Înregistrarea a eșuat!")

    def login_user(self):
        """Gestionează autentificarea utilizatorului"""
        email = self.entry_email.get()
        password = self.entry_password.get()
        user = self.user_signing.login_user(email, password)
        if user:
            id_token = user['idToken']
            messagebox.showinfo("Succes", "Autentificare reușită!")
            self.root.destroy()
            root_menu = tk.Tk()
            app = MenuInterface(root_menu, current_user=email, id_token=id_token)
            root_menu.mainloop()
        else:
            messagebox.showerror("Eroare", "Autentificarea a eșuat!")


if __name__ == "__main__":
    root = tk.Tk()
    app = LoginInterface(root, current_user="", password="")
    root.mainloop()
