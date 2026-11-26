"""
Roda no NOTEBOOK (Windows).
Recebe o video do Raspberry (webcam do robo), reconhece cenario (CLIP) e pessoas (YOLO)
e toca videos COM SOM disparados por marcadores ArUco.

LAYOUT DA TELA (projetor):
  - Plano principal (tela cheia): a imagem C:\\shrek\\imagemfundo.jpg fica na tela e os videos tocam
    NESSE MESMO PLANO, so quando o robo enxerga o marcador ArUco. Quando o video acaba, a imagem volta.
  - Janelinha no canto superior esquerdo (~20% da tela): SEMPRE mostra a webcam do robo
    (com os efeitos Shrek e o contorno dos marcadores detectados).
    Quando ha pessoas, o rosto do Shrek (homem) ou da Fiona (mulher) e desenhado sobre a cabeca de cada
    uma, usando rosto_shrek.png e rosto_fiona.png (pasta C:\\shrek).

VIDEOS: C:\\shrek\\videos\\video 0.mp4 ... video 6.mp4
  Nada toca ate o robo ver um marcador. Cada marcador toca o SEU video na hora em que e visto,
  em qualquer ordem (nao precisa ter visto os anteriores):
  ArUco ID 0 -> video 0, ID 1 -> video 1, ... ID 6 -> video 6   (dicionario 6x6_250, arucogrid.com)
  Para mudar quais IDs disparam cada video, edite ARUCO_PARA_VIDEO.

Instalar: python -m pip install pygame imageio-ffmpeg
(o audio e extraido dos mp4 na 1a execucao e guardado em C:\\shrek\\videos\\_audio)

Teclas (clique na janela do video antes):
  0-6  pula direto para o video N (teste)   N  proximo video   R  reinicia (volta para a imagem de fundo)
  M  mostra/oculta os textos de status      E  liga/desliga efeitos na janelinha da webcam      Q  sair
  A S D F G H  forca cenario (floresta, agua, casa, castelo, estrada, interior)   X  cenario automatico
"""
import math
import os
import random
import subprocess
import threading
import time
from collections import Counter, deque

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import cv2
import numpy as np
import open_clip
import torch
from PIL import Image
from ultralytics import YOLO

try:
    import pygame
    import imageio_ffmpeg
    AUDIO_LIBS = True
except ImportError:
    AUDIO_LIBS = False

# ----------------------------- CONFIGURACAO -----------------------------
PI_URL = "http://redhammer.local:8080/video"   # IP do Raspberry
OUT_W, OUT_H = 1280, 720                    # resolucao de saida (a do projetor)
PROJECTOR_X = 1920      # largura da tela do notebook: a janela abre no 2o monitor (projetor)
CLIP_CONF = 0.35
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ---- Imagem de fundo, videos, som e marcadores ----
IMAGEM_FUNDO = r"C:\shrek\imagemfundo.jpg"   # fica na tela (no plano dos videos) ate um video comecar
VIDEO_DIR = r"C:\shrek\videos"
N_VIDEOS = 7            # video 0 ate video 6
LOOP_VIDEOS = False     # False: o video toca uma vez e a imagem de fundo volta | True: repete ate o proximo marcador
AUDIO = True            # toca o som dos videos
SO_NA_ORDEM = False     # False: cada marcador toca o seu video assim que e visto, em qualquer ordem | True: so aceita o seguinte (0, 1, 2...)
ARUCO_DICT = "DICT_6X6_250"  # mesmo dicionario do arucogrid.com (e do gerar_aruco.py)
# {ID do marcador ArUco: numero do video que ele dispara}. Nada toca ate o robo ver um marcador.
ARUCO_PARA_VIDEO = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}
ARUCO_CONFIRMACOES = 3  # quadros seguidos com o marcador visivel para confirmar
ARUCO_REARME = 2.0      # segundos sem ver o marcador para ele poder disparar o video de novo

# ---- Janelinha da webcam (canto superior esquerdo, sempre visivel) ----
JANELA_CAM_ESCALA = 0.20   # largura = 20% da largura da tela
JANELA_MARGEM = 20         # distancia da borda (pixels)
EFEITOS_NA_CAMERA = True   # efeitos Shrek (vagalumes, nevoa...) so dentro da janelinha (tecla E liga/desliga)
CONTORNO_ARUCO = True      # contorno verde nos marcadores que o robo enxerga

# ---- Rostos desenhados sobre as pessoas (na janelinha da webcam) ----
ROSTOS_DIR = r"C:\shrek"   # pasta com rosto_shrek.png e rosto_fiona.png
ROSTO_FIXO = None          # None = automatico (homem -> Shrek, mulher -> Fiona) | "shrek" ou "fiona" = o mesmo em todos
# olho_x/olho_y = ponto entre os olhos no PNG (0 a 1); dist_olhos = distancia entre os olhos / largura do PNG
# escala = ajuste fino do tamanho do rosto (maior = rosto maior)
ROSTOS = {
    "shrek": dict(arquivo="rosto_shrek.png", olho_x=0.484, olho_y=0.375, dist_olhos=0.308, escala=1.08),
    "fiona": dict(arquivo="rosto_fiona.png", olho_x=0.501, olho_y=0.541, dist_olhos=0.269, escala=1.2),
}

SCENES = {
    "floresta": "a photo of a forest with many trees",
    "agua":     "a photo of a lake, river or pond",
    "casa":     "a photo of a small house or cottage",
    "castelo":  "a photo of a castle or a big stone building",
    "estrada":  "a photo of a dirt road or path outdoors",
    "interior": "a photo of the inside of a room",
}
WASH = {
    "floresta": (6, 38, 12),
    "agua":     (10, 45, 20),
    "casa":     (0, 20, 45),
    "castelo":  (35, 25, 5),
    "estrada":  (5, 25, 10),
}
EFFECTS = {
    "floresta": dict(fireflies=45, fog=0.25),
    "agua":     dict(bubbles=25, fog=0.20),
    "casa":     dict(fireflies=12),
    "castelo":  dict(confetti=60),
    "estrada":  dict(fireflies=15, fog=0.10),
    "interior": dict(),
}
# ------------------------------------------------------------------------


def find_video(i):
    for name in (f"video {i}.mp4", f"video{i}.mp4", f"video_{i}.mp4",
                 f"Video {i}.mp4", f"Video{i}.mp4", f"Video_{i}.mp4"):
        p = os.path.join(VIDEO_DIR, name)
        if os.path.isfile(p):
            return p
    return None


def check_videos():
    print(f"Procurando videos em {VIDEO_DIR}")
    missing = False
    for i in range(N_VIDEOS):
        p = find_video(i)
        print(f"  video {i}: {'OK' if p else 'NAO ENCONTRADO'}")
        missing |= p is None
    if missing:
        try:
            print("  Arquivos que existem na pasta:", os.listdir(VIDEO_DIR))
        except OSError:
            print("  A pasta nao existe!")


def fit(frame):
    """Redimensiona mantendo proporcao, com barras pretas (preto nao ilumina no projetor)."""
    h, w = frame.shape[:2]
    s = min(OUT_W / w, OUT_H / h)
    nw, nh = max(int(w * s), 1), max(int(h * s), 1)
    canvas = np.zeros((OUT_H, OUT_W, 3), np.uint8)
    x, y = (OUT_W - nw) // 2, (OUT_H - nh) // 2
    canvas[y:y + nh, x:x + nw] = cv2.resize(frame, (nw, nh))
    return canvas


def load_background():
    """Imagem que fica na tela (no mesmo plano dos videos) enquanto nenhum video toca."""
    img = cv2.imread(IMAGEM_FUNDO)
    if img is None:
        print(f"[aviso] imagem nao encontrada: {IMAGEM_FUNDO} (o fundo ficara preto)")
        return np.zeros((OUT_H, OUT_W, 3), np.uint8)
    return fit(img)


class AudioPlayer:
    """Extrai o audio dos mp4 (ffmpeg embutido no imageio-ffmpeg) e toca com pygame."""

    def __init__(self):
        self.ok = False
        self.files = {}
        self.cur = None
        if not AUDIO:
            return
        if not AUDIO_LIBS:
            print("[aviso] SEM SOM: instale com  python -m pip install pygame imageio-ffmpeg")
            return
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            self.ok = True
        except pygame.error as e:
            print(f"[aviso] SEM SOM: nao consegui abrir a saida de audio ({e})")

    def prepare(self):
        if not self.ok or not os.path.isdir(VIDEO_DIR):
            return
        try:
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as e:
            print(f"[aviso] SEM SOM: ffmpeg indisponivel ({e})")
            self.ok = False
            return
        cache = os.path.join(VIDEO_DIR, "_audio")
        os.makedirs(cache, exist_ok=True)
        for i in range(N_VIDEOS):
            v = find_video(i)
            if v is None:
                continue
            wav = os.path.join(cache, f"{i}.wav")
            if not (os.path.isfile(wav) and os.path.getmtime(wav) >= os.path.getmtime(v)):
                print(f"  extraindo audio do video {i}...")
                r = subprocess.run(
                    [ffmpeg, "-y", "-i", v, "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", wav],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                )
                if r.returncode != 0 or not os.path.isfile(wav):
                    print(f"  [aviso] video {i}: sem faixa de audio ou falha ao extrair")
                    if os.path.isfile(wav):
                        os.remove(wav)
                    continue
            self.files[i] = wav

    def play(self, idx):
        self.cur = idx
        if not self.ok:
            return
        pygame.mixer.music.stop()
        wav = self.files.get(idx)
        if wav:
            try:
                pygame.mixer.music.load(wav)
                pygame.mixer.music.play()
            except pygame.error as e:
                print(f"[aviso] erro ao tocar audio do video {idx}: {e}")

    def stop(self):
        self.cur = None
        if self.ok:
            pygame.mixer.music.stop()

    def restart(self):
        if self.cur is not None:
            self.play(self.cur)

    def close(self):
        if self.ok:
            pygame.mixer.quit()


class Grabber(threading.Thread):
    """Le o stream o mais rapido possivel e guarda so o quadro mais recente."""

    def __init__(self, src):
        super().__init__(daemon=True)
        self.src, self.frame, self.lock = src, None, threading.Lock()
        self.n = 0  # contador de quadros novos

    def run(self):
        while True:
            cap = cv2.VideoCapture(self.src)
            while True:
                ok, f = cap.read()
                if not ok:
                    break
                with self.lock:
                    self.frame = f
                    self.n += 1
            cap.release()
            time.sleep(1)

    def get(self):
        with self.lock:
            return None if self.frame is None else self.frame.copy()


class ArucoReader(threading.Thread):
    """Procura marcadores ArUco no video da camera e converte o ID no numero do video."""

    def __init__(self, grabber):
        super().__init__(daemon=True)
        self.grabber = grabber
        dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, ARUCO_DICT))
        params = cv2.aruco.DetectorParameters()
        params.markerBorderBits = 1
        self.detector = cv2.aruco.ArucoDetector(dictionary, params)
        self.lock = threading.Lock()
        self.confirmed = []
        self.counts, self.last_seen = {}, {}
        self.active = set()  # marcadores que ja dispararam e continuam a vista
        self.boxes = []  # [(id, cantos normalizados)] para desenhar no preview
        self.last_n = -1

    def run(self):
        while True:
            if self.grabber.n == self.last_n:
                time.sleep(0.005)
                continue
            frame = self.grabber.get()
            self.last_n = self.grabber.n
            if frame is None:
                continue
            h, w = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = self.detector.detectMarkers(gray)
            found = {}  # numero do video -> (ID do marcador, cantos normalizados)
            if ids is not None:
                for c, mid in zip(corners, ids.flatten()):
                    v = ARUCO_PARA_VIDEO.get(int(mid))
                    if v is not None:
                        found[v] = (int(mid), c.reshape(4, 2) / [w, h])
            self.boxes = [(v, mid, pts) for v, (mid, pts) in found.items()]
            now = time.time()
            for i in found:
                self.counts[i] = self.counts.get(i, 0) + 1
                self.last_seen[i] = now
                if self.counts[i] >= ARUCO_CONFIRMACOES and i not in self.active:
                    self.active.add(i)  # so dispara de novo depois que sair de vista
                    with self.lock:
                        self.confirmed.append(i)
            for i in list(self.counts):
                if i not in found and now - self.last_seen.get(i, 0) > ARUCO_REARME:
                    self.counts[i] = 0
                    self.active.discard(i)

    def pop(self):
        with self.lock:
            codes, self.confirmed = self.confirmed, []
        return codes


class VideoPlayer:
    """Toca o mp4 em tempo real (sincronizado pelo relogio) junto com o audio."""

    def __init__(self, audio):
        self.audio = audio
        self.cap, self.frame, self.fps, self.start, self.pos = None, None, 30.0, 0.0, 0
        self.finished = False

    def stop(self):
        if self.cap is not None:
            self.cap.release()
        self.cap, self.frame, self.pos, self.finished = None, None, 0, False
        self.audio.stop()

    def play(self, idx):
        self.stop()
        self.audio.play(idx)
        path = find_video(idx)
        if path is None:
            print(f"[aviso] video {idx} nao encontrado em {VIDEO_DIR}")
            return
        self.cap = cv2.VideoCapture(path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.start = time.time()  # marcado logo depois de iniciar o audio

    @property
    def playing(self):
        return self.cap is not None and not self.finished

    def next_frame(self):
        """Quadro atual do video, ou None quando nao ha video tocando (mostra-se a imagem de fundo)."""
        if self.cap is None or self.finished:
            return None
        target = int((time.time() - self.start) * self.fps)
        while self.pos <= target:
            ok, f = self.cap.read()
            if not ok:
                if LOOP_VIDEOS:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.audio.restart()
                    self.start, self.pos = time.time(), 0
                    break
                self.finished = True
                return None
            self.frame = f
            self.pos += 1
        return self.frame


class Brain(threading.Thread):
    """Roda a IA de cenario/pessoas em segundo plano."""

    def __init__(self, grabber):
        super().__init__(daemon=True)
        self.grabber = grabber
        print("Carregando modelos...")
        self.yolo = YOLO("yolov8n-pose.pt")  # acha as pessoas e os pontos do rosto
        self.clip, _, self.preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        self.clip = self.clip.to(DEVICE).eval()
        tokenizer = open_clip.get_tokenizer("ViT-B-32")
        with torch.no_grad():
            t = self.clip.encode_text(tokenizer(list(SCENES.values())).to(DEVICE))
            self.text = t / t.norm(dim=-1, keepdim=True)
            g = self.clip.encode_text(tokenizer(["a photo of a man", "a photo of a woman"]).to(DEVICE))
            self.gtext = g / g.norm(dim=-1, keepdim=True)
        self.names = list(SCENES.keys())
        self.history = deque(maxlen=5)
        self.scene = "none"
        self.faces = []   # rostos a desenhar (lidos pela janelinha da webcam)
        self.tracks = []  # pessoas acompanhadas entre um quadro e outro

    def classify_scene(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = self.preprocess(Image.fromarray(rgb)).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            f = self.clip.encode_image(img)
            f = f / f.norm(dim=-1, keepdim=True)
            probs = (100.0 * f @ self.text.T).softmax(dim=-1)[0]
        idx = int(probs.argmax())
        self.history.append(self.names[idx] if float(probs[idx]) >= CLIP_CONF else "none")
        self.scene = Counter(self.history).most_common(1)[0][0]

    @staticmethod
    def head_geometry(box, kp=None, kc=None):
        """Acha a cabeca pelo esqueleto (olhos, orelhas) ou, se nao der, pela caixa da pessoa.
        Devolve (ex, ey, ed, ang): ponto entre os olhos (px), distancia entre os olhos (px), inclinacao (rad)."""
        if kp is not None and kc is not None:
            if kc[1] > 0.5 and kc[2] > 0.5:  # os dois olhos visiveis
                a, b = sorted((kp[1], kp[2]), key=lambda q: q[0])
                ed = float(math.hypot(b[0] - a[0], b[1] - a[1]))
                if ed > 3:
                    return (float(a[0] + b[0]) / 2, float(a[1] + b[1]) / 2, ed, math.atan2(b[1] - a[1], b[0] - a[0]))
            if kc[3] > 0.5 and kc[4] > 0.5:  # so as orelhas (cabeca de lado)
                a, b = sorted((kp[3], kp[4]), key=lambda q: q[0])
                hw = float(math.hypot(b[0] - a[0], b[1] - a[1]))
                if hw > 6:
                    ang = math.atan2(b[1] - a[1], b[0] - a[0])
                    return (float(a[0] + b[0]) / 2 + 0.04 * hw * math.sin(ang),
                            float(a[1] + b[1]) / 2 - 0.04 * hw * math.cos(ang), 0.42 * hw, ang)
        x1, y1, x2, y2 = box  # sem rosto visivel: estima pela caixa (cabeca no topo)
        hw = min(0.45 * (x2 - x1), 0.28 * (y2 - y1))
        return ((x1 + x2) / 2, y1 + 0.48 * hw, 0.42 * hw, 0.0)

    def read_people(self, res):
        boxes = res.boxes.xyxy.cpu().numpy() if res.boxes is not None else []
        kps = kcs = None
        try:
            if res.keypoints is not None and len(boxes):
                kps = res.keypoints.xy.cpu().numpy()
                kcs = (res.keypoints.conf.cpu().numpy() if res.keypoints.conf is not None
                       else np.ones(kps.shape[:2], np.float32))
        except Exception:
            kps = kcs = None
        people = []
        for i, b in enumerate(boxes):
            box = tuple(float(v) for v in b)
            geom = self.head_geometry(box, None if kps is None else kps[i], None if kcs is None else kcs[i])
            people.append((box, geom))
        return people

    def classify_gender(self, frame, boxes):
        """Probabilidade de ser mulher para cada pessoa, olhando a parte de cima do corpo (cabeca e tronco)."""
        imgs = []
        for x1, y1, x2, y2 in boxes:
            crop = frame[max(int(y1), 0):max(int(y1 + (y2 - y1) * 0.55), 1), max(int(x1), 0):max(int(x2), 1)]
            if crop.shape[0] < 4 or crop.shape[1] < 4:
                crop = np.full((32, 32, 3), 127, np.uint8)
            h, w = crop.shape[:2]
            side = max(h, w)
            top, left = (side - h) // 2, (side - w) // 2
            sq = cv2.copyMakeBorder(crop, top, side - h - top, left, side - w - left,
                                    cv2.BORDER_CONSTANT, value=(127, 127, 127))
            imgs.append(self.preprocess(Image.fromarray(cv2.cvtColor(sq, cv2.COLOR_BGR2RGB))))
        batch = torch.stack(imgs).to(DEVICE)
        with torch.no_grad():
            f = self.clip.encode_image(batch)
            f = f / f.norm(dim=-1, keepdim=True)
            probs = (100.0 * f @ self.gtext.T).softmax(dim=-1)[:, 1]
        return [float(v) for v in probs.cpu().numpy()]

    def update_tracks(self, people, frame):
        """Acompanha cada pessoa entre os quadros: suaviza a posicao do rosto e decide Shrek ou Fiona."""
        h, w = frame.shape[:2]
        now = time.time()
        used = set()
        for box, geom in people:
            cx, cy = (box[0] + box[2]) / 2 / w, (box[1] + box[3]) / 2 / h
            best, best_d = None, 0.25
            for t in self.tracks:
                if id(t) not in used:
                    d = math.hypot(t["cx"] - cx, t["cy"] - cy)
                    if d < best_d:
                        best, best_d = t, d
            if best is None:
                best = {"pw": None, "who": ROSTO_FIXO, "cls_t": 0.0, "geom": geom}
                self.tracks.append(best)
            else:  # suaviza para o rosto nao tremer
                best["geom"] = tuple(0.5 * a + 0.5 * b for a, b in zip(best["geom"], geom))
            best.update(cx=cx, cy=cy, box=box, seen=now)
            used.add(id(best))
        self.tracks = [t for t in self.tracks if now - t["seen"] < 1.0]

        if ROSTO_FIXO is None:  # homem ou mulher, a cada ~0,7 s, so para as 4 maiores pessoas
            due = [t for t in self.tracks if t["seen"] == now and now - t["cls_t"] > 0.7]
            due.sort(key=lambda t: -(t["box"][2] - t["box"][0]) * (t["box"][3] - t["box"][1]))
            due = due[:4]
            if due:
                for t, p in zip(due, self.classify_gender(frame, [t["box"] for t in due])):
                    t["cls_t"] = now
                    t["pw"] = p if t["pw"] is None else 0.6 * t["pw"] + 0.4 * p
                    if t["who"] is None:
                        t["who"] = "fiona" if t["pw"] > 0.5 else "shrek"
                    elif t["who"] == "shrek" and t["pw"] > 0.62:  # histerese: nao fica trocando
                        t["who"] = "fiona"
                    elif t["who"] == "fiona" and t["pw"] < 0.38:
                        t["who"] = "shrek"

        self.faces = [
            dict(ex=t["geom"][0] / w, ey=t["geom"][1] / h, ed=t["geom"][2] / w, ang=t["geom"][3], who=t["who"])
            for t in self.tracks if t["who"] and t["seen"] == now
        ]

    def run(self):
        last_clip = 0.0
        while True:
            frame = self.grabber.get()
            if frame is None:
                time.sleep(0.05)
                continue
            res = self.yolo(frame, verbose=False, conf=0.5)[0]
            self.update_tracks(self.read_people(res), frame)
            if time.time() - last_clip > 1.0:
                self.classify_scene(frame)
                last_clip = time.time()


class Effects:
    """Efeitos de 'pantano', desenhados na resolucao w x h da janelinha da webcam."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.k = max(w / 1280.0, 0.5)               # escala dos elementos (tamanho/velocidade)
        self.dens = min(1.0, 0.25 + w / 1280.0)     # menos particulas numa janela pequena
        self.ff, self.bb, self.cf = [], [], []
        small = np.random.rand(9, 16).astype(np.float32)
        self.noise = np.clip(cv2.resize(small, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC), 0, 1)

    def fog(self, layer, strength, t):
        w, h = self.w, self.h
        ox = int(w / 2 + w / 2 * math.sin(t * 0.07))
        oy = int(h / 2 + h / 2 * math.cos(t * 0.05))
        g = self.noise[oy:oy + h, ox:ox + w] ** 2 * strength * 255
        cv2.add(layer, np.dstack([g * 0.8, g, g * 0.7]).astype(np.uint8), dst=layer)

    def fireflies(self, layer, n, t):
        w, h, k = self.w, self.h, self.k
        while len(self.ff) < n:
            self.ff.append([random.uniform(0, w), random.uniform(0, h),
                            random.uniform(0, 6.28), random.uniform(0, 6.28)])
        del self.ff[n:]
        if not self.ff:
            return
        glow = np.zeros_like(layer)
        r = max(1, int(round(3 * k)))
        for p in self.ff:
            p[2] += random.uniform(-0.3, 0.3)
            p[0] = (p[0] + math.cos(p[2]) * 1.5 * k) % w
            p[1] = (p[1] + math.sin(p[2]) * 1.5 * k) % h
            b = 0.5 + 0.5 * math.sin(t * 3 + p[3])
            cv2.circle(glow, (int(p[0]), int(p[1])), r, (int(80 * b), int(255 * b), int(220 * b)), -1)
        halo = cv2.convertScaleAbs(cv2.GaussianBlur(glow, (0, 0), max(1.0, 6 * k)), alpha=3)
        cv2.add(layer, cv2.add(glow, halo), dst=layer)

    def bubbles(self, layer, n, t):
        w, h, k = self.w, self.h, self.k
        while len(self.bb) < n:
            self.bb.append([random.uniform(0, w), random.uniform(0, h),
                            max(2, int(random.randint(4, 18) * k)), random.uniform(1, 3) * k])
        del self.bb[n:]
        for b in self.bb:
            b[1] -= b[3]
            b[0] += math.sin(t * 2 + b[2]) * 0.7 * k
            if b[1] < -20 * k:
                b[0], b[1] = random.uniform(0, w), h + 20 * k
            cv2.circle(layer, (int(b[0]), int(b[1])), b[2], (120, 220, 160), 1, cv2.LINE_AA)

    def confetti(self, layer, n, t):
        w, h, k = self.w, self.h, self.k
        palette = [(60, 60, 255), (60, 220, 255), (255, 160, 60), (90, 255, 120)]
        while len(self.cf) < n:
            self.cf.append([random.uniform(0, w), random.uniform(0, h),
                            random.uniform(2, 5) * k, random.choice(palette)])
        del self.cf[n:]
        rw, rh = max(2, int(6 * k)), max(3, int(10 * k))
        for c in self.cf:
            c[1] += c[2]
            c[0] += math.sin(t * 2 + c[2]) * 1.5 * k
            if c[1] > h + 10:
                c[0], c[1] = random.uniform(0, w), -10
            x, y = int(c[0]), int(c[1])
            cv2.rectangle(layer, (x, y), (x + rw, y + rh), c[3], -1)

    def render(self, scene, t):
        cfg = EFFECTS.get(scene, {})

        def count(key):
            return max(1, int(cfg[key] * self.dens)) if cfg.get(key) else 0

        layer = np.zeros((self.h, self.w, 3), np.uint8)
        layer[:] = WASH.get(scene, (0, 0, 0))
        if "fog" in cfg:
            self.fog(layer, cfg["fog"], t)
        self.fireflies(layer, count("fireflies"), t)
        self.bubbles(layer, count("bubbles"), t)
        self.confetti(layer, count("confetti"), t)
        return layer


def window_size(fw, fh):
    """Tamanho da janelinha da webcam: 20% da largura da tela, mantendo a proporcao da camera."""
    cw = int(OUT_W * JANELA_CAM_ESCALA)
    ch = max(int(cw * fh / fw), 1)
    if ch > OUT_H * 0.35:
        ch = int(OUT_H * 0.35)
        cw = max(int(ch * fw / fh), 1)
    return cw, ch


def load_sprites():
    """Carrega os PNGs dos rostos (com transparencia) ja multiplicados pelo alfa, para misturar sem halo."""
    sprites = {}
    for nome, cfg in ROSTOS.items():
        path = os.path.join(ROSTOS_DIR, cfg["arquivo"])
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None or img.ndim < 3 or img.shape[2] != 4:
            print(f"[aviso] rosto nao encontrado (ou sem transparencia): {path}")
            continue
        if max(img.shape[:2]) > 640:
            k = 640 / max(img.shape[:2])
            img = cv2.resize(img, (int(img.shape[1] * k), int(img.shape[0] * k)), interpolation=cv2.INTER_AREA)
        pm = img.copy()
        pm[..., :3] = (img[..., :3].astype(np.float32) * img[..., 3:4] / 255.0).astype(np.uint8)
        sprites[nome] = dict(img=pm, **cfg)
    return sprites


def draw_faces(win, faces, sprites):
    """Desenha o rosto do Shrek / Fiona sobre cada cabeca, alinhado pelos olhos e inclinado como a cabeca."""
    ch, cw = win.shape[:2]
    for f in faces:
        sp = sprites.get(f["who"])
        if sp is None:
            continue
        ed = f["ed"] * cw  # distancia entre os olhos, em pixels da janelinha
        if ed < 2.0:
            continue
        pm = sp["img"]
        h0, w0 = pm.shape[:2]
        sc = ed / (sp["dist_olhos"] * w0) * sp["escala"]
        tw, th = max(int(w0 * sc), 2), max(int(h0 * sc), 2)
        if tw > 3 * cw:
            continue
        small = cv2.resize(pm, (tw, th), interpolation=cv2.INTER_AREA)
        ax, ay = sp["olho_x"] * tw, sp["olho_y"] * th
        c, sn = math.cos(f["ang"]), math.sin(f["ang"])
        ex, ey = f["ex"] * cw, f["ey"] * ch
        m = np.float32([[c, -sn, ex - (c * ax - sn * ay)], [sn, c, ey - (sn * ax + c * ay)]])
        warped = cv2.warpAffine(small, m, (cw, ch), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        a = warped[..., 3:4].astype(np.float32) / 255.0
        win[:] = np.clip(win.astype(np.float32) * (1.0 - a) + warped[..., :3], 0, 255).astype(np.uint8)


def put(img, text, y, x=20, scale=0.8):
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 2, cv2.LINE_AA)


def main():
    check_videos()
    audio = AudioPlayer()
    audio.prepare()
    grabber = Grabber(PI_URL)
    grabber.start()
    brain = Brain(grabber)
    brain.start()
    aruco = ArucoReader(grabber)
    aruco.start()
    player = VideoPlayer(audio)
    background = load_background()
    sprites = load_sprites()
    fx = None

    names = list(SCENES.keys())
    scene_keys = "asdfgh"
    manual_scene = None
    current = None  # None = nenhum video ainda: a imagem de fundo fica na tela
    effects_on = EFEITOS_NA_CAMERA
    show_status = True
    msg, msg_t = "", 0.0

    cv2.namedWindow("MR", cv2.WINDOW_NORMAL)
    cv2.moveWindow("MR", PROJECTOR_X, 0)
    cv2.setWindowProperty("MR", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    t0 = time.time()
    while True:
        t = time.time() - t0

        # --- gatilhos ArUco: o robo viu um marcador ---
        for code in aruco.pop():
            if code == current and (SO_NA_ORDEM or player.playing):
                continue  # mesmo marcador: ignora enquanto o proprio video ainda esta tocando
            proximo = 0 if current is None else current + 1
            if not SO_NA_ORDEM or code == proximo:
                current = code
                player.play(current)
                new_msg = f"ArUco detectado -> video {code}"
            else:
                new_msg = f"ArUco {code} ignorado (esperando o {proximo})"
            print(new_msg)
            msg, msg_t = new_msg, time.time()

        scene = manual_scene or brain.scene

        # --- plano principal: video tocando, ou a imagem de fundo ---
        vid = player.next_frame()
        out = fit(vid) if vid is not None else background.copy()

        # --- janelinha da webcam (canto superior esquerdo, sempre visivel) ---
        frame = grabber.get()
        if frame is not None:
            fh, fw = frame.shape[:2]
            cw, ch = window_size(fw, fh)
            win = cv2.resize(frame, (cw, ch))
            if effects_on:
                if fx is None or (fx.w, fx.h) != (cw, ch):
                    fx = Effects(cw, ch)
                cv2.add(win, fx.render(scene, t), dst=win)
                draw_faces(win, brain.faces, sprites)
            if CONTORNO_ARUCO:
                for v, mid, pts in aruco.boxes:
                    q = (pts * [cw, ch]).astype(np.int32)
                    cv2.polylines(win, [q], True, (0, 255, 0), 2)
                    cv2.putText(win, f"ID {mid}", (int(q[0][0]), max(int(q[0][1]) - 4, 12)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)
        else:
            cw = int(OUT_W * JANELA_CAM_ESCALA)
            ch = cw * 3 // 4
            win = np.full((ch, cw, 3), 40, np.uint8)
            cv2.putText(win, "sem camera", (12, ch // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        x0 = y0 = JANELA_MARGEM
        out[y0:y0 + ch, x0:x0 + cw] = win
        cv2.rectangle(out, (x0 - 3, y0 - 3), (x0 + cw + 2, y0 + ch + 2), (255, 255, 255), 3)

        if show_status:
            atual = "nenhum" if current is None else str(current)
            put(out, f"cenario: {scene} | video: {atual}", OUT_H - 30)
            if time.time() - msg_t < 3:
                put(out, msg, OUT_H - 70)

        cv2.imshow("MR", out)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("m"):
            show_status = not show_status
        elif key == ord("e"):
            effects_on = not effects_on
        elif key == ord("r"):  # volta ao inicio: imagem de fundo, esperando o ID 0
            current = None
            player.stop()
            msg, msg_t = "reiniciado: esperando um ArUco", time.time()
        elif key == ord("n"):
            current = 0 if current is None else min(current + 1, N_VIDEOS - 1)
            player.play(current)
        elif ord("0") <= key < ord("0") + N_VIDEOS:
            current = key - ord("0")
            player.play(current)
        elif key == ord("x"):
            manual_scene = None
        elif key != 255 and chr(key) in scene_keys and scene_keys.index(chr(key)) < len(names):
            manual_scene = names[scene_keys.index(chr(key))]
    cv2.destroyAllWindows()
    player.stop()
    audio.close()


if __name__ == "__main__":
    main()
