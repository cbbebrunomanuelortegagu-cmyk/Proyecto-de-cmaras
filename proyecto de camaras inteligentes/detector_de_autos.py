import cv2
from ultralytics import YOLO
import time

# ==========================================
# CLASE PADRE: Manejo basico de hardware
# ==========================================
class CamaraBase:
    def __init__(self, indice_camara=0):
        """Inicializa la conexion fisica con la camara."""
        self.cap = cv2.VideoCapture(indice_camara)
        if not self.cap.isOpened():
            print("Error: No se pudo acceder a la camara.")
        else:
            print(f"Camara {indice_camara} conectada correctamente.")

    def leer_frame(self):
        """Lee un solo fotograma del video."""
        ret, frame = self.cap.read()
        return ret, frame

    def apagar(self):
        """Libera la camara y cierra las ventanas."""
        self.cap.release()
        cv2.destroyAllWindows()
        print("Camara apagada y recursos liberados.")


# ==========================================
# CLASE HIJA: Hereda la camara y le suma IA (YOLO)
# ==========================================
class CamaraInteligente(CamaraBase):
    def __init__(self, indice_camara=0, modelo_yolo='yolov8s.pt'):
        """
        HERENCIA: Llama al constructor del padre y carga el modelo IA.
        Usamos 'yolov8s.pt' (Small) — detecta mejor objetos pequeños.
        """
        super().__init__(indice_camara)

        print("Cargando modelo YOLOv8s... por favor espera.")
        self.modelo = YOLO(modelo_yolo)
        print("Modelo cargado con exito!\n")

        # Solo autos (clase 2 del dataset COCO)
        self.clases_objetivo = [2]
        self.confianza        = 0.35

        # ── Estadisticas de sesion ──
        self.id_deteccion      = 0          # Contador unico por cada auto registrado
        self.total_detecciones = 0          # Cuantos autos en total se detectaron
        self.fiabilidades      = []         # Guardamos todas para calcular el promedio al final
        self.tiempo_inicio     = None       # Para calcular duracion de la sesion

    # ──────────────────────────────────────────
    # Dibuja recuadros personalizados en español
    # en vez de usar el .plot() default de YOLO
    # ──────────────────────────────────────────
    def dibujar_recuadros(self, frame, resultados):
        """
        Recorre cada deteccion y dibuja manualmente el recuadro
        con color y texto en español. Retorna el frame modificado.
        """
        for box in resultados[0].boxes:
            confianza_val = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # Color segun nivel de fiabilidad:
            # Verde fuerte  = alta confianza (>=80%)
            # Verde normal  = confianza media (50-79%)
            # Amarillo      = confianza baja  (<50%)
            if confianza_val >= 0.80:
                color = (0, 220, 0)       # Verde fuerte
            elif confianza_val >= 0.50:
                color = (0, 180, 80)      # Verde medio
            else:
                color = (0, 200, 200)     # Amarillo verdoso

            # Dibujar recuadro
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Etiqueta con porcentaje en español
            etiqueta = f"Auto  {confianza_val*100:.1f}%"
            (ancho_txt, alto_txt), _ = cv2.getTextSize(
                etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2
            )

            # Fondo de la etiqueta
            cv2.rectangle(frame,
                          (x1, y1 - alto_txt - 8),
                          (x1 + ancho_txt + 6, y1),
                          color, -1)

            # Texto sobre el fondo
            cv2.putText(frame, etiqueta,
                        (x1 + 3, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)

        return frame

    # ──────────────────────────────────────────
    # Superpone el panel de estado en la imagen
    # ──────────────────────────────────────────
    def dibujar_panel_estado(self, frame, detecciones_frame, fps):
        """Dibuja el recuadro de informacion en la esquina superior izquierda."""
        tiempo_activo = int(time.time() - self.tiempo_inicio)
        minutos       = tiempo_activo // 60
        segundos      = tiempo_activo % 60

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (340, 80), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        cv2.putText(frame,
                    f"Autos en pantalla: {detecciones_frame}   |   Total sesion: {self.total_detecciones}",
                    (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)

        cv2.putText(frame,
                    f"FPS: {fps:.1f}   |   Tiempo activo: {minutos:02d}:{segundos:02d}",
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.putText(frame,
                    f"Confianza minima: {int(self.confianza*100)}%   |   ID siguiente: #{self.id_deteccion + 1}",
                    (10, 73), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)

        return frame

    # ──────────────────────────────────────────
    # Bucle principal de monitoreo
    # ──────────────────────────────────────────
    def iniciar_monitoreo(self):
        """Captura frames, los procesa con YOLO y muestra resultado en pantalla."""
        self.tiempo_inicio = time.time()

        print("=" * 60)
        print("  SISTEMA GTS VIAL - NODO DE DETECCION ACTIVO")
        print("  Detectando: Autos  |  Modelo: YOLOv8s")
        print("  Presiona Q para detener el monitoreo")
        print("=" * 60)

        tiempo_anterior = time.time()

        while self.cap.isOpened():
            exito, frame = self.leer_frame()
            if not exito:
                print("Se perdio la senal de la camara.")
                break

            # ── 1. Procesar frame con YOLO ──
            resultados = self.modelo(
                frame,
                classes=self.clases_objetivo,
                conf=self.confianza,
                verbose=False
            )

            detecciones_frame = len(resultados[0].boxes)

            # ── 2. Registrar y mostrar en terminal ──
            if detecciones_frame > 0:
                ahora      = time.localtime()
                dias       = ["Lunes","Martes","Miercoles","Jueves",
                              "Viernes","Sabado","Domingo"]
                dia_semana = dias[ahora.tm_wday]
                fecha      = f"{ahora.tm_mday:02d}/{ahora.tm_mon:02d}/{ahora.tm_year}"
                hora       = f"{ahora.tm_hour:02d}:{ahora.tm_min:02d}:{ahora.tm_sec:02d}"

                for conf_val in resultados[0].boxes.conf.tolist():
                    self.id_deteccion      += 1
                    self.total_detecciones += 1
                    pct = round(conf_val * 100, 1)
                    self.fiabilidades.append(pct)

                    # Etiqueta de nivel para la terminal
                    if pct >= 80:
                        nivel = "*** ALTA ***"
                    elif pct >= 50:
                        nivel = "MEDIA      "
                    else:
                        nivel = "baja       "

                    print(f"  [#{self.id_deteccion:04d}]  {dia_semana} {fecha}  {hora}"
                          f"  |  Fiabilidad: {pct:5.1f}%  {nivel}")

            # ── 3. Dibujar recuadros personalizados ──
            frame = self.dibujar_recuadros(frame, resultados)

            # ── 4. Calcular FPS ──
            tiempo_actual   = time.time()
            fps             = 1 / (tiempo_actual - tiempo_anterior + 1e-9)
            tiempo_anterior = tiempo_actual

            # ── 5. Dibujar panel de estado ──
            frame = self.dibujar_panel_estado(frame, detecciones_frame, fps)

            # ── 6. Mostrar ventana ──
            cv2.imshow('GTS Vial - Nodo de Deteccion', frame)

            # ── 7. Salir con Q ──
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # ── Resumen final en terminal ──
        duracion_total = int(time.time() - self.tiempo_inicio)
        promedio_fiab  = (sum(self.fiabilidades) / len(self.fiabilidades)
                          if self.fiabilidades else 0)

        print("\n" + "=" * 60)
        print("  RESUMEN DE SESION")
        print(f"  Duracion total         : {duracion_total // 60:02d} min {duracion_total % 60:02d} seg")
        print(f"  Total autos registrados: {self.total_detecciones}")
        print(f"  Fiabilidad promedio    : {promedio_fiab:.1f}%")
        print(f"  Ultimo ID registrado   : #{self.id_deteccion:04d}")
        print("=" * 60)

        self.apagar()


# ==========================================
# EJECUCION DEL PROGRAMA
# ==========================================
if __name__ == "__main__":
    nodo_edge_01 = CamaraInteligente(indice_camara=0)
    nodo_edge_01.iniciar_monitoreo()
