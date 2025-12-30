"""
auto.py
Rol arquitectura: robot (Hub LEGO) que asigna los nombrea a variables necesarias para controlar los motores.
"""

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait
import sys

# CONFIGURACIÓN DE MOTORES

hub = PrimeHub()

motor_der = Motor(Port.A)   # Rueda derecha
motor_izq = Motor(Port.E)   # Rueda izquierda
motor_dir = Motor(Port.C)   # Dirección

# Variables iniciales
Speed = 0
giro = 0

# BUCLE PRINCIPAL DE COMANDOS

while True:

    cmd = sys.stdin.readline()

    if not cmd:
        wait(10)
        continue
    cmd = cmd.strip()

