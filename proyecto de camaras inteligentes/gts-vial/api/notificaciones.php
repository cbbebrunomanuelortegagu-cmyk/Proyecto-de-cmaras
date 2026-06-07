<?php
require_once 'config.php';
$body      = json_decode(file_get_contents("php://input"), true);
$id_boleta = $body['id_boleta'] ?? 0;
$canal     = $body['canal']     ?? 'Email';
 
$conn = conectar();
$stmt = $conn->prepare(
    "INSERT INTO notificaciones (id_boleta_fk, canal_envio, estado_envio, fecha_envio)
     VALUES (?, ?, 'Enviado', NOW())"
);
$stmt->bind_param("is", $id_boleta, $canal);
$stmt->execute();
 
echo json_encode(["ok" => true, "id_notificacion" => $conn->insert_id]);
$conn->close();
?>