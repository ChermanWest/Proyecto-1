# ControlMotores.py

LISTENER_SCRIPT = """
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port, Color
from pybricks.tools import wait
import usys as sys
import uselect

# -- CONFIGURACIÓN --
hub = PrimeHub()
hub.light.on(Color.ORANGE) 

motorA = None
motor_izq = None
motor_dir = None # Motor de dirección (Puerto C)

# Inicialización de motores de tracción
try:
    motorA = Motor(Port.A)  # Rueda derecha
except Exception: pass

try:
    motor_izq = Motor(Port.E)  # Rueda izquierda
except Exception: pass

# Inicialización del motor de dirección
try:
    motor_dir = Motor(Port.C)
    motor_dir.reset_angle(0)
except Exception: pass

# -- LOOP TIPO SOCKET --
hub.light.on(Color.GREEN) # Verde = LISTO

buffer = ""

while True:
    # Comprobación no bloqueante de datos
    ready = uselect.select([sys.stdin], [], [], 0)[0]
    
    if ready:
        char = sys.stdin.read(1)
        
        if char == ';':
            # Fin del comando
            cmd = buffer.strip()
            buffer = "" 
            
            if len(cmd) > 0:
                action = cmd[0] # F, B, S, L, R, Z
                
                # --- LÓGICA DE TRACCIÓN (F=Forward, B=Back, S=Stop) ---
                if action == 'S':
                    if motorA: motorA.stop()
                    if motor_izq: motor_izq.stop()
                    hub.light.on(Color.GREEN)
                    
                elif action == 'F' or action == 'B':
                    try:
                        val_part = cmd[1:]
                        if val_part == '': val_part = '0'
                        speed = int(val_part)
                        
                        if action == 'B':
                            speed = -speed
                        
                        if motorA: motorA.run(speed)
                        if motor_izq: motor_izq.run(-speed)
                        hub.light.on(Color.BLUE)
                    except ValueError:
                        pass

                # --- LÓGICA DE DIRECCIÓN (Puerto C) ---
                elif action in ['L', 'R', 'Z']:
                    if motor_dir:
                        try:
                            if action == 'L':
                                motor_dir.run_target(800, -30, wait=False)
                            elif action == 'R':
                                motor_dir.run_target(800, 30, wait=False)
                            elif action == 'Z':
                                motor_dir.run_target(800, 0, wait=False)
                        except Exception:
                            pass

        else:
            if char != '\\n' and char != '\\r':
                buffer += char
            
    wait(5)
"""