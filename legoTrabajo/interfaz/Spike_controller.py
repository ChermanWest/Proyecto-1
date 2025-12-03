import asyncio
import serial
import serial.tools.list_ports
import threading

class SpikeController:
    def __init__(self):
        self.ser = None
        self.port = None
        self.connected = False
        self.lock = threading.Lock()
        
    async def scan_hubs(self):
        """Escanea puertos seriales disponibles."""
        ports = []
        try:
            for port_info in serial.tools.list_ports.comports():
                port_name = port_info.device
                description = port_info.description if port_info.description else ""
                ports.append((f"{port_name} - {description}", port_name))
            return ports if ports else [("Sin puertos disponibles", None)]
        except Exception as e:
            print(f"Error escaneando puertos: {e}")
            return []
    
    async def connect(self, port):
        """Conecta al hub a través del puerto serial."""
        if not port:
            print("Puerto inválido")
            return False
        try:
            self.ser = serial.Serial(port, baudrate=115200, timeout=2.0)
            self.port = port
            self.connected = True
            await asyncio.sleep(0.5)
            print(f"Conectado al puerto {port}")
            return True
        except Exception as e:
            print(f"Error conectando al puerto {port}: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Desconecta del hub."""
        if self.ser and self.connected:
            try:
                self.ser.close()
                print("Desconectado")
            except Exception as e:
                print(f"Error al desconectar: {e}")
        self.connected = False
    
    async def send_command(self, command):
        """Envía un comando al hub vía puerto serial."""
        if not self.connected or not self.ser:
            print("No conectado al hub")
            return False
        try:
            with self.lock:
                if isinstance(command, str):
                    b = command.encode('utf-8')
                else:
                    b = bytes(command)
                
                if not b.endswith(b"\n"):
                    b = b + b"\n"
                
                self.ser.write(b)
                self.ser.flush()
            
            print(f"Enviado: {b.decode('utf-8', errors='replace').strip()}")
            return True
        except Exception as e:
            print(f"Error enviando comando: {e}")
            self.connected = False
            return False
    
    async def move_motors(self, motor_a_speed, motor_b_speed, duration=1000):
        """Envía comando de movimiento (compatible con auto.py)."""
        cmd = f"velocidad:{int(motor_a_speed)}\n"
        await self.send_command(cmd)
