<?php
require_once 'config.php';
$conn = conectar();

$pend = $conn->query("SELECT COUNT(*) AS n FROM infracciones_ia WHERE estado_revision='Pendiente'")->fetch_assoc()['n'];
$emit = $conn->query("SELECT COUNT(*) AS n FROM infracciones_ia WHERE estado_revision='Aprobada'")->fetch_assoc()['n'];
$desc = $conn->query("SELECT COUNT(*) AS n FROM infracciones_ia WHERE estado_revision='Descartada'")->fetch_assoc()['n'];
$mont = $conn->query("SELECT COALESCE(SUM(monto_multa_bs),0) AS t FROM boletas_oficiales WHERE estado_pago != 'Anulado'")->fetch_assoc()['t'];

echo json_encode(["ok"=>true,"pendientes"=>$pend,"emitidas"=>$emit,"descartadas"=>$desc,"monto_total"=>$mont]);
$conn->close();
?>
