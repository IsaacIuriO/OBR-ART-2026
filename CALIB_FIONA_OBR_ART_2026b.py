from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, ColorSensor, UltrasonicSensor
from pybricks.parameters import Button, Color, Direction, Port, Side, Stop
from pybricks.robotics import DriveBase
from pybricks.tools import wait, StopWatch

hub = PrimeHub()

# Motores (Esq na F, Dir na E)
motor_esq = Motor(Port.F, Direction.CLOCKWISE)
motor_dir = Motor(Port.E, Direction.COUNTERCLOCKWISE)

# Sensores
ultra = UltrasonicSensor(Port.D)
sensor = ColorSensor(Port.A)
cdir = ColorSensor(Port.B)

# HSV das cores: preto e branco
Color.WHITE = Color(h=206, s=35, v=8)
Color.BLACK = Color(h=120, s=0, v=0)

# Joga esses valores em uma lista
minhas_cores = [Color.BLACK, Color.WHITE]

# Joga a lista para o spike obter os novos valores
sensor.detectable_colors(minhas_cores)

while True:
    
    # Lê o hsv
    hsv = sensor.hsv(surface=False)
    
    # Lê a cor
    color = sensor.color(surface=False)

    # Lê a luz ambiente
    ambient = sensor.ambient()

    # Lê a luz refletida
    reflection = sensor.reflection()

    print(reflection)

    wait(100)

# TESTES
# Color.GREEN = Color(h=170, s=70, v=1)
# Color.WHITE = Color(h=204, s=44, v=8)
# Color.BLACK = Color(h=220, s=0, v=0)

# # Joga esses valores em uma lista
# minhas_cores = [Color.BLACK, Color.WHITE, Color.GREEN]

# # Joga a lista para o spike obter os novos valores
# sensor.detectable_colors(minhas_cores)