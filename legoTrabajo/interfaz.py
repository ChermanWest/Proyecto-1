import asyncio
import os
import tkinter as Tkinter
from bleak import BleakClient, BleakScanner
from PIL import Image, ImageTk


# UUID del carácter BLE del hub (valor por defecto/fallback)
CHAR_UUID = "00001800-0000-1000-8000-00805f9b34fb"

# Variables que se asignarán tras descubrir características
WRITE_CHAR_UUID = None
NOTIFY_CHAR_UUID = None

client = None
# Crear y establecer un event loop explícito para evitar
# DeprecationWarning: "There is no current event loop" en Python 3.10+
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ---------------- Funciones BLE ----------------
async def emparejar_async():
    """Busca y conecta con un hub Pybricks o SPIKE."""
    # Declarar globals para que los UUIDs encontrados se asignen
    global client, WRITE_CHAR_UUID, NOTIFY_CHAR_UUID
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
    else:
        print("No se pudo conectar.")

async def send_async(cmd):
    """Envía un comando al hub si está conectado."""
    global client
    if client and client.is_connected:
        # Terminar el comando con '\n' para que el Spike lo lea por línea
        msg = (cmd + "\n").encode("utf-8")
        # Usar la característica de escritura descubierta si existe,
        # si no, usar el CHAR_UUID por compatibilidad.
        char_to_write = WRITE_CHAR_UUID if WRITE_CHAR_UUID else CHAR_UUID
        await client.write_gatt_char(char_to_write, msg)
        print("Enviado:", cmd)
    else:
        print("No estás conectado al hub.")

async def cerrar_conexion():
    """Cierra la conexión BLE."""
    global client
    if client and client.is_connected:
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

# (Las imágenes de botones se cargarán más abajo, después de asegurar
# que `img_dir` existe)


# Cargar imagen de fondo 
try:
    script_dir = os.path.dirname(__file__)
except NameError:
    script_dir = os.getcwd()

img_dir = os.path.join(script_dir, "imagenesInterfaz")
os.makedirs(img_dir, exist_ok=True)
image_path = os.path.join(img_dir, "Fondo.png")

try:
    original = Image.open(image_path).convert("RGBA")
except Exception:
    print(f"No se encontró: {image_path}; usando fondo por defecto")
    original = Image.new("RGBA", (800, 600), (30, 30, 30, 255))

# Cargar imagen del botón Emparejar (ahora que img_dir existe)
emp_path = os.path.join(img_dir, "Emparejar.jpeg")
try:
    ImgBtEmp = Image.open(emp_path).convert("RGBA")
except Exception:
    print(f"No se encontró: {emp_path}; usando placeholder para Emparejar")
    ImgBtEmp = Image.new("RGBA", (40, 40), (200, 200, 200, 255))

try:
    resample = Image.Resampling.LANCZOS
except AttributeError:
    resample = Image.ANTIALIAS

ImgBtEmp = ImgBtEmp.resize((40, 40), resample)
ImgBtEmp_tk = ImageTk.PhotoImage(ImgBtEmp)
top.img_emparejar = ImgBtEmp_tk

# último tamaño conocido para evitar redibujos innecesarios
_last_size = (0, 0)

def actualizar_fondo(event):
    global fondo_tk, _last_size
    w, h = event.width, event.height
    if w <= 0 or h <= 0:
        return
    # solo redimensionar si cambió el tamaño
    if (w, h) == _last_size:
        return
    _last_size = (w, h)
    # usar remuestreo de calidad (compatibilidad con Pillow)
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.ANTIALIAS

    nueva = original.resize((w, h), resample)
    fondo_tk = ImageTk.PhotoImage(nueva)
    fondo_label.config(image=fondo_tk)

fondo_tk = ImageTk.PhotoImage(original)
fondo_label = Tkinter.Label(top, image=fondo_tk)
fondo_label.place(x=0, y=0, relwidth=1, relheight=1)

top.bind("<Configure>", actualizar_fondo)

# Botón de emparejar
Tkinter.Button(
    top,text="Emparejar Hub",image=ImgBtEmp_tk,compound="left",bg="blue",fg="white",width=200,height=60,
    command=lambda: run_async_task(emparejar_async())).grid(row=0, column=0, columnspan=3, pady=5)

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
