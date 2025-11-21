import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
from bleak import BleakScanner, BleakClient
import threading

class SpikeController:
    def __init__(self):
        self.client = None
        self.hub_address = None
        self.connected = False
        
        # UUID para comunicación UART con LEGO Hub
        self.UART_SERVICE_UUID = "00001800-0000-1000-8000-00805f9b34fb"
        self.UART_TX_CHAR_UUID = "00001800-0000-1000-8000-00805f9b34fb"
        
    async def scan_hubs(self):
        """Escanea dispositivos BLE cercanos buscando el Hub"""
        devices = await BleakScanner.discover(timeout=15.0)
        spike_hubs = []
        all_devices = []
        
        for device in devices:
            # Guardar todos los dispositivos para debug
            device_name = device.name if device.name else "Sin nombre"
            all_devices.append((device_name, device.address))
            
            # Buscar hubs LEGO por nombre (incluyendo "sp-" para Spike Prime)
            if device.name:
                name_lower = device.name.lower()
                name_upper = device.name.upper()
                # Detectar hubs LEGO Spike Prime (sp-X-) y otros hubs LEGO
                if any(keyword in name_upper for keyword in ["LEGO", "SPIKE", "TECHNIC", "HUB"]) or name_lower.startswith("sp-"):
                    spike_hubs.append((device.name, device.address))
        
        # Si no encuentra nada, devolver todos los dispositivos para que el usuario pueda seleccionar
        if not spike_hubs:
            print("No se encontraron hubs LEGO. Mostrando todos los dispositivos BLE:")
            for name, addr in all_devices:
                print(f"  - {name} ({addr})")
            return all_devices
        
        return spike_hubs
    
    async def connect(self, address):
        """Conecta al hub LEGO"""
        try:
            self.client = BleakClient(address, timeout=20.0)
            await self.client.connect()
            self.connected = True
            self.hub_address = address
            return True
        except Exception as e:
            print(f"Error conectando: {e}")
            return False
    
    async def disconnect(self):
        """Desconecta del hub"""
        if self.client and self.connected:
            await self.client.disconnect()
            self.connected = False
    
    async def send_command(self, command):
        """Envía comando al hub"""
        if not self.connected or not self.client:
            return False
        try:
            await self.client.write_gatt_char(self.UART_TX_CHAR_UUID, command.encode())
            return True
        except Exception as e:
            print(f"Error enviando comando: {e}")
            return False
    
    async def move_motors(self, motor_a_speed, motor_b_speed, duration=1000):
        """Controla los motores del auto"""
        # Comando MicroPython para LEGO Spike
        cmd = f"from spike import MotorPair\nimport time\npair=MotorPair('A','B')\npair.start_tank({motor_a_speed},{motor_b_speed})\ntime.sleep({duration/1000})\npair.stop()\n"
        await self.send_command(cmd)

class SpikeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Control LEGO Spike Prime")
        self.root.geometry("500x600")
        self.root.resizable(False, False)
        
        self.controller = SpikeController()
        self.hub_addresses = {}
        
        # Thread para operaciones asíncronas
        self.thread = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # Frame de conexión
        conn_frame = ttk.LabelFrame(self.root, text="Conexión", padding=10)
        conn_frame.pack(fill="x", padx=10, pady=10)
        
        self.scan_btn = ttk.Button(conn_frame, text="Buscar Hubs", command=self.scan_devices)
        self.scan_btn.pack(side="left", padx=5)
        
        self.hub_combo = ttk.Combobox(conn_frame, width=30, state="readonly")
        self.hub_combo.pack(side="left", padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Conectar", command=self.connect_hub)
        self.connect_btn.pack(side="left", padx=5)
        
        # Indicador de estado
        self.status_label = tk.Label(self.root, text="● Desconectado", fg="red", font=("Arial", 12, "bold"))
        self.status_label.pack(pady=5)
        
        # Frame de controles
        control_frame = ttk.LabelFrame(self.root, text="Control del Auto", padding=20)
        control_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Botones de dirección
        btn_style = {"width": 12, "height": 2}
        
        # Adelante
        self.forward_btn = tk.Button(control_frame, text="↑\nAdelante", command=self.move_forward, 
                                     bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), **btn_style)
        self.forward_btn.grid(row=0, column=1, padx=5, pady=5)
        
        # Izquierda
        self.left_btn = tk.Button(control_frame, text="←\nIzquierda", command=self.turn_left,
                                  bg="#2196F3", fg="white", font=("Arial", 12, "bold"), **btn_style)
        self.left_btn.grid(row=1, column=0, padx=5, pady=5)
        
        # Detener
        self.stop_btn = tk.Button(control_frame, text="■\nDetener", command=self.stop,
                                  bg="#f44336", fg="white", font=("Arial", 12, "bold"), **btn_style)
        self.stop_btn.grid(row=1, column=1, padx=5, pady=5)
        
        # Derecha
        self.right_btn = tk.Button(control_frame, text="→\nDerecha", command=self.turn_right,
                                   bg="#2196F3", fg="white", font=("Arial", 12, "bold"), **btn_style)
        self.right_btn.grid(row=1, column=2, padx=5, pady=5)
        
        # Atrás
        self.back_btn = tk.Button(control_frame, text="↓\nAtrás", command=self.move_backward,
                                  bg="#FF9800", fg="white", font=("Arial", 12, "bold"), **btn_style)
        self.back_btn.grid(row=2, column=1, padx=5, pady=5)
        
        # Control de velocidad
        speed_frame = ttk.LabelFrame(self.root, text="Velocidad", padding=10)
        speed_frame.pack(fill="x", padx=10, pady=10)
        
        self.speed_var = tk.IntVar(value=50)
        self.speed_scale = ttk.Scale(speed_frame, from_=0, to=100, orient="horizontal",
                                variable=self.speed_var, length=400)
        self.speed_scale.pack(side="left", padx=5)
        
        self.speed_label = tk.Label(speed_frame, text="50%", font=("Arial", 10))
        self.speed_label.pack(side="left", padx=5)
        
        self.speed_var.trace_add("write", self.update_speed_label)
        
        # Deshabilitar controles inicialmente
        self.toggle_controls(False)
        
    def update_speed_label(self, *args):
        self.speed_label.config(text=f"{self.speed_var.get()}%")
    
    def toggle_controls(self, enabled):
        state = "normal" if enabled else "disabled"
        for btn in [self.forward_btn, self.back_btn, self.left_btn, 
                   self.right_btn, self.stop_btn]:
            btn.config(state=state)
        self.speed_scale.config(state=state)
    
    def run_in_thread(self, coro, callback=None):
        """Ejecuta una corutina en un thread separado"""
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
            if hubs:
                self.hub_combo["values"] = [f"{name} ({addr})" for name, addr in hubs]
                self.hub_combo.current(0)
                self.hub_addresses = {f"{name} ({addr})": addr for name, addr in hubs}
                
                # Verificar si se encontraron hubs LEGO específicos
                lego_found = any("LEGO" in name.upper() or "SPIKE" in name.upper() or "HUB" in name.upper() 
                                for name, _ in hubs)
                
                if lego_found:
                    messagebox.showinfo("Éxito", f"Se encontraron {len(hubs)} hub(s) LEGO")
                else:
                    messagebox.showinfo("Dispositivos encontrados", 
                        f"Se encontraron {len(hubs)} dispositivos Bluetooth.\n\n"
                        "No se detectó ningún hub LEGO por nombre.\n"
                        "Busca en la lista un dispositivo que pueda ser tu hub\n"
                        "(puede aparecer como 'Sin nombre' o con otro identificador).")
            else:
                messagebox.showwarning("Sin resultados", 
                    "No se encontraron dispositivos Bluetooth.\n\n"
                    "Verifica que:\n"
                    "✓ El Bluetooth de tu laptop esté activado\n"
                    "✓ El hub LEGO esté encendido (luz encendida)\n"
                    "✓ Estés cerca del hub (menos de 5 metros)\n"
                    "✓ El hub no esté en modo de suspensión")
        
        try:
            self.run_in_thread(self.controller.scan_hubs(), on_scan_complete)
        except Exception as e:
            messagebox.showerror("Error", f"Error al escanear: {e}")
            self.scan_btn.config(state="normal", text="Buscar Hubs")
    
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
                self.connect_btn.config(text="Desconectar", command=self.disconnect_hub, state="normal")
                messagebox.showinfo("Éxito", "Conectado al hub")
            else:
                messagebox.showerror("Error", 
                    "No se pudo conectar al hub.\n\n"
                    "Verifica que:\n"
                    "- El hub esté encendido\n"
                    "- No esté conectado a otra aplicación")
                self.connect_btn.config(state="normal", text="Conectar")
        
        try:
            self.run_in_thread(self.controller.connect(address), on_connect_complete)
        except Exception as e:
            messagebox.showerror("Error", f"Error de conexión: {e}")
            self.connect_btn.config(state="normal", text="Conectar")
    
    def disconnect_hub(self):
        self.connect_btn.config(state="disabled", text="Desconectando...")
        
        def on_disconnect_complete(result):
            self.status_label.config(text="● Desconectado", fg="red")
            self.toggle_controls(False)
            self.connect_btn.config(text="Conectar", command=self.connect_hub, state="normal")
            messagebox.showinfo("Desconectado", "Hub desconectado")
        
        try:
            self.run_in_thread(self.controller.disconnect(), on_disconnect_complete)
        except Exception as e:
            messagebox.showerror("Error", f"Error al desconectar: {e}")
            self.connect_btn.config(state="normal", text="Desconectar")
    
    def move_forward(self):
        speed = self.speed_var.get()
        self.run_in_thread(self.controller.move_motors(speed, speed, 500))
    
    def move_backward(self):
        speed = self.speed_var.get()
        self.run_in_thread(self.controller.move_motors(-speed, -speed, 500))
    
    def turn_left(self):
        speed = self.speed_var.get()
        self.run_in_thread(self.controller.move_motors(-speed//2, speed//2, 500))
    
    def turn_right(self):
        speed = self.speed_var.get()
        self.run_in_thread(self.controller.move_motors(speed//2, -speed//2, 500))
    
    def stop(self):
        self.run_in_thread(self.controller.move_motors(0, 0, 100))

def main():
    root = tk.Tk()
    app = SpikeGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
