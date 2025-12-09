import asyncio
import threading
import tempfile
import os
from queue import Queue, Empty
import tkinter as tk  # Necesario para algunas constantes o mixins
import customtkinter as ctk  # pip install customtkinter

from pybricksdev.ble import find_device  # type: ignore
from pybricksdev.connections.pybricks import PybricksHubBLE  # type: ignore

# Configuración global de CustomTkinter
ctk.set_appearance_mode("Dark")  # Modos: "System" (estándar), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Temas: "blue" (estándar), "green", "dark-blue"

* * 
# -------------------- PROGRAMA ENVIADO AL HUB (LÓGICA ACTUALIZADA) -------------------- 

def create_program(drive_cmd: str, speed_pct: int) -> str:
    """
    Código Pybricks para controlar el motor A.
    Recibe el comando y la velocidad en porcentaje (0-100).
    """
    # Convertimos porcentaje (0-100) a velocidad de motor (0-1000 aprox)
    speed_val = int(speed_pct * 10) 
    
    # Definimos la lógica de dirección basada en el signo de la velocidad
    drive_commands = {
        'run_forward': f"motorA.run({speed_val})\nmotor_izq.run({-speed_val})",
        'run_backward': f"motorA.run({-speed_val})\nmotor_izq.run({speed_val})",
        'stop': "motorA.stop()\nmotor_izq.stop()",
        
    }

    drive_code = drive_commands.get(drive_cmd, "motorA.stop()\nmotor_izq.stop()")

    wait_code = ""
    # Si es movimiento, mantenemos el script vivo un tiempo (o hasta nueva orden)
    if drive_cmd in ['run_forward', 'run_backward']:
        wait_code = "wait(2000)" 

    program = f"""
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait

hub = PrimeHub()
motorA = Motor(Port.A)
motor_izq = Motor(Port.E)

{drive_code}
{wait_code}
"""
    return program


async def execute_command(hub: PybricksHubBLE, drive_cmd: str, speed: int, log_cb=None):
    program = create_program(drive_cmd, speed)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tf:
        tf.write(program)
        temp_path = tf.name

    should_wait = drive_cmd not in ['stop']

    try:
        # print_output=False acelera la respuesta al no esperar logs del hub
        await hub.run(temp_path, wait=should_wait, print_output=False)
        if log_cb:
            log_cb(f"Cmd: {drive_cmd} | Vel: {speed}%")

    except Exception as e:
        if log_cb:
            log_cb(f"Error ejecutando: {e}")

    finally:
        try:
            os.unlink(temp_path)
        except:
            pass


# -------------------- WORKER BLE -------------------- 

class BLEWorker:
    def __init__(self, log_queue: Queue):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._thread_main, daemon=True)
        self.queue = None
        self.hub = None
        self.running = threading.Event()
        self.log_queue = log_queue

    def log(self, msg: str):
        self.log_queue.put(msg)

    def _thread_main(self):
        asyncio.set_event_loop(self.loop)
        self.queue = asyncio.Queue()
        self.loop.create_task(self._runner())
        self.loop.run_forever()

    async def _runner(self):
        try:
            self.log("Buscando hub 'SP-7'...")
            device = await find_device("SP-7")
            if not device:
                self.log("No se encontró hub.")
                return

            self.hub = PybricksHubBLE(device)
            await self.hub.connect()
            self.log("Conectado al Hub.")
            self.running.set()

            while True:
                # Ahora la cola recibe una tupla: (comando, velocidad)
                cmd_data = await self.queue.get()
                cmd, speed = cmd_data
                await execute_command(self.hub, cmd, speed, self.log)

        except asyncio.CancelledError:
            pass

        except Exception as e:
            self.log(f"Error en worker: {e}")

        finally:
            if self.hub:
                try:
                    await self.hub.disconnect()
                    self.log("Hub desconectado.")
                except Exception as e:
                    self.log(f"Error desconexión: {e}")
            self.running.clear()

    def start(self):
        if not self.thread.is_alive():
            self.thread.start()
            # Wait for the event loop to be ready
            while self.queue is None:
                threading.Event().wait(0.01)

    def stop(self):
        if self.loop.is_running():
            for task in asyncio.all_tasks(self.loop):
                task.cancel()
            self.loop.call_soon_threadsafe(self.loop.stop)

    def send_command(self, cmd: str, speed: int = 50):
        if self.loop.is_running() and self.queue is not None:
            # Enviamos tupla (comando, velocidad)
            self.loop.call_soon_threadsafe(self.queue.put_nowait, (cmd, speed))


# -------------------- GUI CON CUSTOMTKINTER -------------------- 

class LegoGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Control LEGO Spike Prime")
        self.geometry("500x600")
        self.resizable(False, False)

        # Configuración de variables
        self.log_queue = Queue()
        self.worker = BLEWorker(self.log_queue)
        
        # Colores personalizados para botones (Hex)
        self.color_green = "#2EA043"   # Verde estilo GitHub
        self.color_red = "#DA3633"     # Rojo alerta
        self.color_blue = "#1F6FEB"    # Azul acento
        self.color_gray = "#30363D"    # Gris oscuro panel
        self.color_yellow = "#D29922"  # Amarillo para 'conectando'

        self._build_ui()
        self._poll_logs()

    def _build_ui(self):
        # --- 1. HEADER (Título y Conexión) ---
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title_lbl = ctk.CTkLabel(self.header_frame, text="Spike Prime Control", 
                                 font=ctk.CTkFont(size=20, weight="bold"))
        title_lbl.pack(side="left")

        # Contenedor derecho para botón y estado
        right_header = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        right_header.pack(side="right")

        # Indicador visual (LED circular)
        # Hacemos el círculo más pequeño (width/height 14) y ajustamos el radio
        self.status_indicator = ctk.CTkButton(right_header, text="", width=14, height=14,
                                              corner_radius=7, fg_color=self.color_red,
                                              hover=False, state="disabled")
        self.status_indicator.pack(side="left", padx=(0, 10))

        # Texto de estado
        self.lbl_status = ctk.CTkLabel(right_header, text="Sin conexión", 
                                       text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_status.pack(side="left", padx=(0, 10))

        # Botón de conexión
        self.btn_connect = ctk.CTkButton(right_header, text="Conectar", width=100,
                                         fg_color=self.color_gray,
                                         command=self.toggle_connection)
        self.btn_connect.pack(side="left")


        # --- 2. ÁREA CENTRAL (D-PAD) ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=10)

        # Contenedor para centrar los botones
        dpad_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        # Ajustamos rely a 0.5 (exactamente al medio vertical) para que no se corte arriba
        dpad_container.place(relx=0.5, rely=0.5, anchor="center")

        # Botón Adelante (Verde)
        self.btn_up = ctk.CTkButton(dpad_container, text="▲\nAdelante", width=120, height=80,
                                    fg_color=self.color_green, hover_color="#3FB950",
                                    font=ctk.CTkFont(size=14, weight="bold"))
        self.btn_up.grid(row=0, column=1, pady=10)
        # Bindeos para mantener presionado
        self.btn_up.bind("<ButtonPress-1>", lambda e: self.send_cmd("run_forward"))
        self.btn_up.bind("<ButtonRelease-1>", lambda e: self.send_cmd("stop"))

        # Botón Izquierda (Azul - Solo visual por ahora)
        self.btn_left = ctk.CTkButton(dpad_container, text="◀", width=80, height=80,
                                      fg_color=self.color_blue, hover_color="#58A6FF",
                                      font=ctk.CTkFont(size=18, weight="bold"))
        self.btn_left.grid(row=1, column=0, padx=10)
        self.btn_left.bind("<ButtonPress-1>", lambda e: self._log("Izquierda (Visual)"))

        # Botón STOP (Rojo - Centro)
        self.btn_stop = ctk.CTkButton(dpad_container, text="STOP", width=100, height=80,
                                      fg_color=self.color_red, hover_color="#F85149",
                                      font=ctk.CTkFont(size=14, weight="bold"),
                                      command=lambda: self.send_cmd("stop"))
        self.btn_stop.grid(row=1, column=1, padx=5)

        # Botón Derecha (Azul - Solo visual por ahora)
        self.btn_right = ctk.CTkButton(dpad_container, text="▶", width=80, height=80,
                                       fg_color=self.color_blue, hover_color="#58A6FF",
                                       font=ctk.CTkFont(size=18, weight="bold"))
        self.btn_right.grid(row=1, column=2, padx=10)
        self.btn_right.bind("<ButtonPress-1>", lambda e: self._log("Derecha (Visual)"))

        # Botón Atrás (Azul Oscuro/Gris)
        self.btn_down = ctk.CTkButton(dpad_container, text="▼\nAtrás", width=120, height=80,
                                      fg_color="#3b8ed0", hover_color="#58A6FF", # Un azul distinto para diferenciar
                                      font=ctk.CTkFont(size=14, weight="bold"))
        self.btn_down.grid(row=2, column=1, pady=10)
        self.btn_down.bind("<ButtonPress-1>", lambda e: self.send_cmd("run_backward"))
        self.btn_down.bind("<ButtonRelease-1>", lambda e: self.send_cmd("stop"))


        # --- 3. CONTROLES INFERIORES (Velocidad y Emergencia) ---
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.pack(fill="x", padx=20, pady=20)

        # Etiqueta Velocidad
        speed_label = ctk.CTkLabel(self.bottom_frame, text="Potencia del Motor")
        speed_label.pack(pady=(10, 0))

        # Slider de Velocidad
        self.slider = ctk.CTkSlider(self.bottom_frame, from_=0, to=100, number_of_steps=100, width=300)
        self.slider.set(50) # Valor inicial
        self.slider.pack(pady=5)
        
        # Etiquetas Lento/Rápido debajo del slider
        labels_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        labels_frame.pack(fill="x", padx=40)
        ctk.CTkLabel(labels_frame, text="0%", text_color="gray", font=("Arial", 10)).pack(side="left")
        self.lbl_speed_val = ctk.CTkLabel(labels_frame, text="50%", text_color="white", font=("Arial", 10, "bold"))
        self.lbl_speed_val.pack(side="top") # Centro (truco visual)
        ctk.CTkLabel(labels_frame, text="100%", text_color="gray", font=("Arial", 10)).pack(side="right")

        # Actualizar etiqueta de valor al mover slider
        self.slider.configure(command=self.update_speed_label)

        # Botón de Emergencia (Full Width abajo)
        self.btn_emergencia = ctk.CTkButton(self.bottom_frame, text="PARADA DE EMERGENCIA",
                                            fg_color="transparent", border_color=self.color_red, border_width=2,
                                            text_color=self.color_red, hover_color=self.color_red,
                                            height=40, font=ctk.CTkFont(weight="bold"),
                                            command=lambda: self.send_cmd("stop"))
        self.btn_emergencia.pack(fill="x", padx=20, pady=15)

        # Barra de estado simple
        self.status_bar = ctk.CTkLabel(self, text="Listo.", anchor="w", padx=10, 
                                       font=ctk.CTkFont(size=11), text_color="gray")
        self.status_bar.pack(side="bottom", fill="x")

    def update_speed_label(self, value):
        self.lbl_speed_val.configure(text=f"{int(value)}%")

    # -------- Lógica Conexión --------

    def toggle_connection(self):
        if self.btn_connect.cget("text") == "Conectar":
            self.on_connect()
        else:
            self.on_disconnect()

    def on_connect(self):
        self.lbl_status.configure(text="Buscando...", text_color="yellow")
        self.status_indicator.configure(fg_color=self.color_yellow) # Amarillo
        self.btn_connect.configure(state="disabled")
        self.worker.start()

        def wait_ready():
            if self.worker.running.is_set():
                self.lbl_status.configure(text="Conectado", text_color=self.color_green)
                self.status_indicator.configure(fg_color=self.color_green) # Verde
                self.btn_connect.configure(text="Desconectar", state="normal", fg_color=self.color_red)
                self._log("Conexión establecida.")
            else:
                self.after(200, wait_ready)

        wait_ready()

    def on_disconnect(self):
        self.worker.stop()
        self.lbl_status.configure(text="Desconectado", text_color="gray")
        self.status_indicator.configure(fg_color=self.color_red) # Rojo
        self.btn_connect.configure(text="Conectar", fg_color=self.color_gray)
        self._log("Desconectado.")

    def send_cmd(self, cmd):
        # Leemos la velocidad actual del slider
        current_speed = int(self.slider.get())
        
        if self.worker.running.is_set():
            self.worker.send_command(cmd, current_speed)
        else:
            self._log(f"[Offline] Cmd: {cmd} | Speed: {current_speed}%")

    # -------- Logs --------

    def _log(self, msg: str):
        self.status_bar.configure(text=msg)
        print(f"[LOG]: {msg}")

    def _poll_logs(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._log(msg)
        except Empty:
            pass
        self.after(150, self._poll_logs)


if __name__ == '__main__':
    app = LegoGUI()
    app.mainloop()