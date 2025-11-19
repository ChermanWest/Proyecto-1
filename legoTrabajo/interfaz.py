import asyncio
import tkinter as Tkinter
from bleak import BleakClient, BleakScanner

# UUIDs serán detectadas dinámicamente tras la conexión
CHAR_UUID = None
WRITE_CHAR_UUID = None
NOTIFY_CHAR_UUID = None

client = None
loop = asyncio.get_event_loop()

# ---------------- Funciones BLE ----------------
async def emparejar_async():
    """Busca y conecta con un hub Pybricks o SPIKE."""
    global client
    print("Buscando dispositivos BLE...")
    devices = await BleakScanner.discover(timeout=5.0)

    target = None
    for d in devices:
        if "Pybricks" in d.name or "sp-7-" in d.name:
            target = d
            break

    if not target:
        print("No se encontró un hub Pybricks o SPIKE.")
        return

    print(f"Conectando a {target.name} ({target.address})...")
    client = BleakClient(target.address)
    await client.connect()

    if client.is_connected:
        print(f"Conectado exitosamente a {target.name}")

        # Descubrir servicios y características para encontrar
        # la característica correcta de escritura / notificación.
        services = await client.get_services()
        write_char = None
        notify_char = None

        for service in services:
            for char in service.characteristics:
                props = getattr(char, "properties", [])
                # Buscar primera característica con capacidad de escritura
                if ("write" in props or "write-without-response" in props) and not write_char:
                    write_char = char
                # Buscar primera característica con notificaciones
                if ("notify" in props or "indicate" in props) and not notify_char:
                    notify_char = char

        if write_char:
            WRITE_CHAR_UUID = write_char.uuid
            print("Usando característica de escritura:", WRITE_CHAR_UUID)
        else:
            print("No se encontró característica de escritura.")

        if notify_char:
            NOTIFY_CHAR_UUID = notify_char.uuid
            print("Usando característica de notificación:", NOTIFY_CHAR_UUID)
            # Iniciar notificaciones
            await client.start_notify(NOTIFY_CHAR_UUID, notification_handler)
        else:
            print("No se encontró característica de notificación.")

    else:
        print("No se pudo conectar.")

async def send_async(cmd):
    """Envía un comando al hub si está conectado."""
    global client
    if client and client.is_connected and WRITE_CHAR_UUID:
        # Terminar comando con newline para que el programa en el hub
        # que lee por líneas lo reciba correctamente.
        msg = (cmd + "\n").encode("utf-8")
        await client.write_gatt_char(WRITE_CHAR_UUID, msg)
        print("Enviado:", cmd)
    else:
        print("No estás conectado al hub o no se encontró la característica de escritura.")
    else:
        print("No estás conectado al hub.")

async def cerrar_conexion():
    """Cierra la conexión BLE."""
    global client
    if client and client.is_connected:
        # detiene notificaciones si hay una característica registrada
        try:
            if NOTIFY_CHAR_UUID:
                await client.stop_notify(NOTIFY_CHAR_UUID)
        except Exception:
            pass
        await client.disconnect()
        print("Conexión cerrada.")

# ---------------- Integración con Tkinter y Asyncio ----------------
def run_async_task(coro):
    """Ejecuta una tarea asyncio desde Tkinter."""
    asyncio.ensure_future(coro)

def process_asyncio_events():
    """Procesa eventos de asyncio periódicamente para Tkinter."""
    loop.call_soon(loop.stop)
    loop.run_forever()
    top.after(50, process_asyncio_events)

# ---------------- Interfaz Gamer ----------------
top = Tkinter.Tk()
top.title("Control BLE Gamer")

# Botón de emparejar
Tkinter.Button(
    top, text="Emparejar Hub", bg="blue", fg="white",
    width=33, height=3, command=lambda: run_async_task(emparejar_async())
).grid(row=0, column=0, columnspan=3, pady=5)

# Slider horizontal para girar izquierda/derecha
Tkinter.Label(top, text="Giro").grid(row=1, column=0, columnspan=3)
giro_slider = Tkinter.Scale(
    top, from_=-100, to=100, orient=Tkinter.HORIZONTAL, length=300
)
giro_slider.grid(row=2, column=0, columnspan=3, pady=5)

# Botones de adelantar y retroceder
Tkinter.Button(
    top, text="Adelante", bg="green", fg="white",
    width=15, height=5, command=lambda: run_async_task(send_async("forward"))
).grid(row=3, column=0, padx=5, pady=5)

Tkinter.Button(
    top, text="Atrás", bg="red", fg="white",
    width=15, height=5, command=lambda: run_async_task(send_async("backward"))
).grid(row=3, column=1, padx=5, pady=5)

# Slider vertical para control de aceleración
Tkinter.Label(top, text="Aceleración").grid(row=1, column=3)
aceleracion_slider = Tkinter.Scale(
    top, from_=100, to=0, orient=Tkinter.VERTICAL, length=200
)
aceleracion_slider.grid(row=2, column=3, rowspan=2, padx=5)

# Botón Stop
Tkinter.Button(
    top, text="Stop", bg="gray", fg="white",
    width=33, height=3, command=lambda: run_async_task(send_async("stop"))
).grid(row=4, column=0, columnspan=3, pady=5)

# Función para cerrar ventana
def on_close():
    run_async_task(cerrar_conexion())
    top.destroy()

top.protocol("WM_DELETE_WINDOW", on_close)
top.after(50, process_asyncio_events)

# ---------------- Loop principal ----------------
try:
    loop.run_until_complete(asyncio.sleep(0.1))
    top.mainloop()
finally:
    loop.run_until_complete(cerrar_conexion())
    loop.close()

# c:\Users\germa\Documents\GitHub\Proyecto-1\legoTrabajo\.venv\Scripts\Activate.ps1
