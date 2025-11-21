import asyncio
from bleak import BleakScanner, BleakClient

class SpikeController:
    def __init__(self):
        self.client = None
        self.hub_address = None
        self.connected = False
        
        # UUID para comunicación UART con LEGO Hub
        self.UART_SERVICE_UUID = "00001800-0000-1000-8000-00805f9b34fb"
        self.UART_TX_CHAR_UUID = "00001800-0000-1000-8000-00805f9b34fb"
        
    async def scan_hubs(self):
        devices = await BleakScanner.discover(timeout=15.0)
        spike_hubs = []
        all_devices = []
        
        for device in devices:
            name = device.name if device.name else "Sin nombre"
            all_devices.append((name, device.address))

            if device.name:
                n1 = device.name.lower()
                n2 = device.name.upper()
                if any(k in n2 for k in ["LEGO", "SPIKE", "TECHNIC", "HUB"]) or n1.startswith("sp-"):
                    spike_hubs.append((device.name, device.address))
        
        return spike_hubs if spike_hubs else all_devices
    
    async def connect(self, address):
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
        if self.client and self.connected:
            await self.client.disconnect()
        self.connected = False
    
    async def send_command(self, command):
        if not self.connected or not self.client:
            return False
        try:
            await self.client.write_gatt_char(self.UART_TX_CHAR_UUID, command.encode())
            return True
        except Exception as e:
            print(f"Error enviando comando: {e}")
            return False
    
    async def move_motors(self, motor_a_speed, motor_b_speed, duration=1000):
        cmd = (
            "from spike import MotorPair\nimport time\n"
            f"pair=MotorPair('A','B')\n"
            f"pair.start_tank({motor_a_speed},{motor_b_speed})\n"
            f"time.sleep({duration/1000})\n"
            "pair.stop()\n"
        )
        await self.send_command(cmd)
