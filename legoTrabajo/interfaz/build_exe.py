import subprocess
import sys
import os
import shutil

# --- Configuración Inicial ---
script_dir = os.path.dirname(os.path.abspath(__file__))
main_py = os.path.join(script_dir, "Main.py")
dist_dir = os.path.join(script_dir, "dist")
work_dir = os.path.join(script_dir, "build")

# --- 1. Limpieza ---
for folder in [dist_dir, work_dir]:
    if os.path.exists(folder):
        shutil.rmtree(folder)
        print(f"Limpiado: {folder}")

# --- 2. Comando PyInstaller CORREGIDO ---
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--clean",
    "--console", # Mantenlo en console para ver errores si fallara
    "--name", "ControlLego",
    "--distpath", dist_dir,
    "--workpath", work_dir,
    
    # === AQUÍ ESTABA EL ERROR ===
    # Usamos el signo '=' para asegurar que no haya espacios sueltos
    "--collect-all=bleak",
    "--collect-all=pybricksdev",
    "--collect-all=winsdk",
    
    # Importaciones ocultas
    "--hidden-import=bleak.backends.winrt",
    "--hidden-import=winsdk.windows.devices.bluetooth",
    "--hidden-import=winsdk.windows.devices.bluetooth.genericattributeprofile",
    "--hidden-import=customtkinter",
    "--hidden-import=asyncio",
    "--hidden-import=Conexion",
    "--hidden-import=ControlMotores",
    "--hidden-import=Interfaz",
    
    main_py
]

print(f"Compilando {main_py}...\n")

try:
    subprocess.run(cmd, check=True)
    print(f"\n✓ ¡Compilación exitosa!")
    print(f"Ejecutable en: {os.path.join(dist_dir, 'ControlLego.exe')}")
except subprocess.CalledProcessError as e:
    print(f"\n✗ Error: {e}")