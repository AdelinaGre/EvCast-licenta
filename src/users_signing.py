from tkinter import messagebox

try:
    from .authentification_config import auth, db
except ImportError:
    from .authentification_config import auth, db


class UserSigning:
    def __init__(self):
        pass

    def register_user(self, email, password, username):
        if not email or not password or not username:
            messagebox.showerror("Eroare", "Toate câmpurile sunt obligatorii!")
            return False

        if len(password) < 6:
            messagebox.showerror("Eroare", "Parola trebuie să aibă cel puțin 6 caractere!")
            return False

        try:
          
            try:
                auth.sign_in_with_email_and_password(email, "dummy_password")
                messagebox.showerror("Eroare", "Acest email este deja înregistrat!")
                return False
            except:
                pass  

            user = auth.create_user_with_email_and_password(email, password)
            print("Utilizator creat cu succes!")

            user_data = {"email": email, "username": username}
            db.child("utilizatori").push(user_data)
            print("Datele utilizatorului au fost salvate în baza de date.")

            return True
        except Exception as e:
            error_message = str(e)
            if "INVALID_EMAIL" in error_message:
                messagebox.showerror("Eroare", "Adresa de email nu este validă!")
            elif "EMAIL_EXISTS" in error_message:
                messagebox.showerror("Eroare", "Acest email este deja înregistrat!")
            elif "WEAK_PASSWORD" in error_message:
                messagebox.showerror("Eroare", "Parola este prea slabă!")
            else:
                messagebox.showerror("Eroare", "A apărut o eroare la înregistrare. Încercați din nou.")
            print("Eroare la înregistrare:", e)
            return False

    def login_user(self, email, password):
        if not email or not password:
            messagebox.showerror("Eroare", "Toate câmpurile sunt obligatorii!")
            return None

        try:
            user = auth.sign_in_with_email_and_password(email, password)
            print("Autentificare reușită!")
            return user
        except Exception as e:
            error_message = str(e)
            if "INVALID_LOGIN_CREDENTIALS" in error_message:
                messagebox.showerror("Eroare", "Email sau parolă incorectă!")
            elif "INVALID_EMAIL" in error_message:
                messagebox.showerror("Eroare", "Adresa de email nu este validă!")
            elif "TOO_MANY_ATTEMPTS_TRY_LATER" in error_message:
                messagebox.showerror("Eroare", "Prea multe încercări. Încercați mai târziu!")
            else:
                messagebox.showerror("Eroare", "A apărut o eroare la autentificare. Încercați din nou.")
            print("Eroare la autentificare:", e)
            return None