from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Axis, Color, Direction, Port
from pybricks.tools import wait
from pybricks.robotics import DriveBase

hub = PrimeHub(Axis.X, Axis.Z)

# --- CONFIGURAÇÕES ---

POTENCIA_ALVO = 90
PASSO_RAMPA   = 2

# --- MOTORES ---

motor_fl = Motor(Port.A) # Frente Esq
motor_fr = Motor(Port.B, Direction.COUNTERCLOCKWISE) # Frente Dir
motor_tl = Motor(Port.E, Direction.COUNTERCLOCKWISE) # Trás Esq
motor_tr = Motor(Port.F) # Trás Dir

robo = DriveBase(motor_tl, motor_tr, 59, 170)
robo.use_gyro(True)

# ==========================================
# --- FUNÇÕES DE SUPORTE ---
# ==========================================
# ----- LÓGICA MECANUM -----
# ==========================================

"de Ré"
def re_reto(p):

    """
    Lógica para andar de ré compensando o desvio à direita.
    Ajuste o fator_cotrmotor_trecao se ele ainda entortar:
    - Menor que 0.85: Esquerda fica mais fraca.
    - Maior que 0.85: Esquerda fica mais forte.
    """

    fator_cotrmotor_trecao = 0.75 
    motor_fl.dc(-(p * fator_cotrmotor_trecao)) 
    motor_tl.dc(p * fator_cotrmotor_trecao)    
    motor_fr.dc(p)                     
    motor_tr.dc(-p)

"Deslizar à esquerda"
def caranguejo_esq(p):
    motor_fl.dc(p+15)
    motor_fr.dc(-p)
    motor_tl.dc(p)
    motor_tr.dc(-p+15)

"Diagona à esquerda trás"
def diag_tl(p, n):
    motor_fl.dc(-(p/n))
    motor_fr.dc(-2*p)
    motor_tl.dc(-(p/n))
    motor_tr.dc(-2*p)

"Parar"
def parar():
    motor_fl.stop()
    motor_fr.stop()
    motor_tl.stop()
    motor_tr.stop()
    wait(500)


"Giro de correção de guinada"
def giro_correcao(p):
    erro = 2 # número qualquer maior que 1
    erro_min = 0.5
    while erro > erro_min or erro < -erro_min:
        ang = robo.angle()
        erro = 0 - ang

        if erro > erro_min:
            motor_fl.dc(-p)
            motor_fr.dc(p)
            motor_tl.dc(p)
            motor_tr.dc(-p)
            wait(5)
        elif erro < -erro_min:
            motor_fl.dc(p)
            motor_fr.dc(-p)
            motor_tl.dc(-p)
            motor_tr.dc(p)
            wait(5)
        else:
            break
        
    parar()
    robo.reset()

"Deslizar à direita"
def caranguejo_dir(p):
    motor_fl.dc(-p)
    motor_fr.dc(p)
    motor_tl.dc(-p)
    motor_tr.dc(p)

"Diagonal à direita trás"
def diag_tr(p, n):
    motor_fl.dc(-2*p)
    motor_fr.dc(-(p/n))
    motor_tl.dc(-2*p)
    motor_tr.dc(-(p/n))

# ==========================================
# --- EXECUÇÃO ---
# ==========================================

# PASSO 0: ESPERA INICIAL
hub.light.on(Color.RED) 
for i in range(54, -1, -1):
    print(f"Aguardando {i} segundos...")
    wait(1000)

# Sinal de início
hub.light.on(Color.ORANGE)
wait(500)

# ==========================================
# PASSO 1: CARANGUEJO PARA ESQUERDA
# ==========================================

caranguejo_esq(90)
wait(3800)
giro_correcao(30)

wait(5000)

# ==========================================
# PASSO 2: PARA TRÁS (METADE)
# ==========================================

diag_tl(150, 2)
wait(2500)
giro_correcao(30)

wait(3000)

# ==========================================
# PASSO 3: PARA TRÁS ATÉ CASTELO
# ==========================================

diag_tl(150, 5)
wait(2500)
giro_correcao(30)

# Medir o angulo atual do robo
# while True:
#     ang = robo.angle()
#     print(f'{ang:.2f}')
#     wait(20)
