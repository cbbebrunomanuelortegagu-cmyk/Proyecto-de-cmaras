<?php
require_once 'config.php';

$body = json_decode(file_get_contents("php://input"), true);
$credencial = $body['credencial'] ?? '';
$password   = $body['password']   ?? '';

if (empty($credencial) || empty($password)) {
    http_response_code(400);
    echo json_encode(["error" => "Credenciales incompletas"]);
    exit();
}

$conn = conectar();
$stmt = $conn->prepare(
    "SELECT id_usuario, nombre_completo, rol
     FROM usuarios
     WHERE credencial = ? AND password_hash = ? AND estado = 'Activo'"
);
$stmt->bind_param("ss", $credencial, $password);
$stmt->execute();
$result = $stmt->get_result();

if ($result->num_rows === 1) {
    $usuario = $result->fetch_assoc();

    // Registrar ultimo acceso en la BD
    $upd = $conn->prepare("UPDATE usuarios SET ultimo_acceso = NOW() WHERE id_usuario = ?");
    $upd->bind_param("i", $usuario['id_usuario']);
    $upd->execute();

    // Registrar en auditoria
    $ip  = $_SERVER['REMOTE_ADDR'] ?? '127.0.0.1';
    $aud = $conn->prepare(
        "INSERT INTO auditoria (id_usuario_fk, accion, tabla_afectada, id_registro, ip_origen)
         VALUES (?, 'LOGIN_EXITOSO', 'usuarios', ?, ?)"
    );
    $id_str = (string)$usuario['id_usuario'];
    $aud->bind_param("iss", $usuario['id_usuario'], $id_str, $ip);
    $aud->execute();

    echo json_encode(["ok" => true, "usuario" => $usuario]);
} else {
    http_response_code(401);
    echo json_encode(["ok" => false, "error" => "Credenciales incorrectas"]);
}

$conn->close();
?>