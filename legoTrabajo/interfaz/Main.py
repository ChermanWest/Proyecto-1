# main.py

import customtkinter as ctk
from Interfaz import LegoGUI

# Configuración global de CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

if __name__ == '__main__':
    app = LegoGUI()
    try:
        app.mainloop()
    finally:
        # Cierre limpio
        try:
            app.worker.stop()
        except Exception:
            pass