<?php
require_once 'config.php';

$body          = json_decode(file_get_contents("php://input"), true);
$id_infraccion = $body['id_infraccion'] ?? '';
$id_nodo       = $body['id_nodo']       ?? 1;
$id_tipo_falta = $body['id_tipo_falta'] ?? 4; // 4 = Estacionamiento Indebido
$placa         = $body['placa']         ?? 'NO-LEIDA';
$fecha_hora    = $body['fecha_hora']    ?? date('Y-m-d H:i:s');
$confianza     = $body['confianza']     ?? 0;
$hash          = $body['hash']          ?? hash('sha256', $id_infraccion);

$conn = conectar();
$stmt = $conn->prepare(
    "INSERT INTO infracciones_ia
        (id_infraccion, id_nodo_fk, id_tipo_falta_fk, placa_detectada,
         fecha_hora, confianza_ia, ruta_imagen, hash_evidencia, estado_revision)
     VALUES (?, ?, ?, ?, ?, ?, 'evidencias/sin_imagen.jpg', ?, 'Pendiente')"
);
$stmt->bind_param("siissds", 
    $id_infraccion, $id_nodo, $id_tipo_falta,
    $placa, $fecha_hora, $confianza, $hash
);

if ($stmt->execute()) {
    echo json_encode(["ok" => true, "id" => $id_infraccion]);
} else {
    http_response_code(500);
    echo json_encode(["ok" => false, "error" => $conn->error]);
}
$conn->close();
?>