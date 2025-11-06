from pybricks.pupdevices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait

# Initialize a motor on port A.
RueTraDerecha = Motor(Port.A)
RueTraIzquierda = Motor(Port.E)
RuedaDelantera = Motor(Port.C)

# Make the motor run clockwise at 500 degrees per second.
RueTraDerecha.run(500)
RueTraIzquierda.run(500)
RuedaDelantera.run(0)
# Wait for three seconds.
wait(3000)

# Make the motor run counterclockwise at 500 degrees per second.
RueTraDerecha.run(-500)
RueTraIzquierda.run(-500)
RuedaDelantera.run(0)

# Wait for three seconds.
wait(3000)

