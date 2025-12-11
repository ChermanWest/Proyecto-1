
import asyncio
import threading
import tempfile
import os
from queue import Queue, Empty
import tkinter as tk
import customtkinter as ctk

from pybricksdev.ble import find_device  # type: ignore
from pybricksdev.connections.pybricks import PybricksHubBLE  # type: ignore

# Configuración global de CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# -------------------- CÓDIGO DEL ROBOT (MODO SOCKET STREAM) -------------------- 
LISTENER_SCRIPT = """
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port, Color
from pybricks.tools import wait
import usys as sys
import uselect

# -- CONFIGURACIÓN --
hub = PrimeHub()
hub.light.on(Color.ORANGE) 

motorA = None
motor_izq = None
motor_dir = None # Motor de dirección (Puerto C)

# Inicialización de motores de tracción
try:
    motorA = Motor(Port.A)  # Rueda derecha
except Exception: pass

try:
    motor_izq = Motor(Port.E)  # Rueda izquierda
except Exception: pass

# Inicialización del motor de dirección
try:
    motor_dir = Motor(Port.C)
    # Asumimos que al encender el robot las ruedas están rectas.
    # Reseteamos el ángulo a 0.
    motor_dir.reset_angle(0)
except Exception: pass

# -- LOOP TIPO SOCKET --
hub.light.on(Color.GREEN) # Verde = LISTO

buffer = ""

while True:
    # Comprobación no bloqueante de datos
    ready = uselect.select([sys.stdin], [], [], 0)[0]
    
    if ready:
        char = sys.stdin.read(1)
        
        if char == ';':
            # Fin del comando
            cmd = buffer.strip()
            buffer = "" 
            
            if len(cmd) > 0:
                action = cmd[0] # F, B, S, L, R, Z
                
                # --- LÓGICA DE TRACCIÓN (F=Forward, B=Back, S=Stop) ---
                if action == 'S':
                    if motorA: motorA.stop()
                    if motor_izq: motor_izq.stop()
                    hub.light.on(Color.GREEN)
                    
                elif action == 'F' or action == 'B':
                    try:
                        val_part = cmd[1:]
                        if val_part == '': val_part = '0'
                        speed = int(val_part)
                        
                        if action == 'B':
                            speed = -speed
                        
                        if motorA: motorA.run(speed)
                        if motor_izq: motor_izq.run(-speed)
                        hub.light.on(Color.BLUE)
                    except ValueError:
                        pass

                # --- LÓGICA DE DIRECCIÓN (Puerto C) ---
                # Rango de -100 a 100 grados
                elif action in ['L', 'R', 'Z']:
                    if motor_dir:
                        try:
                            # Velocidad de giro alta (800) para respuesta rápida
                            if action == 'L':
                                # Izquierda: Angulo -100
                                motor_dir.run_target(800, -100, wait=False)
                            elif action == 'R':
                                # Derecha: Angulo 100
                                motor_dir.run_target(800, 100, wait=False)
                            elif action == 'Z':
                                # Centro: Angulo 0 (Al soltar botón)
                                motor_dir.run_target(800, 0, wait=False)
                        except Exception:
                            pass

        else:
            if char != '\\n' and char != '\\r':
                buffer += char
            
    wait(5)
"""


# -------------------- WORKER BLE (MODO SOCKET) -------------------- 

class BLEWorker:
    def __init__(self, log_queue: Queue):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._thread_main, daemon=True)
        self.queue = asyncio.Queue()
        self.hub = None
        self.running = threading.Event()
        self.log_queue = log_queue

    def log(self, msg: str):
        if self.log_queue:
            self.log_queue.put(msg)

    def _thread_main(self):
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._runner())
        self.loop.run_forever()

    async def _runner(self):
        temp_path = None
        try:
            self.log("Buscando hub 'SP-7'...")
            device = await find_device("SP-7")
            if not device:
                self.log("No se encontró hub.")
                return

            self.hub = PybricksHubBLE(device)
            await self.hub.connect()
            self.log("Conectado. Cargando script...")

            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tf:
                tf.write(LISTENER_SCRIPT)
                temp_path = tf.name

            await self.hub.run(temp_path, wait=False, print_output=True)
            await asyncio.sleep(2) 
            
            self.running.set()
            self.log("¡Listo para conducir!")

            while True:
                cmd_raw = await self.queue.get() 
                
                if self.hub and self.running.is_set():
                    packet = f"{cmd_raw};" 
                    payload = packet.encode('utf-8')
                    
                    try:
                        await self.hub.write(payload)
                    except Exception as e:
                        self.log(f"Error TX: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.log(f"Error fatal: {e}")
        finally:
            if temp_path:
                try: os.unlink(temp_path)
                except: pass
            if self.hub:
                try:
                    await self.hub.write(b'S;') 
                    await self.hub.disconnect()
                except: pass
            self.running.clear()
            self.log("Socket cerrado.")

    def start(self):
        if not self.thread.is_alive():
            self.thread.start()

    def stop(self):
        if self.loop.is_running():
            for task in asyncio.all_tasks(self.loop):
                task.cancel()
            self.loop.call_soon_threadsafe(self.loop.stop)

    def send_packet(self, text_cmd: str):
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.queue.put_nowait, text_cmd)


# -------------------- GUI (CONTROL HÍBRIDO) -------------------- 

class LegoGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Control LEGO Spike Prime - Con Dirección")
        self.geometry("500x650")
        self.resizable(False, False)

        self.log_queue = Queue()
        self.worker = BLEWorker(self.log_queue)
        
        # Colores
        self.color_green = "#2EA043"
        self.color_red = "#DA3633"
        self.color_blue = "#1F6FEB"
        self.color_gray = "#30363D"
        self.color_yellow = "#D29922"

        self._build_ui()
        self._poll_logs()

    def _build_ui(self):
        # Header
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title_lbl = ctk.CTkLabel(self.header_frame, text="Spike Prime Control", 
                                 font=ctk.CTkFont(size=20, weight="bold"))
        title_lbl.pack(side="left")

        right_header = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        right_header.pack(side="right")

        self.status_indicator = ctk.CTkButton(right_header, text="", width=14, height=14,
                                              corner_radius=7, fg_color=self.color_red,
                                              hover=False, state="disabled")
        self.status_indicator.pack(side="left", padx=(0, 10))

        self.lbl_status = ctk.CTkLabel(right_header, text="Sin conexión", 
                                     text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_status.pack(side="left", padx=(0, 10))

        self.btn_connect = ctk.CTkButton(right_header, text="Conectar", width=90,
                                         fg_color=self.color_gray,
                                         command=self.toggle_connection)
        self.btn_connect.pack(side="left")

        # PANEL D-PAD
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=10)
        
        dpad_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        dpad_container.place(relx=0.5, rely=0.5, anchor="center")

        btn_style = {
            "font": ("Arial", 11, "bold"),
            "relief": "flat",
            "borderwidth": 0,
            "fg": "white",
            "activeforeground": "white"
        }

        # ADELANTE
        self.btn_up = tk.Button(dpad_container, text="▲\nAdelante", bg=self.color_green, 
                                activebackground="#268c3b", width=14, height=4, **btn_style)
        self.btn_up.grid(row=0, column=1, pady=10)
        self.btn_up.bind("<ButtonPress-1>", lambda e: self.cmd_move("F"))
        self.btn_up.bind("<ButtonRelease-1>", lambda e: self.cmd_stop_traction())

        # IZQUIERDA (DIRECCIÓN)
        self.btn_left = tk.Button(dpad_container, text="◀", bg=self.color_blue,
                                  activebackground="#1a5cbf", width=8, height=4, **btn_style)
        self.btn_left.grid(row=1, column=0, padx=10)
        # Eventos para dirección: Presionar gira a -100, soltar vuelve a 0 (Centro)
        self.btn_left.bind("<ButtonPress-1>", lambda e: self.cmd_steer("L"))
        self.btn_left.bind("<ButtonRelease-1>", lambda e: self.cmd_steer("Z"))

        # STOP (PARADA TOTAL)
        self.btn_stop = tk.Button(dpad_container, text="STOP", bg=self.color_red,
                                  activebackground="#b02a28", width=10, height=4, **btn_style)
        self.btn_stop.grid(row=1, column=1, padx=5)
        self.btn_stop.config(command=self.cmd_emergency_stop)

        # DERECHA (DIRECCIÓN)
        self.btn_right = tk.Button(dpad_container, text="▶", bg=self.color_blue,
                                   activebackground="#1a5cbf", width=8, height=4, **btn_style)
        self.btn_right.grid(row=1, column=2, padx=10)
        # Eventos para dirección: Presionar gira a 100, soltar vuelve a 0 (Centro)
        self.btn_right.bind("<ButtonPress-1>", lambda e: self.cmd_steer("R"))
        self.btn_right.bind("<ButtonRelease-1>", lambda e: self.cmd_steer("Z"))

        # ATRAS
        self.btn_down = tk.Button(dpad_container, text="▼\nAtrás", bg="#3b8ed0",
                                  activebackground="#2a6da3", width=14, height=4, **btn_style)
        self.btn_down.grid(row=2, column=1, pady=10)
        self.btn_down.bind("<ButtonPress-1>", lambda e: self.cmd_move("B"))
        self.btn_down.bind("<ButtonRelease-1>", lambda e: self.cmd_stop_traction())

        # Footer
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(self.bottom_frame, text="Velocidad Tracción").pack(pady=(10, 0))

        self.slider = ctk.CTkSlider(self.bottom_frame, from_=0, to=100, number_of_steps=100, width=300)
        self.slider.set(50) 
        self.slider.pack(pady=5)
        
        labels_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        labels_frame.pack(fill="x", padx=40)
        self.lbl_speed_val = ctk.CTkLabel(labels_frame, text="50%", text_color="white", font=("Arial", 12, "bold"))
        self.lbl_speed_val.pack(side="top") 
        self.slider.configure(command=lambda v: self.lbl_speed_val.configure(text=f"{int(v)}%"))

        self.btn_emergencia = ctk.CTkButton(self.bottom_frame, text="PARADA DE EMERGENCIA",
                                            fg_color="transparent", border_color=self.color_red, border_width=2,
                                            text_color=self.color_red, hover_color=self.color_red,
                                            height=45, font=ctk.CTkFont(weight="bold"),
                                            command=self.cmd_emergency_stop)
        self.btn_emergencia.pack(fill="x", padx=20, pady=15)

        self.status_bar = ctk.CTkLabel(self, text="Listo.", anchor="w", padx=10, 
                                     font=ctk.CTkFont(size=11), text_color="gray")
        self.status_bar.pack(side="bottom", fill="x")

    # -------- COMANDOS --------

    def cmd_steer(self, action):
        # L = Izquierda, R = Derecha, Z = Centro (Cero)
        print(f"[UI] Steer: {action}")
        if self.worker.running.is_set():
            self.worker.send_packet(action)

    def cmd_move(self, direction):
        # direction: 'F' o 'B'
        pct = self.slider.get()
        speed = int(pct * 10) # 0 a 1000
        cmd = f"{direction}{speed}"
        print(f"[UI] Move: {cmd}")
        if self.worker.running.is_set():
            self.worker.send_packet(cmd)

    def cmd_stop_traction(self, event=None):
        # Detiene solo la tracción, no la dirección
        print(f"[UI] Stop Traction")
        if self.worker.running.is_set():
            self.worker.send_packet("S")

    def cmd_emergency_stop(self):
        # Detiene todo
        print(f"[UI] EMERGENCY STOP")
        if self.worker.running.is_set():
            self.worker.send_packet("S") # Para motores A/E
            self.worker.send_packet("Z") # Centra dirección

    # -------- CONEXIÓN --------

    def toggle_connection(self):
        if self.btn_connect.cget("text") == "Conectar":
            self.on_connect()
        else:
            self.on_disconnect()

    def on_connect(self):
        self.lbl_status.configure(text="Conectando...", text_color="yellow")
        self.status_indicator.configure(fg_color=self.color_yellow)
        self.btn_connect.configure(state="disabled")
        self.worker.start()

        def wait_ready():
            if self.worker.running.is_set():
                self.lbl_status.configure(text="Conectado", text_color=self.color_green)
                self.status_indicator.configure(fg_color=self.color_green)
                self.btn_connect.configure(text="Desconectar", state="normal", fg_color=self.color_red)
                self._log("¡Sistema Listo! Ruedas centradas.")
            else:
                self.after(200, wait_ready)
        wait_ready()

    def on_disconnect(self):
        self.worker.stop()
        self.lbl_status.configure(text="Desconectado", text_color="gray")
        self.status_indicator.configure(fg_color=self.color_red)
        self.btn_connect.configure(text="Conectar", fg_color=self.color_gray)
        self._log("Desconectado.")

    def _log(self, msg: str):
        try:
            self.status_bar.configure(text=msg)
            print(f"[LOG] {msg}")
        except: pass

    def _poll_logs(self):
        try:
            while True:
                try:
                    msg = self.log_queue.get_nowait()
                    self._log(msg)
                except Empty: break
        except: pass
        self.after(150, self._poll_logs)

if __name__ == '__main__':
    app = LegoGUI()
    try:
        app.mainloop()
    finally:
        # Intentamos detener el worker si está corriendo para cerrar limpia
        try:
            app.worker.stop()
        except Exception:
            pass
