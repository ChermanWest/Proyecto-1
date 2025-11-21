import asyncio
from bleak import BleakClient

ADDRESS = "17:E8:2B:B8:66:05"   # tu Spike

async def main():
    async with BleakClient(ADDRESS) as client:
        print("Conectando...")
        await client.connect()

        print("Conectado. Servicios disponibles:")

        svcs = await client.get_services()
        for service in svcs:
            print(f"\nSERVICE: {service.uuid}")
            for char in service.characteristics:
                print(f"  CHAR: {char.uuid} - {char.properties}")

asyncio.run(main())
