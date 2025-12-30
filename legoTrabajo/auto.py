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

motorA = Motor(Port.A)   # Rueda derecha
motor_izq = Motor(Port.E)   # Rueda izquierda
motor_dir = Motor(Port.C)   # Dirección

# Variables iniciales
velocidad = 0
giro = 0

def aplicar_giro():
    """ Mueve el motor de dirección según el slider (-100 a 100). """
    motor_dir.run_target(300, giro)

def mover_adelante():
    motorA.dc(velocidad)
    motor_izq.dc(velocidad)

def mover_atras():
    motorA.dc(-velocidad)
    motor_izq.dc(-velocidad)

def detener():
    motorA.stop()
    motor_izq.stop()

# BUCLE PRINCIPAL DE COMANDOS

while True:

    cmd = sys.stdin.readline()

    if not cmd:
        wait(10)
        continue
    cmd = cmd.strip()

