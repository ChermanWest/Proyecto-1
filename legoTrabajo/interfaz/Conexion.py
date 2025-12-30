# conexion.py

import asyncio
import threading
import tempfile
import os
import traceback
from queue import Queue
from pybricksdev.ble import find_device  # type: ignore
from pybricksdev.connections.pybricks import PybricksHubBLE  # type: ignore

# Importamos el script del robot del otro archivo
from ControlMotores import LISTENER_SCRIPT  # payload del servidor a cargar en el hub

# worker BLE asíncrono, puente cliente→servidor
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
                tf.flush()
                temp_path = tf.name

            # Log the temp script path and check existence to help diagnose WinError 2
            self.log(f"Temp script path: {temp_path} (exists: {os.path.exists(temp_path)})")

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
        
            tb = traceback.format_exc()
            self.log(f"Error fatal: {e} ({type(e).__name__})\n{tb}")
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
            self.log("Sistema cerrado.")

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