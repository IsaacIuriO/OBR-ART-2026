from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, ColorSensor, UltrasonicSensor
from pybricks.parameters import Port, Direction, Stop
from pybricks.robotics import DriveBase
from pybricks.tools import wait

# Hub
hub = PrimeHub()

# Motores
motor_esq = Motor(Port.E, Direction.COUNTERCLOCKWISE)
motor_dir = Motor(Port.F, Direction.CLOCKWISE)

# Sensores
sensor_esq = ColorSensor(Port.B)
sensor_dir = ColorSensor(Port.A)
ultra = UltrasonicSensor(Port.D)

# DriveBase
robo = DriveBase(
    motor_esq,
    motor_dir,
    wheel_diameter=63,
    axle_track=135
)

# Velocidade base
velocidade = 120

# Ganho de correção
KP = 1.2

# Vakir di verde
verde = [26, 27, 28, 29 ,30]


ultra.lights.off()
wait(5000)
ultra.lights.on()

while True:
    distance = ultra.distance()
    if distance <= 100:
        while True:

            # Leitura da reflexão
            esquerdo = sensor_esq.reflection()
            direito = sensor_dir.reflection()

            # Erro = diferença entre os sensores
            erro = esquerdo - direito

            # Correção proporcional
            correcao = erro * KP

            # Andar seguindo a linha
            robo.drive(velocidade, correcao)


            if esquerdo in verde and direito in verde:
                robo.brake()
                wait(100)
                break

        robo.drive(velocidade, correcao)
        wait(5500)
        robo.brake()
        wait(800)
        motor_dir.run(350)
        wait(1250)
        robo.drive(-160, correcao)
        wait(1500)
        robo.brake()
        break