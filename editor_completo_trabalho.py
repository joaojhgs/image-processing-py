import sys
from PyQt5.QtWidgets import (
    QApplication, QLabel, QMainWindow, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QMessageBox, QInputDialog
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
from PIL import Image
import os

class ImageProcessor:
    """
    Classe responsável por manipular imagens como matrizes de pixels RGB,
    oferecendo métodos de leitura, escrita e transformação.
    """
    def __init__(self):
        # Imagem original carregada
        self.original = None
        # Imagem resultante após transformações
        self.resultado = None
        # Frames gerados para animações (transparência e mistura)
        self.alpha_frames = []
        self.alpha_index = 0
        # Segunda imagem para mistura
        self.second_image = None

    def carregar_imagem(self, caminho):
        """
        Carrega uma imagem de arquivo (PNG, JPG, WEBP) ou PPM P3.
        Converte em matriz de tuplas RGB.
        """
        ext = os.path.splitext(caminho)[1].lower()
        if ext == '.ppm':
            img = self.carregar_ppm_p3(caminho)
        else:
            # Usa PIL para formatos comuns e converte para RGB
            img_pil = Image.open(caminho).convert("RGB")
            largura, altura = img_pil.size
            pixels = list(img_pil.getdata())
            # Constrói matriz 2D de pixels
            img = [
                [pixels[i * largura + j] for j in range(largura)]
                for i in range(altura)
            ]
        self.original = img
        self.resultado = [linha.copy() for linha in img]
        return img

    def carregar_ppm_p3(self, caminho):
        """
        Lê imagem PPM tipo P3 (ASCII) manualmente, retornando matriz RGB.
        """
        with open(caminho, 'r') as f:
            # Verifica cabeçalho
            if f.readline().strip() != 'P3':
                raise ValueError("Formato inválido. Apenas P3 suportado.")
            # Lê dimensões e descarta valor máximo
            largura, altura = map(int, f.readline().split())
            f.readline()
            dados = list(map(int, f.read().split()))
        img = []
        for i in range(altura):
            linha = []
            for j in range(largura):
                idx = (i * largura + j) * 3
                linha.append((dados[idx], dados[idx+1], dados[idx+2]))
            img.append(linha)
        return img

    def salvar_imagem(self, caminho):
        """
        Salva matriz `resultado` em formatos suportados pelo PIL (PNG, JPG, etc.).
        """
        altura, largura = len(self.resultado), len(self.resultado[0])
        img = Image.new("RGB", (largura, altura))
        pixels = [p for linha in self.resultado for p in linha]
        img.putdata(pixels)
        img.save(caminho)

    def salvar_ppm_p3(self, caminho):
        """
        Exporta `resultado` em arquivo PPM texto (P3).
        """
        with open(caminho, 'w') as f:
            altura, largura = len(self.resultado), len(self.resultado[0])
            # Cabeçalho
            f.write(f"P3\n{largura} {altura}\n255\n")
            # Dados RGB
            for linha in self.resultado:
                linha_str = ' '.join(f"{r} {g} {b}" for (r, g, b) in linha)
                f.write(linha_str + "\n")
    
    def restaurar_original(self):
        """
        Restaura a imagem original e limpa quaisquer animações em andamento.
        """
        self.resultado = [linha.copy() for linha in self.original]
        self.alpha_frames.clear()
        self.alpha_index = 0

    def aplicar_espelhamento_horizontal(self):
        """
        Inverte a imagem da esquerda para direita.
        """
        self.resultado = [linha[::-1] for linha in self.resultado]

    def aplicar_espelhamento_vertical(self):
        """
        Inverte a imagem de cima para baixo.
        """
        self.resultado = self.resultado[::-1]

    def rotacionar_direita(self):
        """
        Rotaciona 90 graus no sentido horário.
        """
        h, w = len(self.resultado), len(self.resultado[0])
        nova = [[None] * h for _ in range(w)]
        # Para cada pixel (i, j), coloca-o na posição rotacionada 90° horário:
        # O pixel da linha i e coluna j vai para a linha j e coluna (h - 1 - i) na nova matriz.
        for i in range(h):
            for j in range(w):
                nova[j][h - 1 - i] = self.resultado[i][j]
        self.resultado = nova

    def rotacionar_esquerda(self):
        """
        Rotaciona 90 graus no sentido anti-horário.
        """
        h, w = len(self.resultado), len(self.resultado[0])
        nova = [[None] * h for _ in range(w)]
        # Para cada pixel (i, j), coloca-o na posição rotacionada 90° anti-horário:
        # O pixel da linha i e coluna j vai para a linha (w - 1 - j) e coluna i na nova matriz.
        for i in range(h):
            for j in range(w):
                nova[w - 1 - j][i] = self.resultado[i][j]
        self.resultado = nova

    def segmentar_por_cor(self, alvo_rgb, tolerancia=30):
        """
        Segmenta mantendo pixels com cor próxima a `alvo_rgb`.
        Pixels fora da tolerância tornam-se pretos.
        """
        def cor_proxima(p):
            return all(abs(p[i] - alvo_rgb[i]) <= tolerancia for i in range(3))
        self.resultado = [
            [(p if cor_proxima(p) else (0, 0, 0)) for p in linha]
            for linha in self.resultado
        ]

    def aplicar_transparencia_preto(self):
        """
        Gera `alpha_frames` para animação de fade de preto até a original.
        """
        self.alpha_frames.clear()
        # Criar 6 frames: de 0% até 100% de revelação
        for k in range(6):
            a = k / 5.0
            frame = [
                [(int(p[0] * a), int(p[1] * a), int(p[2] * a)) for p in linha]
                for linha in self.original
            ]
            self.alpha_frames.append(frame)
        # Define primeiro frame (tudo preto)
        self.resultado = self.alpha_frames[0]
        self.alpha_index = 0

    def avancar_transparencia(self):
        """
        Avança para o próximo frame da animação de transparência.
        """
        if not self.alpha_frames:
            return
        self.alpha_index = (self.alpha_index + 1) % len(self.alpha_frames)
        self.resultado = self.alpha_frames[self.alpha_index]

    def preparar_mistura(self, caminho2):
        """
        Carrega segunda imagem para posterior mistura gradual.
        """
        img2 = Image.open(caminho2).convert("RGB")
        w, h = img2.size
        pix2 = list(img2.getdata())
        self.second_image = [
            [pix2[i * w + j] for j in range(w)]
            for i in range(h)
        ]

    def aplicar_mistura(self):
        """
        Gera `alpha_frames` interpolando entre `original` e `second_image`.
        """
        if self.second_image is None:
            raise ValueError("Carregue segunda imagem antes de misturar.")
        im1, im2 = self.original, self.second_image
        h, w = len(im1), len(im1[0])
        self.alpha_frames.clear()
        # 11 frames de alpha 0.0 a 1.0
        for k in range(11):
            a = k / 10.0
            # R’ = R1*(1-α) + R2*α
            # G’ = G1*(1-α) + G2*α
            # B’ = B1*(1-α) + B2*α
            frame = [
                [
                    (
                        int(im1[i][j][0] * (1 - a) + im2[i][j][0] * a),
                        int(im1[i][j][1] * (1 - a) + im2[i][j][1] * a),
                        int(im1[i][j][2] * (1 - a) + im2[i][j][2] * a)
                    )
                    for j in range(w)
                ]
                for i in range(h)
            ]
            self.alpha_frames.append(frame)
        self.resultado = self.alpha_frames[0]
        self.alpha_index = 0

    def exibir_em_qimage(self, imagem):
        """
        Converte matriz RGB em QImage para exibição no Qt.
        """
        h, w = len(imagem), len(imagem[0])
        qimage = QImage(w, h, QImage.Format_RGB888)
        for y in range(h):
            for x in range(w):
                r, g, b = imagem[y][x]
                qimage.setPixel(x, y, (r << 16) + (g << 8) + b)
        return qimage

class MainWindow(QMainWindow):
    """
    Janela principal que integra UI e ImageProcessor.
    Permite abrir, aplicar filtros, animar e exportar imagens.
    """
    def __init__(self):
        super().__init__()
        self.processor = ImageProcessor()
        self.setWindowTitle("Editor Trabalho CG")
        self.resize(1000, 550)
        self.init_ui()

    def init_ui(self):
        # Labels para mostrar as imagens
        self.lbl_orig = QLabel("Original")
        self.lbl_res  = QLabel("Resultado")
        for lbl in (self.lbl_orig, self.lbl_res):
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(450, 450)

        # Botões de controle
        btn_open  = QPushButton("Abrir Imagem")
        btn_open.clicked.connect(self.open_image)
        btn_second = QPushButton("Carregar 2ª Imagem")
        btn_second.clicked.connect(self.load_second)
        btn_save  = QPushButton("Exportar Imagem")
        btn_save.clicked.connect(self.save_image)
        btn_rest  = QPushButton("Restaurar Original")
        btn_rest.clicked.connect(self.restore_image)
        btn_next  = QPushButton("Avançar Animação")
        btn_next.clicked.connect(self.next_frame)

        # ComboBox de filtros
        self.cmb = QComboBox()
        self.cmb.addItems([
            "Selecione Filtro",
            "Transparência Preto",
            "Espelhar Horizontal",
            "Espelhar Vertical",
            "Rotacionar 90° Horário",
            "Rotacionar 90° Anti-horário",
            "Misturar Imagens",
            "Segmentar Cor"
        ])
        self.cmb.currentIndexChanged.connect(self.apply_filter)

        # Layout principal
        h1 = QHBoxLayout()
        h1.addWidget(self.lbl_orig)
        h1.addWidget(self.lbl_res)

        h2 = QHBoxLayout()
        for w in (btn_open, btn_second, btn_save, btn_rest, btn_next, self.cmb):
            h2.addWidget(w)

        v = QVBoxLayout()
        v.addLayout(h1)
        v.addLayout(h2)

        container = QWidget()
        container.setLayout(v)
        self.setCentralWidget(container)

    def open_image(self):
        """
        Abre diálogo e carrega a imagem selecionada.
        """
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir Imagem", "", "Imagens (*.png *.jpg *.jpeg *.webp *.ppm)"
        )
        if path:
            self.processor.carregar_imagem(path)
            self.update_display()

    def load_second(self):
        """
        Abre diálogo para carregar a segunda imagem para mistura.
        """
        path, _ = QFileDialog.getOpenFileName(
            self, "Carregar 2ª Imagem", "", "Imagens (*.png *.jpg *.jpeg *.webp *.ppm)"
        )
        if path:
            self.processor.preparar_mistura(path)

    def update_display(self):
        """
        Atualiza os QLabels com original e resultado.
        """
        img1 = self.processor.exibir_em_qimage(self.processor.original)
        img2 = self.processor.exibir_em_qimage(self.processor.resultado)
        self.lbl_orig.setPixmap(
            QPixmap.fromImage(img1).scaled(450, 450, Qt.KeepAspectRatio)
        )
        self.lbl_res.setPixmap(
            QPixmap.fromImage(img2).scaled(450, 450, Qt.KeepAspectRatio)
        )

    def save_image(self):
        """
        Exporta imagem resultado para arquivo.
        """
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Imagem", "", "Todos os formatos (*.png *.jpg *.bmp *.gif *.ppm)"
        )
        if path:
            if path.lower().endswith('.ppm'):
                self.processor.salvar_ppm_p3(path)
            else:
                self.processor.salvar_imagem(path)

    def restore_image(self):
        """
        Restaura a imagem original.
        """
        self.processor.restaurar_original()
        self.update_display()

    def apply_filter(self, idx):
        """
        Aplica o filtro selecionado no ComboBox.
        """
        if self.processor.original is None or idx == 0:
            return
        if idx == 1:
            self.processor.aplicar_transparencia_preto()
        elif idx == 2:
            self.processor.aplicar_espelhamento_horizontal()
        elif idx == 3:
            self.processor.aplicar_espelhamento_vertical()
        elif idx == 4:
            self.processor.rotacionar_direita()
        elif idx == 5:
            self.processor.rotacionar_esquerda()
        elif idx == 6:
            self.processor.aplicar_mistura()
        elif idx == 7:
            # Solicita cor ao usuário
            texto, ok = QInputDialog.getText(
                self, "Segmentar Cor", "Digite a cor RGB (ex: 255,0,0):"
            )
            if ok:
                try:
                    rgb = tuple(map(int, texto.split(',')))
                    self.processor.segmentar_por_cor(rgb)
                except:
                    QMessageBox.warning(
                        self, "Erro", "Formato inválido. Use R,G,B."
                    )
        self.update_display()
        # Reseta seleção
        self.cmb.setCurrentIndex(0)

    def next_frame(self):
        """
        Avança para próximo frame em animações de transparência/mistura.
        """
        self.processor.avancar_transparencia()
        self.update_display()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
