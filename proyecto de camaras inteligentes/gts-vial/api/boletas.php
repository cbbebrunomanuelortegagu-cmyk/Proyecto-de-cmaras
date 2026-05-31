<?php
require_once 'config.php';

$metodo = $_SERVER['REQUEST_METHOD'];
$conn   = conectar();

// GET → listar boletas con datos del propietario
if ($metodo === 'GET') {
    $result = $conn->query(
        "SELECT b.id_boleta, b.id_infraccion_fk, b.fecha_emision,
                b.monto_multa_bs, b.estado_pago, b.fecha_vencimiento,
                p.nombre_completo AS propietario, v.placa
         FROM boletas_oficiales b
         JOIN infracciones_ia i  ON b.id_infraccion_fk = i.id_infraccion
         LEFT JOIN vehiculos  v  ON i.placa_detectada  = v.placa
         LEFT JOIN propietarios p ON v.ci_propietario_fk = p.ci_propietario
         ORDER BY b.fecha_emision DESC"
    );
    $datos = [];
    while ($fila = $result->fetch_assoc()) {
        $datos[] = $fila;
    }
    echo json_encode(["ok" => true, "data" => $datos]);

// POST → emitir nueva boleta
} elseif ($metodo === 'POST') {
    $body          = json_decode(file_get_contents("php://input"), true);
    $id_infraccion = $body['id_infraccion']  ?? '';
    $id_usuario    = $body['id_usuario']     ?? 0;
    $monto         = $body['monto_multa_bs'] ?? 0;

    // Calcular vencimiento a 30 días
    $vencimiento = date('Y-m-d', strtotime('+30 days'));

    $stmt = $conn->prepare(
        "INSERT INTO boletas_oficiales
             (id_infraccion_fk, id_usuario_validador_fk, monto_multa_bs, fecha_vencimiento)
         VALUES (?, ?, ?, ?)"
    );
    $stmt->bind_param("sids", $id_infraccion, $id_usuario, $monto, $vencimiento);

    if ($stmt->execute()) {
        // Actualizar estado de la infracción a 'Aprobada'
        $upd = $conn->prepare(
            "UPDATE infracciones_ia SET estado_revision = 'Aprobada', fecha_revision = NOW()
             WHERE id_infraccion = ?"
        );
        $upd->bind_param("s", $id_infraccion);
        $upd->execute();

        echo json_encode(["ok" => true, "id_boleta" => $conn->insert_id, "vencimiento" => $vencimiento]);
    } else {
        http_response_code(500);
        echo json_encode(["ok" => false, "error" => $conn->error]);
    }
}

$conn->close();
?>