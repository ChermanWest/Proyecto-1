import subprocess
import sys
import os
import shutil
import time

# --- Configuración Inicial ---
script_dir = os.path.dirname(os.path.abspath(__file__))
main_py = os.path.join(script_dir, "Main.py")
dist_dir = os.path.join(script_dir, "dist")
work_dir = os.path.join(script_dir, "build")

# --- 1. Limpieza Segura ---
def limpiar_directorios():
    for folder in [dist_dir, work_dir]:
        if os.path.exists(folder):
            try:
                print(f"Intentando limpiar: {folder}...")
                shutil.rmtree(folder)
                print(f"✓ Limpiado: {folder}")
            except PermissionError:
                print(f"⚠ ADVERTENCIA: No se pudo borrar {folder}.")
                print("Asegúrate de que 'ControlLego.exe' no esté abierto.")
                print("Intentando continuar de todos modos...")
                # Si es la carpeta build, es crítico borrarla. 
                # Si es dist, PyInstaller puede sobrescribir a veces.
            except Exception as e:
                print(f"No se pudo limpiar {folder}: {e}")

limpiar_directorios()

# --- 2. Comando PyInstaller ---
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--clean",
    "--console", 
    "--name", "ControlLego",
    "--distpath", dist_dir,
    "--workpath", work_dir,
    
    # Recolección de paquetes
    "--collect-all=bleak",
    "--collect-all=pybricksdev",
    "--collect-all=winsdk",
    "--collect-all=mpy_cross_v6",
    "--collect-all=mpy_cross_v5",
    
    # Importaciones ocultas
    "--hidden-import=bleak.backends.winrt",
    "--hidden-import=winsdk.windows.devices.bluetooth",
    "--hidden-import=winsdk.windows.devices.bluetooth.genericattributeprofile",
    "--hidden-import=customtkinter",
    "--hidden-import=asyncio",
    "--hidden-import=Conexion",
    "--hidden-import=ControlMotores",
    "--hidden-import=Interfaz",
    "--hidden-import=mpy_cross_v6",
    "--hidden-import=mpy_cross_v5",
    
    main_py
]

print(f"\nCompilando {main_py}...\n")

try:
    # Agregamos una pequeña pausa para que Windows suelte los archivos
    time.sleep(1) 
    subprocess.run(cmd, check=True)
    print(f"\n" + "="*30)
    print(f"✓ ¡Compilación exitosa!")
    print(f"Ejecutable en: {os.path.join(dist_dir, 'ControlLego.exe')}")
    print("="*30)
except subprocess.CalledProcessError as e:
    print(f"\n✗ Error durante la ejecución de PyInstaller: {e}")
except Exception as e:
    print(f"\n✗ Error inesperado: {e}")