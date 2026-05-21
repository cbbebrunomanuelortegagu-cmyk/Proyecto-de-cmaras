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
        Usamos 'yolov8s.pt' (Small) en vez de Nano, detecta mejor objetos
        pequeños como autos de juguete o autos en pantalla de celular.
        """
        super().__init__(indice_camara)

        print("Cargando modelo YOLOv8s... por favor espera.")
        self.modelo = YOLO(modelo_yolo)
        print("Modelo cargado con exito!\n")

        # ── Solo buscamos AUTOS (clase 2 del dataset COCO) ──
        # COCO: 0=persona, 1=bicicleta, 2=auto, 3=moto, 5=bus, 7=camion
        self.clases_objetivo = [2]  # <-- Solo autos

        # Umbral de confianza bajo para pruebas (detecta mas cosas)
        # Si hay muchos falsos positivos, sube esto a 0.45 o 0.55
        self.confianza = 0.35

        # Contador total de detecciones en la sesion
        self.total_detecciones = 0

    def iniciar_monitoreo(self):
        """Bucle principal que captura, procesa y muestra el video."""
        print("=" * 50)
        print("  MONITOREO INICIADO - Solo detectando AUTOS")
        print("  Presiona Q para apagar el sistema")
        print("=" * 50)

        tiempo_anterior = time.time()

        while self.cap.isOpened():
            exito, frame = self.leer_frame()
            if not exito:
                print("Se perdio la senal de la camara.")
                break

            # ── 1. Procesar con YOLO (solo autos, baja confianza para pruebas) ──
            resultados = self.modelo(
                frame,
                classes=self.clases_objetivo,
                conf=self.confianza,
                verbose=False
            )

            # ── 2. Contar cuantos autos detecto en este frame ──
            detecciones_frame = len(resultados[0].boxes)

            # ── 3. Imprimir en terminal si detecto algo (solo para pruebas) ──
            if detecciones_frame > 0:
                self.total_detecciones += detecciones_frame
                print(f"[DETECCION] Autos en pantalla: {detecciones_frame} | "
                      f"Confianzas: {[round(float(c), 2) for c in resultados[0].boxes.conf.tolist()]}")

            # ── 4. Dibujar los recuadros sobre el frame ──
            frame_procesado = resultados[0].plot()

            # ── 5. Calcular FPS para ver si corre fluido ──
            tiempo_actual = time.time()
            fps = 1 / (tiempo_actual - tiempo_anterior + 1e-9)
            tiempo_anterior = tiempo_actual

            # ── 6. Agregar texto de estado en la pantalla ──
            # Fondo semitransparente para el texto
            overlay = frame_procesado.copy()
            cv2.rectangle(overlay, (0, 0), (320, 70), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame_procesado, 0.5, 0, frame_procesado)

            cv2.putText(frame_procesado,
                        f"Autos detectados: {detecciones_frame}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.putText(frame_procesado,
                        f"FPS: {fps:.1f}  |  Confianza min: {self.confianza}",
                        (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            # ── 7. Mostrar ventana ──
            cv2.imshow('GTS Vial - Detector de Autos (prueba)', frame_procesado)

            # ── 8. Salir con Q ──
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # ── Resumen final en terminal ──
        print("\n" + "=" * 50)
        print(f"  SESION TERMINADA")
        print(f"  Total de detecciones en esta sesion: {self.total_detecciones}")
        print("=" * 50)

        self.apagar()


# ==========================================
# EJECUCION DEL PROGRAMA
# ==========================================
if __name__ == "__main__":
    nodo_edge_01 = CamaraInteligente(indice_camara=0)
    nodo_edge_01.iniciar_monitoreo()
