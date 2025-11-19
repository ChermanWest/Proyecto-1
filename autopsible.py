from pybricks.pupdevices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait
import tkinter as tk
from tkinter import ttk

RueTraDerecha = Motor(Port.A)
RueTraIzquierda = Motor(Port.E)
RuedaDelantera = Motor(Port.C)

def mover_adelante():
    vel = velocidad.get() * 10
    giro_val = giro.get()
    RueTraDerecha.run(vel - giro_val * 5)
    RueTraIzquierda.run(vel + giro_val * 5)
    RuedaDelantera.run(giro_val * 5)

def mover_atras():
    vel = velocidad.get() * 10
    giro_val = giro.get()
    RueTraDerecha.run(-vel + giro_val * 5)
    RueTraIzquierda.run(-vel - giro_val * 5)
    RuedaDelantera.run(giro_val * 5)

def detener():
    RueTraDerecha.stop()
    RueTraIzquierda.stop()
    RuedaDelantera.stop()

ventana = tk.Tk()
ventana.title("Control Pybricks + Tkinter")

tk.Label(ventana, text="Velocidad (0–100)").pack()
velocidad = tk.Scale(ventana, from_=0, to=100, orient="horizontal")
velocidad.set(50)
velocidad.pack(padx=10, pady=5)

tk.Label(ventana, text="Giro (-100 a 100)").pack()
giro = tk.Scale(ventana, from_=-100, to=100, orient="horizontal")
giro.set(0)
giro.pack(padx=10, pady=5)

frame_botones = tk.Frame(ventana)
frame_botones.pack(pady=10)

btn_adelante = ttk.Button(frame_botones, text="Adelante", command=mover_adelante)
btn_adelante.grid(row=0, column=0, padx=10)

btn_atras = ttk.Button(frame_botones, text="Atrás", command=mover_atras)
btn_atras.grid(row=0, column=1, padx=10)

btn_detener = ttk.Button(frame_botones, text="Detener", command=detener)
btn_detener.grid(row=0, column=2, padx=10)

ventana.mainloop()
