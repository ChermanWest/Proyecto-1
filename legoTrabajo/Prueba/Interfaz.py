import asyncio
import threading
import tempfile
import os
from queue import Queue, Empty
import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
    USING_CUSTOMTKINTER = True
except ImportError:
    print("Aviso: customtkinter no instalado. Usando tkinter estándar.")
    ctk = tk
    USING_CUSTOMTKINTER = False

from pybricksdev.ble import find_device  # type: ignore
from pybricksdev.connections.pybricks import PybricksHubBLE  # type: ignore

# Configuración global de CustomTkinter (solo si disponible)
if USING_CUSTOMTKINTER:
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")


# -------------------- GENERADOR DE SCRIPTS (Estilo Clásico) -------------------- 
# Generamos scripts pequeños para cada acción. Es lo más fiable.

def create_program(drive_cmd: str, speed_pct: int) -> str:
    # Convertimos slider (0-100) a velocidad real (0-1000)
    speed_val = int(speed_pct * 10)
    
    # Lógica de movimiento
    # Usamos un wait grande para que el motor siga girando indefinidamente
    # hasta que nosotros lo interrumpamos con otro comando.
    # CORRECCIÓN: Agregamos 4 espacios después del \n para mantener la indentación dentro del 'try'
    if drive_cmd == 'run_forward':
        code = f"motorA.run({speed_val})\n    wait(50000)"
    elif drive_cmd == 'run_backward':
        code = f"motorA.run({-speed_val})\n    wait(50000)"
    else:
        # Stop
        code = "motorA.stop()"

    program = f"""
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait

# Inicializar
hub = PrimeHub()
# Intentar conectar motor, si falla no pasa nada (evita crash del script)
try:
    motorA = Motor(Port.A)
    {code}
except:
    pass
"""
    return program



# -------------------- WORKER BLE (MODO INTERRUPCIÓN) -------------------- 

class BLEWorker:
    def _init_(self, log_queue: Queue):
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
        try:
            self.log("Buscando hub 'SP-7'...")
            device = await find_device("SP-7")
            if not device:
                self.log("No se encontró hub.")
                return

            self.hub = PybricksHubBLE(device)
            await self.hub.connect()
            self.log("Conectado. Listo.")
            self.running.set()

            while True:
                # Esperar siguiente comando de la GUI
                # cmd_data es una tupla: (comando, velocidad)
                cmd_data = await self.queue.get()
                cmd, speed = cmd_data
                
                if self.hub and self.running.is_set():
                    # PASO 1: INTERRUPCIÓN (Ctrl+C)
                    # Enviamos el byte \x03 que significa "KeyboardInterrupt" en MicroPython.
                    # Esto detiene cualquier script anterior (evita Protocol Error).
                    try:
                        await self.hub.write(b'\x03')
                        # Pequeña pausa para dar tiempo al Hub a detenerse
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        print(f"Error enviando stop signal: {e}")

                    # Si el comando era solo STOP, con el Ctrl+C ya basta (el script muere y motor para).
                    # Pero si queremos frenar 'suave' o asegurarnos, podemos mandar script de stop.
                    # Para optimizar: Si es STOP, ya paramos con Ctrl+C.
                    # Si es MOVER, enviamos el script de movimiento.
                    
                    if cmd != 'stop':
                        # PASO 2: ENVIAR NUEVO SCRIPT
                        program_code = create_program(cmd, speed)
                        await self._run_script(program_code)
                        print(f"[BLE] Ejecutando {cmd} ({speed}%)")
                    else:
                        print("[BLE] Stop forzado (Ctrl+C)")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.log(f"Error conexión: {e}")
        finally:
            if self.hub:
                try:
                    await self.hub.disconnect()
                except:
                    pass
            self.running.clear()
            self.log("Desconectado.")

    async def _run_script(self, code):
        """Ayuda para crear archivo temporal y ejecutarlo"""
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tf:
                tf.write(code)
                temp_path = tf.name
            
            # wait=False es clave: lanzamos el script y no bloqueamos Python
            await self.hub.run(temp_path, wait=False, print_output=False)
        except Exception as e:
            self.log(f"Error run: {e}")
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except:
                    pass

    def start(self):
        if not self.thread.is_alive():
            self.thread.start()

    def stop(self):
        if self.loop.is_running():
            for task in asyncio.all_tasks(self.loop):
                task.cancel()
            self.loop.call_soon_threadsafe(self.loop.stop)

    def send_command(self, cmd: str, speed: int):
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.queue.put_nowait, (cmd, speed))


# -------------------- GUI (HÍBRIDA) -------------------- 

class LegoGUI(ctk.CTk):
    def _init_(self):
        super()._init_()
        
        self.title("Control LEGO Spike Prime")
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

        # PANEL D-PAD (Botones TK normales para fiabilidad)
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
        self.btn_up.bind("<ButtonPress-1>", lambda e: self.cmd_action("run_forward"))
        self.btn_up.bind("<ButtonRelease-1>", lambda e: self.cmd_action("stop"))

        # IZQUIERDA
        self.btn_left = tk.Button(dpad_container, text="◀", bg=self.color_blue,
                                  activebackground="#1a5cbf", width=8, height=4, **btn_style)
        self.btn_left.grid(row=1, column=0, padx=10)

        # STOP
        self.btn_stop = tk.Button(dpad_container, text="STOP", bg=self.color_red,
                                  activebackground="#b02a28", width=10, height=4, **btn_style)
        self.btn_stop.grid(row=1, column=1, padx=5)
        self.btn_stop.config(command=lambda: self.cmd_action("stop"))

        # DERECHA
        self.btn_right = tk.Button(dpad_container, text="▶", bg=self.color_blue,
                                   activebackground="#1a5cbf", width=8, height=4, **btn_style)
        self.btn_right.grid(row=1, column=2, padx=10)

        # ATRAS
        self.btn_down = tk.Button(dpad_container, text="▼\nAtrás", bg="#3b8ed0",
                                  activebackground="#2a6da3", width=14, height=4, **btn_style)
        self.btn_down.grid(row=2, column=1, pady=10)
        self.btn_down.bind("<ButtonPress-1>", lambda e: self.cmd_action("run_backward"))
        self.btn_down.bind("<ButtonRelease-1>", lambda e: self.cmd_action("stop"))

        # Footer
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(self.bottom_frame, text="Potencia del Motor").pack(pady=(10, 0))

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
                                            command=lambda: self.cmd_action("stop"))
        self.btn_emergencia.pack(fill="x", padx=20, pady=15)

        self.status_bar = ctk.CTkLabel(self, text="Listo.", anchor="w", padx=10, 
                                       font=ctk.CTkFont(size=11), text_color="gray")
        self.status_bar.pack(side="bottom", fill="x")

    def cmd_action(self, action_cmd):
        pct = self.slider.get()
        print(f"[UI] Accion: {action_cmd} | Speed: {int(pct)}%")
        
        if self.worker.running.is_set():
            self.worker.send_command(action_cmd, int(pct))
        else:
            self._log(f"[Offline] {action_cmd}")

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
                self._log("Sistema listo.")
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
        except:
            pass

    def _poll_logs(self):
        try:
            while True:
                try:
                    msg = self.log_queue.get_nowait()
                    self._log(msg)
                except Empty:
                    break
        except:
            pass
        self.after(150, self._poll_logs)

if __name__ == '__main__':
    
    app = LegoGUI()
    app.mainloop()