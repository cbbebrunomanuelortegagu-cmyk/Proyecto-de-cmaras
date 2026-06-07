<?php
require_once 'config.php';
$body         = json_decode(file_get_contents("php://input"), true);
$id_infraccion = $body['id_infraccion'] ?? '';
$id_usuario    = $body['id_usuario']    ?? 1;

$conn = conectar();

$stmt = $conn->prepare(
    "UPDATE infracciones_ia
     SET estado_revision='Descartada', fecha_revision=NOW(), id_revisor_fk=?
     WHERE id_infraccion=?"
);
$stmt->bind_param("is", $id_usuario, $id_infraccion);
$stmt->execute();

// Registrar en auditoría
$aud = $conn->prepare(
    "INSERT INTO auditoria (id_usuario_fk, accion, tabla_afectada, id_registro, detalle)
     VALUES (?, 'INFRACCION_DESCARTADA', 'infracciones_ia', ?, 'Marcada como Falso Positivo')"
);
$aud->bind_param("is", $id_usuario, $id_infraccion);
$aud->execute();

echo json_encode(["ok" => true]);
$conn->close();
?>
