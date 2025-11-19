# Código para Pybricks (cargarlo al hub SPIKE)
from pybricks.hubs import PrimeHub
from pybricks.tools import wait
from pybricks.iodevices import BLEDevice

hub = PrimeHub()

# Crear el dispositivo BLE en modo UART
ble = BLEDevice()

hub.display.icon("ARROW_UP")

print("Esperando conexión BLE...")

# Esperar a que la computadora se conecte
ble.wait()

print("Conectado!")

# Enviar un mensaje inicial
ble.write("Hola desde SPIKE!\n")

# Loop para leer datos desde la PC
while True:
    if ble.wait_for_data(timeout=100):
        rx = ble.read().decode().strip()
        print("Recibí:", rx)

        # Responder al PC
        ble.write(f"Eco: {rx}\n")

    wait(50)
