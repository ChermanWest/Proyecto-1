import asyncio
import threading
import tempfile
import os
from queue import Queue, Empty
import tkinter as tk
from tkinter import ttk

from pybricksdev.ble import find_device  # type: ignore
from pybricksdev.connections.pybricks import PybricksHubBLE  # type: ignore


# -------------------- PROGRAMA ENVIADO AL HUB -------------------- 

def create_program(drive_cmd: str) -> str:
    """
    Código Pybricks para controlar SOLO el motor A.
    """

    drive_commands = {
        'run_forward': "motorA.run(800)",
        'run_backward': "motorA.run(-800)",
        'stop': "motorA.stop()",
    }

    drive_code = drive_commands.get(drive_cmd, "motorA.stop()")

    wait_code = ""
    if drive_cmd in ['run_forward', 'run_backward']:
        wait_code = "wait(2000)"   # mantiene el motor encendido

    program = f"""
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait

hub = PrimeHub()
motorA = Motor(Port.A)

{drive_code}
{wait_code}
"""
    return program


async def execute_command(hub: PybricksHubBLE, drive_cmd: str, log_cb=None):
    program = create_program(drive_cmd)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tf:
        tf.write(program)
        temp_path = tf.name

    should_wait = drive_cmd not in ['stop']

    try:
        await hub.run(temp_path, wait=should_wait, print_output=False)
        if log_cb:
            log_cb(f"Ejecutado: {drive_cmd}")

    except Exception as e:
        if log_cb:
            log_cb(f"Error ejecutando comando: {e}")

    finally:
        try:
            os.unlink(temp_path)
        except:
            pass


# -------------------- WORKER BLE -------------------- 

class BLEWorker:
    def _init_(self, log_queue: Queue):
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
            self.log("Buscando hub Bluetooth…")
            device = await find_device()
            if not device:
                self.log("No se encontró hub.")
                return

            self.hub = PybricksHubBLE(device)
            await self.hub.connect()
            self.log("Conectado al Hub.")
            self.running.set()

            while True:
                drive_cmd = await self.queue.get()
                await execute_command(self.hub, drive_cmd, self.log)

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
                    self.log(f"Error al desconectar: {e}")
            self.running.clear()

    def start(self):
        if not self.thread.is_alive():
            self.thread.start()

    def stop(self):
        if self.loop.is_running():
            for task in asyncio.all_tasks(self.loop):
                task.cancel()
            self.loop.call_soon_threadsafe(self.loop.stop)

    def send_command(self, cmd: str):
        if self.loop.is_running() and self.queue is not None:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, cmd)


# -------------------- GUI -------------------- 

class LegoGUI:
    def _init_(self, root: tk.Tk):
        self.root = root
        self.root.title("Control Motor A – LEGO Pybricks")
        self.root.geometry("350x350")

        self.log_queue = Queue()
        self.worker = BLEWorker(self.log_queue)

        self._build_ui()
        self._poll_logs()

    def _build_ui(self):

        top = ttk.Frame(self.root, padding=10)
        top.pack(fill='x')

        ttk.Button(top, text="Conectar", command=self.on_connect).pack(side='left', padx=5)
        ttk.Button(top, text="Desconectar", command=self.on_disconnect).pack(side='left', padx=5)

        self.status = ttk.Label(top, text="Estado: sin conexión")
        self.status.pack(side='right')

        body = ttk.Frame(self.root, padding=20)
        body.pack(fill='both', expand=True)

        # Avanzar (mantener)
        self.btn_avanzar = ttk.Button(body, text="Motor A → Adelante")
        self.btn_avanzar.grid(row=0, column=0, pady=15)
        self.btn_avanzar.bind("<ButtonPress>", self.cmd_avanzar_press)
        self.btn_avanzar.bind("<ButtonRelease>", self.cmd_avanzar_release)

        # Retroceder (mantener)
        self.btn_retro = ttk.Button(body, text="Motor A → Atrás")
        self.btn_retro.grid(row=1, column=0, pady=15)
        self.btn_retro.bind("<ButtonPress>", self.cmd_retro_press)
        self.btn_retro.bind("<ButtonRelease>", self.cmd_retro_release)

        logf = ttk.Labelframe(self.root, text="Registro")
        logf.pack(fill='both', expand=True, padx=10, pady=10)

        self.log_text = tk.Text(logf, height=7, wrap='word')
        self.log_text.pack(fill='both', expand=True)
        self.log_text.configure(state='disabled')

    # -------- Controles del motor --------

    def cmd_avanzar_press(self, _):
        self.worker.send_command("run_forward")

    def cmd_avanzar_release(self, _):
        self.worker.send_command("stop")

    def cmd_retro_press(self, _):
        self.worker.send_command("run_backward")

    def cmd_retro_release(self, _):
        self.worker.send_command("stop")

    # -------- Conexión --------

    def on_connect(self):
        self.status.configure(text="Estado: conectando…")
        self.worker.start()

        def wait_ready():
            if self.worker.running.is_set():
                self.status.configure(text="Estado: conectado")
            else:
                self.root.after(200, wait_ready)

        wait_ready()

    def on_disconnect(self):
        self.worker.stop()
        self.status.configure(text="Estado: sin conexión")
        self._log("Desconectado.")

    # -------- Logs --------

    def _log(self, msg: str):
        self.log_queue.put(msg)

    def _poll_logs(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state='normal')
                self.log_text.insert('end', msg + "\n")
                self.log_text.see('end')
                self.log_text.configure(state='disabled')
        except Empty:
            pass

        self.root.after(150, self._poll_logs)


def main():
    root = tk.Tk()
    app = LegoGUI(root)
    root.mainloop()


if _name_ == '_main_':
    main()