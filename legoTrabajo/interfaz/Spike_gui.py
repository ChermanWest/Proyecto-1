import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import threading
import sys
import os

# Asegurar que la carpeta actual está en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Spike_controller import SpikeController


class SpikeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Control LEGO Spike Prime")
        self.root.geometry("500x600")
        self.root.resizable(False, False)
        
        self.controller = SpikeController()
        self.hub_addresses = {}
        
        self.create_widgets()
        
    def create_widgets(self):
        conn_frame = ttk.LabelFrame(self.root, text="Conexión", padding=10)
        conn_frame.pack(fill="x", padx=10, pady=10)
        
        self.scan_btn = ttk.Button(conn_frame, text="Buscar Hubs", command=self.scan_devices)
        self.scan_btn.pack(side="left", padx=5)
        
        self.hub_combo = ttk.Combobox(conn_frame, width=30, state="readonly")
        self.hub_combo.pack(side="left", padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Conectar", command=self.connect_hub)
        self.connect_btn.pack(side="left", padx=5)
        
        self.status_label = tk.Label(self.root, text="● Desconectado",
                                     fg="red", font=("Arial", 12, "bold"))
        self.status_label.pack(pady=5)
        
        control_frame = ttk.LabelFrame(self.root, text="Control del Auto", padding=20)
        control_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        btn_style = {"width": 12, "height": 2}
        
        self.forward_btn = tk.Button(control_frame, text="↑\nAdelante",
            command=self.move_forward, bg="#4CAF50", fg="white",
            font=("Arial", 12, "bold"), **btn_style)
        self.forward_btn.grid(row=0, column=1, padx=5, pady=5)

        self.left_btn = tk.Button(control_frame, text="←\nIzquierda",
            command=self.turn_left, bg="#2196F3", fg="white",
            font=("Arial", 12, "bold"), **btn_style)
        self.left_btn.grid(row=1, column=0, padx=5, pady=5)

        self.stop_btn = tk.Button(control_frame, text="■\nDetener",
            command=self.stop, bg="#f44336", fg="white",
            font=("Arial", 12, "bold"), **btn_style)
        self.stop_btn.grid(row=1, column=1, padx=5, pady=5)

        self.right_btn = tk.Button(control_frame, text="→\nDerecha",
            command=self.turn_right, bg="#2196F3", fg="white",
            font=("Arial", 12, "bold"), **btn_style)
        self.right_btn.grid(row=1, column=2, padx=5, pady=5)

        self.back_btn = tk.Button(control_frame, text="↓\nAtrás",
            command=self.move_backward, bg="#FF9800", fg="white",
            font=("Arial", 12, "bold"), **btn_style)
        self.back_btn.grid(row=2, column=1, padx=5, pady=5)
        
        speed_frame = ttk.LabelFrame(self.root, text="Velocidad", padding=10)
        speed_frame.pack(fill="x", padx=10, pady=10)
        
        self.speed_var = tk.IntVar(value=50)
        self.speed_scale = ttk.Scale(speed_frame, from_=0, to=100,
            orient="horizontal", variable=self.speed_var, length=400)
        self.speed_scale.pack(side="left", padx=5)
        
        self.speed_label = tk.Label(speed_frame, text="50%", font=("Arial", 10))
        self.speed_label.pack(side="left", padx=5)
        
        self.speed_var.trace_add("write", self.update_speed_label)
        
        self.toggle_controls(False)

    def update_speed_label(self, *args):
        self.speed_label.config(text=f"{self.speed_var.get()}%")
        # Enviar la velocidad actual al hub (variable 'velocidad' en auto.py)
        try:
            self.run_in_thread(self.controller.send_command(f"velocidad:{self.speed_var.get()}"))
        except Exception:
            pass
    
    def toggle_controls(self, enabled):
        state = "normal" if enabled else "disabled"
        for btn in [
            self.forward_btn, self.back_btn, self.left_btn,
            self.right_btn, self.stop_btn
        ]:
            btn.config(state=state)
        self.speed_scale.config(state=state)
    
    def run_in_thread(self, coro, callback=None):
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(coro)
            loop.close()
            if callback:
                self.root.after(0, callback, result)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread
    
    def scan_devices(self):
        self.scan_btn.config(state="disabled", text="Buscando...")
        self.root.update()
        
        def on_scan_complete(hubs):
            self.scan_btn.config(state="normal", text="Buscar Hubs")
            print(f"[GUI] Resultado del escaneo: {hubs}")
            if hubs and hubs[0][1] is not None:
                self.hub_combo["values"] = [f"{n} ({a})" for n, a in hubs]
                self.hub_combo.current(0)
                self.hub_addresses = {f"{n} ({a})": a for n, a in hubs}
                messagebox.showinfo("Éxito", f"Se encontraron {len(hubs)} dispositivo(s) BLE")
            else:
                messagebox.showwarning("Sin resultados",
                    "No se encontraron dispositivos BLE.\n"
                    "Verifica que:\n"
                    "1. El hub esté emparejado en Bluetooth del PC\n"
                    "2. El Bluetooth esté activo\n"
                    "3. Revisa la consola para más detalles")
        
        self.run_in_thread(self.controller.scan_hubs(), on_scan_complete)
    
    def connect_hub(self):
        selected = self.hub_combo.get()
        if not selected:
            messagebox.showwarning("Advertencia", "Selecciona un hub primero")
            return
        
        address = self.hub_addresses[selected]
        self.connect_btn.config(state="disabled", text="Conectando...")
        self.root.update()
        
        def on_connect_complete(success):
            if success:
                self.status_label.config(text="● Conectado", fg="green")
                self.toggle_controls(True)
                self.connect_btn.config(text="Desconectar",
                    command=self.disconnect_hub, state="normal")
                messagebox.showinfo("Éxito", "Conectado al hub")
            else:
                messagebox.showerror("Error", "No se pudo conectar al hub.")
                self.connect_btn.config(text="Conectar", state="normal")
        
        self.run_in_thread(self.controller.connect(address), on_connect_complete)
    
    def disconnect_hub(self):
        self.connect_btn.config(state="disabled", text="Desconectando...")
        
        def on_disconnect_complete(_):
            self.status_label.config(text="● Desconectado", fg="red")
            self.toggle_controls(False)
            self.connect_btn.config(text="Conectar",
                command=self.connect_hub, state="normal")
            messagebox.showinfo("Desconectado", "Hub desconectado")
        
        self.run_in_thread(self.controller.disconnect(), on_disconnect_complete)
    
    def move_forward(self):
        # Enviar comando simple al hub para mover adelante
        try:
            self.run_in_thread(self.controller.send_command("forward"))
        except Exception:
            pass
    
    def move_backward(self):
        try:
            self.run_in_thread(self.controller.send_command("backward"))
        except Exception:
            pass
    
    def turn_left(self):
        # Giro negativo
        giro = -50
        try:
            self.run_in_thread(self.controller.send_command(f"giro:{giro}"))
        except Exception:
            pass
    
    def turn_right(self):
        # Giro positivo
        giro = 50
        try:
            self.run_in_thread(self.controller.send_command(f"giro:{giro}"))
        except Exception:
            pass
    
    def stop(self):
        try:
            self.run_in_thread(self.controller.send_command("stop"))
        except Exception:
            pass
