
import asyncio
from bleak import BleakScanner, BleakClient

# UUID del servicio UART usado por Pybricks
UART_SERVICE_UUID = "00001800-0000-1000-8000-00805f9b34fb"
UART_TX_UUID =     "00001800-0000-1000-8000-00805f9b34fb"  # Hub → PC
UART_RX_UUID =     "00001800-0000-1000-8000-00805f9b34fb"  # PC → Hub


async def main():
    print("Buscando dispositivos BLE...")
    devices = await BleakScanner.discover()

    spike = None
    for d in devices:
        if "Pybricks" in d.name or "SPIKE" in d.name:
            spike = d
            break

    if not spike:
        print("No encontré el hub SPIKE :(")
        return

    print("Conectando a:", spike.name, spike.address)

    async with BleakClient(spike.address) as client:

        async def notification_handler(sender, data):
            print("Hub dice:", data.decode().strip())

        # Habilitar recepción
        await client.start_notify(UART_TX_UUID, notification_handler)

        # Enviar un mensaje al hub
        await client.write_gatt_char(UART_RX_UUID, b"Hola Hub!\n")

        print("Conectado. Escribe mensajes para enviarlos. CTRL+C para salir.")

        # Leer desde consola y enviar al hub
        while True:
            msg = input("> ") + "\n"
            await client.write_gatt_char(UART_RX_UUID, msg.encode())


asyncio.run(main())
