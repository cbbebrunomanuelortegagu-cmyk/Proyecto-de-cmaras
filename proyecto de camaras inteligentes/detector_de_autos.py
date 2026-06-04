import cv2
from ultralytics import YOLO
import time
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# ============================================================
# CLASE PADRE: Manejo basico de hardware
# ============================================================
class CamaraBase:
    def __init__(self, indice_camara=0):
        self.cap = cv2.VideoCapture(indice_camara)
        if not self.cap.isOpened():
            print("Error: No se pudo acceder a la camara.")
        else:
            print(f"Camara {indice_camara} conectada correctamente.")

    def leer_frame(self):
        ret, frame = self.cap.read()
        return ret, frame

    def apagar(self):
        self.cap.release()
        cv2.destroyAllWindows()
        print("Camara apagada y recursos liberados.")


# ============================================================
# CLASE HIJA: Hereda la camara y le suma IA + Zona Prohibida
# ============================================================
class CamaraInteligente(CamaraBase):

    # ── Segundos que debe permanecer en zona para generar multa ──
    SEGUNDOS_LIMITE = 10

    def __init__(self, indice_camara=0, modelo_yolo='yolov8s.pt'):
        super().__init__(indice_camara)

        print("Cargando modelo YOLOv8s... por favor espera.")
        self.modelo = YOLO(modelo_yolo)
        print("Modelo cargado!\n")

        # ── Clases COCO ──
        self.clases_objetivo = [2, 3, 5, 7]
        self.confianza        = 0.35
        self.etiquetas        = {2: "Auto", 3: "Moto", 5: "Bus", 7: "Camion"}
        self.colores_tipo     = {
            "Auto":   (0, 220, 0),
            "Moto":   (0, 180, 255),
            "Bus":    (255, 80, 80),
            "Camion": (180, 0, 255),
        }

        # ══════════════════════════════════════════════
        # ZONA PROHIBIDA
        # Se define con el mouse. Empieza sin zona.
        # ══════════════════════════════════════════════
        self.zona            = None   # (x1, y1, x2, y2) de la zona prohibida
        self.dibujando_zona  = False  # True mientras el usuario arrastra
        self.punto_inicio    = None   # Primer clic del mouse
        self.zona_activa     = False  # True cuando ya hay zona definida

        # ══════════════════════════════════════════════
        # SEGUIMIENTO DE VEHÍCULOS EN ZONA
        # Clave: ID de bounding box aproximado
        # Valor: timestamp de cuando entró a la zona
        # ══════════════════════════════════════════════
        self.vehiculos_en_zona = {}   # {bbox_key: tiempo_entrada}
        self.multas_generadas  = set() # bbox_keys que ya generaron multa (no repetir)

        # ── Estadísticas y registros ──
        self.id_infraccion    = 0
        self.total_infracc    = 0
        self.registros_pdf    = []
        self.tiempo_inicio    = None

    # ──────────────────────────────────────────────────
    # MANEJO DEL MOUSE — Dibuja la zona prohibida
    # ──────────────────────────────────────────────────
    def _callback_mouse(self, evento, x, y, flags, param):
        """
        Clic izquierdo + arrastre = dibuja zona.
        Clic derecho              = borra la zona.
        """
        if evento == cv2.EVENT_LBUTTONDOWN:
            # Inicio del dibujo
            self.dibujando_zona = True
            self.punto_inicio   = (x, y)
            self.zona           = None
            self.zona_activa    = False
            # Limpiar seguimiento anterior
            self.vehiculos_en_zona.clear()
            self.multas_generadas.clear()

        elif evento == cv2.EVENT_MOUSEMOVE and self.dibujando_zona:
            # Vista previa en tiempo real mientras arrastra
            self.zona = (
                min(self.punto_inicio[0], x),
                min(self.punto_inicio[1], y),
                max(self.punto_inicio[0], x),
                max(self.punto_inicio[1], y)
            )

        elif evento == cv2.EVENT_LBUTTONUP:
            # Soltar el mouse = zona confirmada
            self.dibujando_zona = False
            if self.zona:
                w = self.zona[2] - self.zona[0]
                h = self.zona[3] - self.zona[1]
                if w > 20 and h > 20:   # zona mínima válida
                    self.zona_activa = True
                    print(f"  [ZONA] Zona prohibida definida: {self.zona}")
                else:
                    self.zona = None
                    print("  [ZONA] Zona muy pequeña, intenta de nuevo.")

        elif evento == cv2.EVENT_RBUTTONDOWN:
            # Clic derecho = borrar zona
            self.zona        = None
            self.zona_activa = False
            self.vehiculos_en_zona.clear()
            self.multas_generadas.clear()
            print("  [ZONA] Zona prohibida eliminada.")

    # ──────────────────────────────────────────────────
    # Verifica si el centro de un bbox está dentro
    # de la zona prohibida
    # ──────────────────────────────────────────────────
    def _esta_en_zona(self, x1, y1, x2, y2):
        if not self.zona_activa or self.zona is None:
            return False
        # Usamos el centro inferior del bbox (ruedas del vehículo)
        cx = (x1 + x2) // 2
        cy = y2   # parte inferior = donde apoya el vehículo
        zx1, zy1, zx2, zy2 = self.zona
        return zx1 <= cx <= zx2 and zy1 <= cy <= zy2

    # ──────────────────────────────────────────────────
    # Clave única aproximada para rastrear un vehículo
    # entre frames (grid de 50px)
    # ──────────────────────────────────────────────────
    def _bbox_key(self, x1, y1, x2, y2):
        cx = ((x1 + x2) // 2) // 50
        cy = ((y1 + y2) // 2) // 50
        return (cx, cy)

    # ──────────────────────────────────────────────────
    # Dibuja la zona prohibida sobre el frame
    # ──────────────────────────────────────────────────
    def _dibujar_zona(self, frame):
        if self.zona is None:
            return frame
        x1, y1, x2, y2 = self.zona

        # Relleno semitransparente rojo
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 200), -1)
        cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)

        # Borde rojo
        color_borde = (0, 80, 220) if self.zona_activa else (100, 100, 220)
        grosor      = 2 if self.zona_activa else 1
        cv2.rectangle(frame, (x1, y1), (x2, y2), color_borde, grosor)

        # Etiqueta de la zona
        etiq = "ZONA PROHIBIDA" if self.zona_activa else "Dibujando zona..."
        cv2.rectangle(frame, (x1, y1 - 24), (x1 + 180, y1), color_borde, -1)
        cv2.putText(frame, etiq, (x1 + 4, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        return frame

    # ──────────────────────────────────────────────────
    # Dibuja recuadros de vehículos con temporizador
    # ──────────────────────────────────────────────────
    def _dibujar_vehiculos(self, frame, resultados):
        ahora         = time.time()
        keys_visibles = set()   # Para limpiar los que ya salieron

        for box in resultados[0].boxes:
            conf_val        = float(box.conf[0])
            clase_id        = int(box.cls[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            tipo  = self.etiquetas.get(clase_id, "Vehiculo")
            color = self.colores_tipo.get(tipo, (200, 200, 200))
            key   = self._bbox_key(x1, y1, x2, y2)
            keys_visibles.add(key)

            en_zona     = self._esta_en_zona(x1, y1, x2, y2)
            ya_multado  = key in self.multas_generadas

            # ── Gestión del temporizador ──
            if en_zona and not ya_multado:
                if key not in self.vehiculos_en_zona:
                    self.vehiculos_en_zona[key] = ahora
                    print(f"  [ZONA] {tipo} entro a zona prohibida — iniciando conteo...")

                tiempo_en_zona = ahora - self.vehiculos_en_zona[key]

                # ¿Ya cumplió los 10 segundos? → MULTA
                if tiempo_en_zona >= self.SEGUNDOS_LIMITE:
                    self._registrar_infraccion(tipo, conf_val, x1, y1, x2, y2)
                    self.multas_generadas.add(key)
                    color = (0, 0, 255)   # Rojo = multado

                else:
                    # Mostrar cuenta regresiva sobre el vehículo
                    restante  = self.SEGUNDOS_LIMITE - int(tiempo_en_zona)
                    porcentaje = tiempo_en_zona / self.SEGUNDOS_LIMITE

                    # Barra de progreso sobre el bbox
                    barra_w = x2 - x1
                    llenado = int(barra_w * porcentaje)
                    cv2.rectangle(frame, (x1, y1 - 8), (x2, y1 - 2), (50, 50, 50), -1)
                    cv2.rectangle(frame, (x1, y1 - 8), (x1 + llenado, y1 - 2), (0, 0, 255), -1)

                    # Texto de cuenta regresiva
                    texto_tiempo = f"MULTA EN {restante}s"
                    cv2.putText(frame, texto_tiempo,
                                (x1, y1 - 12),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

                    color = (0, 140, 255)   # Naranja = en zona, contando

            elif ya_multado:
                color = (0, 0, 200)   # Rojo oscuro = ya fue multado
                cv2.putText(frame, "MULTADO",
                            (x1, y1 - 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 200), 2)

            else:
                # Fuera de zona: si estaba siendo contado, reiniciar
                if key in self.vehiculos_en_zona:
                    del self.vehiculos_en_zona[key]

            # ── Recuadro del vehículo ──
            grosor = 3 if tipo in ("Bus", "Camion") else 2
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, grosor)

            etiqueta = f"{tipo}  {conf_val*100:.1f}%"
            (tw, th), _ = cv2.getTextSize(etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y2), (x1 + tw + 6, y2 + th + 8), color, -1)
            cv2.putText(frame, etiqueta, (x1 + 3, y2 + th + 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        # Limpiar vehículos que ya no están en pantalla
        desaparecidos = set(self.vehiculos_en_zona.keys()) - keys_visibles
        for k in desaparecidos:
            del self.vehiculos_en_zona[k]

        return frame

    # ──────────────────────────────────────────────────
    # Registra la infracción (terminal + lista para PDF)
    # ──────────────────────────────────────────────────
    def _registrar_infraccion(self, tipo, confianza_val, x1, y1, x2, y2):
        self.id_infraccion += 1
        self.total_infracc += 1
        pct   = round(confianza_val * 100, 1)
        ahora = time.localtime()
        dias  = ["Lunes","Martes","Miercoles","Jueves","Viernes","Sabado","Domingo"]

        dia   = dias[ahora.tm_wday]
        fecha = f"{ahora.tm_mday:02d}/{ahora.tm_mon:02d}/{ahora.tm_year}"
        hora  = f"{ahora.tm_hour:02d}:{ahora.tm_min:02d}:{ahora.tm_sec:02d}"

        print(f"\n  ⚠️  INFRACCION #{self.id_infraccion:04d} GENERADA")
        print(f"     Tipo     : {tipo}")
        print(f"     Fecha    : {dia} {fecha}  {hora}")
        print(f"     Falta    : Estacionamiento Indebido")
        print(f"     Multa    : Bs 200.00")
        print(f"     Fiabilidad IA: {pct}%\n")

        self.registros_pdf.append([
            f"#{self.id_infraccion:04d}",
            dia, fecha, hora,
            tipo,
            "Estacionamiento Indebido",
            f"{pct}%",
            "Bs 200.00"
        ])

    # ──────────────────────────────────────────────────
    # Panel de estado en pantalla
    # ──────────────────────────────────────────────────
    def _dibujar_panel_estado(self, frame, n_vehiculos, fps):
        tiempo_activo = int(time.time() - self.tiempo_inicio)
        mins = tiempo_activo // 60
        segs = tiempo_activo % 60

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (440, 105), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        cv2.putText(frame,
            f"Vehiculos en pantalla: {n_vehiculos}   |   Infracciones: {self.total_infracc}",
            (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
        cv2.putText(frame,
            f"FPS: {fps:.1f}   |   Tiempo activo: {mins:02d}:{segs:02d}",
            (10, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        estado_zona = "ZONA ACTIVA" if self.zona_activa else "Sin zona definida"
        color_zona  = (0, 200, 100) if self.zona_activa else (100, 100, 255)
        cv2.putText(frame, f"Zona: {estado_zona}   |   Limite: {self.SEGUNDOS_LIMITE}s",
            (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.48, color_zona, 1)

        cv2.putText(frame,
            "CLIC+ARRASTRE: dibujar zona   |   CLIC DERECHO: borrar   |   Q: salir y generar PDF",
            (10, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 160, 160), 1)

        return frame

    # ──────────────────────────────────────────────────
    # Genera el PDF al cerrar
    # ──────────────────────────────────────────────────
    def _generar_pdf(self):
        ts     = time.strftime("%Y%m%d_%H%M%S")
        nombre = f"infracciones_zona_{ts}.pdf"

        doc = SimpleDocTemplate(nombre, pagesize=A4,
                                rightMargin=1.5*cm, leftMargin=1.5*cm,
                                topMargin=1.5*cm,   bottomMargin=1.5*cm)

        estilos  = getSampleStyleSheet()
        azul_osc = colors.HexColor("#1A56A8")
        azul_med = colors.HexColor("#2E75D4")
        blanco   = colors.white
        gris_cla = colors.HexColor("#F4F6F9")

        st_titulo = ParagraphStyle("t", parent=estilos["Title"],
                                   fontSize=17, textColor=blanco,
                                   alignment=TA_CENTER, fontName="Helvetica-Bold")
        st_sub    = ParagraphStyle("s", parent=estilos["Normal"],
                                   fontSize=10, textColor=blanco,
                                   alignment=TA_CENTER, fontName="Helvetica")
        st_sec    = ParagraphStyle("sc", parent=estilos["Normal"],
                                   fontSize=11, textColor=azul_osc,
                                   fontName="Helvetica-Bold",
                                   spaceBefore=12, spaceAfter=6)
        st_norm   = ParagraphStyle("n", parent=estilos["Normal"],
                                   fontSize=9, fontName="Helvetica")

        elementos    = []
        fecha_rep    = time.strftime("%d/%m/%Y  %H:%M:%S")
        duracion     = int(time.time() - self.tiempo_inicio)
        mins, segs   = duracion // 60, duracion % 60

        # ── Encabezado ──
        enc = Table(
            [[Paragraph("GTS VIAL — Infracciones por Estacionamiento Indebido", st_titulo)],
             [Paragraph(f"Reporte generado: {fecha_rep}", st_sub)]],
            colWidths=[18*cm]
        )
        enc.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), azul_osc),
            ("TOPPADDING",    (0,0), (-1,-1), 12),
            ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ]))
        elementos.append(enc)
        elementos.append(Spacer(1, 0.5*cm))

        # ── Resumen ──
        elementos.append(Paragraph("Resumen de Sesión", st_sec))
        st_val  = ParagraphStyle("v", parent=estilos["Normal"],
                                 fontSize=22, fontName="Helvetica-Bold",
                                 textColor=azul_osc, alignment=TA_CENTER)
        st_etiq = ParagraphStyle("e", parent=estilos["Normal"],
                                 fontSize=8, fontName="Helvetica",
                                 textColor=colors.HexColor("#6B7280"),
                                 alignment=TA_CENTER)

        resumen = Table([[
            Paragraph(str(self.total_infracc),        st_val),
            Paragraph(f"Bs {self.total_infracc*200:.2f}", st_val),
            Paragraph(f"{mins:02d}:{segs:02d}",        st_val),
            Paragraph(f"{self.SEGUNDOS_LIMITE}s",       st_val),
        ],[
            Paragraph("Infracciones",      st_etiq),
            Paragraph("Monto Total",        st_etiq),
            Paragraph("Duración Sesión",    st_etiq),
            Paragraph("Límite de Tiempo",   st_etiq),
        ]], colWidths=[4.4*cm]*4)
        resumen.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), gris_cla),
            ("LINEBELOW",     (0,0), (-1,0),  0.5, colors.HexColor("#D1D5DB")),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LINEAFTER",     (0,0), (2,1),   0.5, colors.HexColor("#D1D5DB")),
        ]))
        elementos.append(resumen)
        elementos.append(Spacer(1, 0.5*cm))

        # ── Tabla de infracciones ──
        elementos.append(Paragraph("Registro de Infracciones Detectadas", st_sec))

        if not self.registros_pdf:
            elementos.append(Paragraph("No se registraron infracciones en esta sesión.", st_norm))
        else:
            cabecera = ["ID", "Día", "Fecha", "Hora", "Vehículo", "Infracción", "Fiabilidad IA", "Monto"]
            st_cab   = ParagraphStyle("cb", parent=estilos["Normal"],
                                      fontSize=8, fontName="Helvetica-Bold",
                                      textColor=blanco, alignment=TA_CENTER)
            st_cel   = ParagraphStyle("cl", parent=estilos["Normal"],
                                      fontSize=7.5, fontName="Helvetica",
                                      alignment=TA_CENTER)

            filas = [[Paragraph(c, st_cab) for c in cabecera]]
            for r in self.registros_pdf:
                filas.append([Paragraph(str(v), st_cel) for v in r])

            tabla = Table(filas,
                          colWidths=[1.4*cm,2.2*cm,2.3*cm,1.8*cm,1.8*cm,3.5*cm,2.2*cm,1.8*cm],
                          repeatRows=1)
            tabla.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,0),  azul_med),
                ("FONTSIZE",      (0,0), (-1,0),  8),
                ("TOPPADDING",    (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ("ALIGN",         (0,0), (-1,-1), "CENTER"),
                ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#E5E7EB")),
                ("LINEBELOW",     (0,0), (-1,0),  1, azul_osc),
                ("ROWBACKGROUNDS",(0,1), (-1,-1),
                 [colors.white, colors.HexColor("#FFF5F5")]),
            ]))
            elementos.append(tabla)

        # ── Pie ──
        elementos.append(Spacer(1, 0.4*cm))
        st_pie = ParagraphStyle("p", parent=estilos["Normal"],
                                fontSize=7.5, textColor=colors.HexColor("#9CA3AF"),
                                alignment=TA_CENTER)
        elementos.append(Paragraph(
            f"GTS Vial  ·  Detección: Estacionamiento Indebido  ·  "
            f"Modelo YOLOv8s  ·  Límite: {self.SEGUNDOS_LIMITE}s  ·  {fecha_rep}",
            st_pie
        ))

        doc.build(elementos)
        print(f"\n  PDF generado: {nombre}")
        return nombre

    # ──────────────────────────────────────────────────
    # Bucle principal
    # ──────────────────────────────────────────────────
    def iniciar_monitoreo(self):
        self.tiempo_inicio = time.time()

        print("=" * 65)
        print("  GTS VIAL — DETECTOR DE ESTACIONAMIENTO INDEBIDO")
        print("  Modelo: YOLOv8s  |  Limite: 10 segundos en zona")
        print()
        print("  INSTRUCCIONES:")
        print("  1. Dibuja la zona prohibida con CLIC + ARRASTRE")
        print("  2. Clic derecho para borrar y redibujar la zona")
        print("  3. Presiona Q para salir y generar el PDF")
        print("=" * 65)

        cv2.namedWindow('GTS Vial - Detector Zona Prohibida')
        cv2.setMouseCallback('GTS Vial - Detector Zona Prohibida', self._callback_mouse)

        tiempo_anterior = time.time()

        while self.cap.isOpened():
            exito, frame = self.leer_frame()
            if not exito:
                print("Se perdio la senal de la camara.")
                break

            # ── 1. Detectar con YOLO ──
            resultados = self.modelo(
                frame,
                classes=self.clases_objetivo,
                conf=self.confianza,
                verbose=False
            )

            # ── 2. Dibujar zona prohibida ──
            frame = self._dibujar_zona(frame)

            # ── 3. Dibujar vehículos y lógica de infracción ──
            frame = self._dibujar_vehiculos(frame, resultados)

            # ── 4. FPS ──
            tiempo_actual   = time.time()
            fps             = 1 / (tiempo_actual - tiempo_anterior + 1e-9)
            tiempo_anterior = tiempo_actual

            # ── 5. Panel de estado ──
            frame = self._dibujar_panel_estado(frame, len(resultados[0].boxes), fps)

            # ── 6. Mostrar ──
            cv2.imshow('GTS Vial - Detector Zona Prohibida', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # ── Resumen y PDF ──
        duracion = int(time.time() - self.tiempo_inicio)
        print("\n" + "=" * 65)
        print("  RESUMEN FINAL")
        print(f"  Duración sesión    : {duracion // 60:02d} min {duracion % 60:02d} seg")
        print(f"  Infracciones total : {self.total_infracc}")
        print(f"  Monto total        : Bs {self.total_infracc * 200:.2f}")
        print("=" * 65)
        print("\n  Generando PDF...")
        self._generar_pdf()
        self.apagar()


# ============================================================
# EJECUCIÓN
# ============================================================
if __name__ == "__main__":
    nodo = CamaraInteligente(indice_camara=0)
    nodo.iniciar_monitoreo()
