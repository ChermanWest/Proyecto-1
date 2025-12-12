#!/usr/bin/env python


import subprocess
import sys
import os
import shutil

# Asegurarse de que PyInstaller está instalado
try:
    import PyInstaller
except ImportError:
    print("PyInstaller no está instalado. Instalando...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

# Directorio del script
script_dir = os.path.dirname(os.path.abspath(__file__))
main_py = os.path.join(script_dir, "Main.py")
dist_dir = os.path.join(script_dir, "dist")

# Limpiar directorios anteriores
for folder in ["build", "dist", ".spec"]:
    folder_path = os.path.join(script_dir, folder)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        print(f"Eliminado: {folder}")

# Comando PyInstaller simplificado
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",                                      # Un único ejecutable
    "--windowed",                                     # Sin consola (GUI puro)
    "--name", "ControlLego",                          # Nombre del ejecutable
    "--distpath", dist_dir,                           # Solo carpeta dist para el .exe
    "--hidden-import=customtkinter",
    "--hidden-import=Conexion",
    "--hidden-import=ControlMotores",
    "--hidden-import=Interfaz",
    "--hidden-import=pybricksdev",
    "--hidden-import=pybricksdev.ble",
    "--hidden-import=pybricksdev.connections",
    "--hidden-import=pybricksdev.connections.pybricks",
    "--hidden-import=bleak",
    "--hidden-import=asyncio",
    "--collect-all=pybricksdev",
    main_py
]

print(f"Compilando {main_py}...\n")

try:
    subprocess.run(cmd, check=True)
    
    # Limpiar archivos temporales de PyInstaller
    spec_file = os.path.join(script_dir, "ControlLego.spec")
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print("Eliminado: ControlLego.spec")
    
    build_dir = os.path.join(script_dir, "build")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
        print("Eliminado: carpeta build/")
    
    exe_path = os.path.join(dist_dir, "ControlLego.exe")
    print(f"\n✓ ¡Compilación exitosa!")
    print(f"Ejecutable: {exe_path}")
    print(f"Tamaño aproximado: {os.path.getsize(exe_path) / (1024**2):.1f} MB")
    
except subprocess.CalledProcessError as e:
    print(f"\n✗ Error durante la compilación: {e}")
    sys.exit(1)
