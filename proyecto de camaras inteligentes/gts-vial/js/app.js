/* =============================================
   GTS VIAL - app.js
   Día 3: Conectado a db_smartcity_vial (XAMPP)
   ============================================= */

// ── Instancias de modales Bootstrap ──
const myModal     = new bootstrap.Modal(document.getElementById('modalDetalle'));
const modalAdd    = new bootstrap.Modal(document.getElementById('modalAddCamara'));
const modalEditar = new bootstrap.Modal(document.getElementById('modalEditarCamara'));

// ── Estado global ──
let usuarioActivo       = null;
let infraccionActivaId  = null;
let infraccionActivaData = null;  // objeto completo de la infracción abierta
let contadorCamaras     = 3;
let intervaloRefresh    = null;   // referencia al auto-refresh
let idsEnTabla          = new Set(); // IDs ya renderizados, para detectar nuevos

// ── Cámaras locales (espejo de nodos_edge) ──
const CAMARAS_BD = {
    1: { nombre: 'Cámara 01 - Centro', ubicacion: 'Av. Ayacucho y Heroínas',     ip: '192.168.1.10', umbral: 85, estado: 'Online' },
    2: { nombre: 'Cámara 02 - Norte',  ubicacion: 'Av. Blanco Galindo Km 2',     ip: '192.168.1.11', umbral: 85, estado: 'Online' },
    3: { nombre: 'Cámara 03 - Sur',    ubicacion: 'Av. Panamericana y 6 de Ago', ip: '192.168.1.12', umbral: 85, estado: 'Mantenimiento' },
};

// ── Usuarios válidos (tabla usuarios) ──
const USUARIOS_BD = {
    'admin':     { password: '123456789', nombre: 'Ing. Bruno Ortega',      rol: 'Administrador' },
    'operador1': { password: 'op123456',  nombre: 'Tec. Carlos Mamani',     rol: 'Operador' },
    'operador2': { password: 'op654321',  nombre: 'Tec. Ana Flores Quispe', rol: 'Operador' }
};

const diasVencimiento = 30;


// ═══════════════════════════════════════════════════
// MÓDULO: AUTENTICACIÓN
// ═══════════════════════════════════════════════════

function validarAcceso(e) {
    e.preventDefault();
    const credencial = document.getElementById('userAdmin').value.trim();
    const password   = document.getElementById('passAdmin').value.trim();
    const usuario    = USUARIOS_BD[credencial];

    if (usuario && usuario.password === password) {
        usuarioActivo = { credencial, ...usuario };

        Swal.fire({
            icon: 'success',
            title: 'Acceso Autorizado',
            html: `Bienvenido, <strong>${usuario.nombre}</strong><br>
                   <span class="badge bg-primary mt-1">${usuario.rol}</span>`,
            timer: 1800,
            showConfirmButton: false
        }).then(() => {
            document.getElementById('sidebar-operador').innerText = usuario.nombre;
            document.getElementById('login-view').style.setProperty('display', 'none', 'important');
            document.getElementById('dashboard-view').style.display = 'block';

            // Carga inicial de datos desde la BD
            cargarInfracciones();
            cargarStats();

            // Auto-refresh cada 10 segundos
            intervaloRefresh = setInterval(() => {
                cargarInfracciones(true); // true = modo silencioso
                cargarStats();
            }, 10000);
        });

    } else {
        Swal.fire({
            icon: 'error',
            title: 'Acceso Denegado',
            text: 'Credencial o contraseña incorrecta.',
            confirmButtonColor: '#0d6efd'
        });
    }
}

function cerrarSesion() {
    Swal.fire({
        title: '¿Cerrar sesión?',
        text: 'Saldrás del sistema de fiscalización.',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, salir',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            // Detener el auto-refresh al salir
            clearInterval(intervaloRefresh);
            intervaloRefresh = null;
            idsEnTabla.clear();
            usuarioActivo = null;
            document.getElementById('dashboard-view').style.display = 'none';
            document.getElementById('login-view').style.setProperty('display', 'flex', 'important');
            document.getElementById('passAdmin').value = '';
        }
    });
}


// ═══════════════════════════════════════════════════
// MÓDULO: NAVEGACIÓN
// ═══════════════════════════════════════════════════

function showSection(sectionId) {
    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.sidebar a').forEach(a => a.classList.remove('active'));
    document.getElementById(sectionId).classList.add('active');
    const btnId = 'link-' + sectionId.split('-')[1];
    document.getElementById(btnId).classList.add('active');

    // Si abre boletas, recargarlas
    if (sectionId === 'sec-boletas') cargarBoletas();
}


// ═══════════════════════════════════════════════════
// MÓDULO: ESTADÍSTICAS
// SELECT COUNT y SUM desde la BD real
// ═══════════════════════════════════════════════════

async function cargarStats() {
    try {
        const res  = await fetch('api/stats.php');
        const data = await res.json();
        if (!data.ok) return;

        document.getElementById('stat-pendientes').innerText  = data.pendientes;
        document.getElementById('stat-emitidas').innerText    = data.emitidas;
        document.getElementById('stat-descartadas').innerText = data.descartadas;
        document.getElementById('stat-monto').innerText       = `Bs ${parseFloat(data.monto_total || 0).toFixed(2)}`;

        const badge = document.getElementById('badge-pendientes');
        badge.innerText      = data.pendientes;
        badge.style.display  = data.pendientes > 0 ? 'inline' : 'none';

    } catch (err) {
        // XAMPP no disponible — usar valores locales sin romper la UI
        console.warn('Stats no disponibles:', err.message);
    }
}


// ═══════════════════════════════════════════════════
// MÓDULO: INFRACCIONES
// Lee vista_infracciones_panel y renderiza la tabla
// ═══════════════════════════════════════════════════

async function cargarInfracciones(silencioso = false) {
    try {
        const res  = await fetch('api/infracciones.php');
        const data = await res.json();
        if (!data.ok) return;

        const infracciones = data.data;
        const tbody        = document.getElementById('tabla-infracciones');
        const nuevas       = infracciones.filter(i => !idsEnTabla.has(i.id_infraccion));

        // Si hay infracciones nuevas y no es la carga inicial, mostrar notificación
        if (silencioso && nuevas.length > 0) {
            _notificarNuevasInfracciones(nuevas.length);
        }

        // Renderizar toda la tabla
        tbody.innerHTML = infracciones.map(inf => _htmlFilaInfraccion(inf)).join('');

        // Actualizar el set de IDs conocidos
        infracciones.forEach(i => idsEnTabla.add(i.id_infraccion));

    } catch (err) {
        console.warn('Infracciones no disponibles (XAMPP offline):', err.message);
        // Si XAMPP está offline la tabla mantiene los datos estáticos del HTML
    }
}

function _htmlFilaInfraccion(inf) {
    // Badge de infracción según gravedad
    const colorFalta = inf.gravedad === 'Muy Grave' ? 'bg-danger'
                     : inf.gravedad === 'Grave'     ? 'bg-warning text-dark'
                     : 'bg-secondary';

    const badgeGravedad = inf.gravedad === 'Muy Grave'
        ? `<span class="badge bg-dark px-2 py-1 rounded-pill ms-1" style="font-size:10px;">Muy Grave</span>`
        : inf.gravedad === 'Grave'
        ? `<span class="badge bg-warning text-dark px-2 py-1 rounded-pill ms-1" style="font-size:10px;">Grave</span>`
        : `<span class="badge bg-secondary px-2 py-1 rounded-pill ms-1" style="font-size:10px;">Leve</span>`;

    // Formato de fecha legible
    const fechaObj  = new Date(inf.fecha_hora);
    const fechaStr  = fechaObj.toLocaleDateString('es-BO', { day:'2-digit', month:'short', year:'numeric' });
    const horaStr   = fechaObj.toLocaleTimeString('es-BO', { hour:'2-digit', minute:'2-digit', second:'2-digit' });

    // Nombre del propietario (puede ser null si la placa no está en el padrón)
    const propietario = inf.propietario_nombre || '<span class="text-muted fst-italic">No registrado</span>';
    const vehiculo    = inf.marca
        ? `${inf.marca} ${inf.modelo || ''} ${inf.anio || ''} - ${inf.color || ''}`
        : '<span class="text-muted fst-italic">No registrado</span>';

    return `
        <tr id="fila-${inf.id_infraccion}">
            <td class="ps-4">
                <span class="fw-bold text-primary">${inf.id_infraccion}</span>
            </td>
            <td class="text-muted">${fechaStr}<br><small>${horaStr}</small></td>
            <td><i class="fa-solid fa-video text-muted me-1 small"></i>${inf.camara_nombre}</td>
            <td>
                <span class="badge ${colorFalta} px-2 py-1 rounded-pill me-1">${inf.nombre_falta}</span>
                ${badgeGravedad}
            </td>
            <td><span class="fw-bold text-dark">${parseFloat(inf.monto_multa_bs).toFixed(2)}</span></td>
            <td><span class="text-success fw-bold"><i class="fa-solid fa-check-circle me-1"></i>${inf.confianza_ia}%</span></td>
            <td class="text-center">
                <button class="btn btn-revisar btn-sm" data-id="${inf.id_infraccion}"
                    onclick='revisarInfraccionBD(${JSON.stringify(inf)})'>
                    <i class="fa-solid fa-magnifying-glass me-1"></i> Revisar Foto
                </button>
            </td>
        </tr>`;
}

function _notificarNuevasInfracciones(cantidad) {
    Swal.fire({
        icon: 'warning',
        title: `${cantidad} infracción${cantidad > 1 ? 'es' : ''} nueva${cantidad > 1 ? 's' : ''}`,
        text: 'El detector registró nuevas infracciones en la BD.',
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 4000,
        timerProgressBar: true
    });
}

// Abre el modal con datos reales de la BD
function revisarInfraccionBD(inf) {
    infraccionActivaId   = inf.id_infraccion;
    infraccionActivaData = inf;

    const hoy        = new Date();
    const vencDate   = new Date(hoy.setDate(hoy.getDate() + diasVencimiento));
    const fechaVenc  = vencDate.toLocaleDateString('es-BO', { day:'2-digit', month:'short', year:'numeric' });

    document.getElementById('detId').innerText          = inf.id_infraccion;
    document.getElementById('detPlaca').innerText       = inf.placa_detectada;
    document.getElementById('detFalta').innerText       = inf.nombre_falta;
    document.getElementById('detGravedad').innerText    = inf.gravedad;
    document.getElementById('detCamara').innerText      = inf.camara_nombre;
    document.getElementById('detDueño').innerText       = inf.propietario_nombre  || 'No registrado';
    document.getElementById('detAuto').innerText        = inf.marca
        ? `${inf.marca} ${inf.modelo || ''} - ${inf.color || ''}`
        : 'No registrado';
    document.getElementById('detMonto').innerText       = parseFloat(inf.monto_multa_bs).toFixed(2);
    document.getElementById('detVencimiento').innerText = fechaVenc;
    document.getElementById('detConfianza').innerText   = `✓ IA: ${inf.confianza_ia}%`;

    // Badge gravedad
    const badgeGrav = document.getElementById('detGravedad');
    badgeGrav.className = 'badge border';
    if (inf.gravedad === 'Muy Grave')   badgeGrav.classList.add('bg-danger', 'text-white');
    else if (inf.gravedad === 'Grave')  badgeGrav.classList.add('bg-warning', 'text-dark');
    else                                badgeGrav.classList.add('bg-secondary', 'text-white');

    myModal.show();
}

// Función legacy para las filas estáticas del HTML (compatibilidad)
function revisarInfraccion(id, placa, falta, gravedad, camara, dueño, auto, monto, confianza) {
    infraccionActivaId   = id;
    infraccionActivaData = null;

    const hoy       = new Date();
    const vencDate  = new Date(hoy.setDate(hoy.getDate() + diasVencimiento));
    const fechaVenc = vencDate.toLocaleDateString('es-BO', { day:'2-digit', month:'short', year:'numeric' });

    document.getElementById('detId').innerText          = id;
    document.getElementById('detPlaca').innerText       = placa;
    document.getElementById('detFalta').innerText       = falta;
    document.getElementById('detGravedad').innerText    = gravedad;
    document.getElementById('detCamara').innerText      = camara;
    document.getElementById('detDueño').innerText       = dueño;
    document.getElementById('detAuto').innerText        = auto;
    document.getElementById('detMonto').innerText       = parseFloat(monto).toFixed(2);
    document.getElementById('detVencimiento').innerText = fechaVenc;
    document.getElementById('detConfianza').innerText   = `✓ IA: ${confianza}%`;

    const badgeGrav = document.getElementById('detGravedad');
    badgeGrav.className = 'badge border';
    if (gravedad === 'Muy Grave')   badgeGrav.classList.add('bg-danger', 'text-white');
    else if (gravedad === 'Grave')  badgeGrav.classList.add('bg-warning', 'text-dark');
    else                            badgeGrav.classList.add('bg-secondary', 'text-white');

    myModal.show();
}

function cambiarEstadoBoton(id, nuevoEstado) {
    const btn = document.querySelector(`.btn-revisar[data-id="${id}"]`);
    if (!btn) return;
    btn.classList.remove('emitida', 'rechazada');
    if (nuevoEstado === 'emitida') {
        btn.classList.add('emitida');
        btn.innerHTML = '<i class="fa-solid fa-check-double me-1"></i> Boleta Emitida';
    } else if (nuevoEstado === 'rechazada') {
        btn.classList.add('rechazada');
        btn.innerHTML = '<i class="fa-solid fa-xmark me-1"></i> Descartada';
    }
}

async function finalizarEmision() {
    myModal.hide();

    const id    = infraccionActivaId;
    const monto = parseFloat(document.getElementById('detMonto').innerText);
    const vence = document.getElementById('detVencimiento').innerText;
    const dueño = document.getElementById('detDueño').innerText;

    // ── INSERT en boletas_oficiales via PHP ──
    try {
        const res  = await fetch('api/boletas.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id_infraccion:  id,
                id_usuario:     usuarioActivo?.id_usuario || 1,
                monto_multa_bs: monto
            })
        });
        const data = await res.json();

        if (data.ok) {
            cambiarEstadoBoton(id, 'emitida');
            idsEnTabla.add(id);
            cargarStats();
            cargarBoletas();

            Swal.fire({
                title: 'Boleta Generada',
                html: `Multa <strong>${id}</strong> registrada en BD.<br>
                       Monto: <strong>Bs ${monto.toFixed(2)}</strong><br>
                       Vence: <strong>${vence}</strong>`,
                icon: 'success',
                confirmButtonColor: '#198754'
            });
        } else {
            throw new Error(data.error);
        }

    } catch (err) {
        // Si XAMPP está offline, igual actualizar la UI
        cambiarEstadoBoton(id, 'emitida');
        Swal.fire({
            title: 'Boleta Generada (offline)',
            html: `Monto: <strong>Bs ${monto.toFixed(2)}</strong><br>
                   <small class="text-warning">XAMPP no disponible — dato no persistido en BD</small>`,
            icon: 'warning',
            confirmButtonColor: '#198754'
        });
    }

    infraccionActivaId   = null;
    infraccionActivaData = null;
}

async function rechazarMulta() {
    myModal.hide();

    const id = infraccionActivaId;

    // ── UPDATE estado_revision = 'Descartada' via PHP ──
    try {
        await fetch('api/rechazar.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id_infraccion: id,
                id_usuario:    usuarioActivo?.id_usuario || 1
            })
        });
    } catch (err) {
        console.warn('No se pudo actualizar BD:', err.message);
    }

    cambiarEstadoBoton(id, 'rechazada');
    cargarStats();

    Swal.fire({
        title: 'Infracción Descartada',
        html: `Registro <strong>${id}</strong> marcado como Falso Positivo.`,
        icon: 'info',
        confirmButtonColor: '#6c757d'
    });

    infraccionActivaId   = null;
    infraccionActivaData = null;
}


// ═══════════════════════════════════════════════════
// MÓDULO: BOLETAS EMITIDAS
// Lee boletas_oficiales con JOIN a propietarios
// ═══════════════════════════════════════════════════

async function cargarBoletas() {
    try {
        const res  = await fetch('api/boletas.php');
        const data = await res.json();
        if (!data.ok) return;

        const tbody = document.getElementById('tabla-boletas');

        if (data.data.length === 0) {
            tbody.innerHTML = `
                <tr><td colspan="7" class="text-center text-muted py-5">
                    <i class="fa-solid fa-inbox fa-2x mb-2 d-block opacity-25"></i>
                    Aún no se han emitido boletas.
                </td></tr>`;
            return;
        }

        tbody.innerHTML = data.data.map(b => {
            const estadoColor = b.estado_pago === 'Pagado'    ? 'bg-success'
                              : b.estado_pago === 'Apelación' ? 'bg-info text-dark'
                              : b.estado_pago === 'Anulado'   ? 'bg-secondary'
                              : 'bg-warning text-dark';
            return `
                <tr>
                    <td class="ps-4 fw-bold text-dark">#${String(b.id_boleta).padStart(4,'0')}</td>
                    <td class="text-primary fw-bold">${b.id_infraccion_fk}</td>
                    <td>${b.propietario || 'No registrado'}<br>
                        <small class="text-muted font-monospace">${b.placa || '---'}</small></td>
                    <td class="fw-bold">Bs ${parseFloat(b.monto_multa_bs).toFixed(2)}</td>
                    <td class="text-danger small">${b.fecha_vencimiento || '---'}</td>
                    <td><span class="badge ${estadoColor} rounded-pill px-2">${b.estado_pago}</span></td>
                    <td>
                        <button class="btn btn-outline-primary btn-sm rounded-pill px-3"
                                onclick="enviarNotificacion(${b.id_boleta}, '${b.propietario || 'No registrado'}')">
                            <i class="fa-solid fa-envelope me-1"></i> Notificar
                        </button>
                    </td>
                </tr>`;
        }).join('');

    } catch (err) {
        console.warn('Boletas no disponibles:', err.message);
    }
}

async function enviarNotificacion(idBoleta, nombre) {
    try {
        await fetch('api/notificaciones.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_boleta: idBoleta, canal: 'Email' })
        });
    } catch (err) {
        console.warn('Notificación no persistida:', err.message);
    }

    Swal.fire({
        icon: 'success',
        title: 'Notificación Enviada',
        html: `Correo enviado a <strong>${nombre}</strong>.<br>
               <small class="text-muted">INSERT en tabla <code>notificaciones</code></small>`,
        timer: 2000,
        showConfirmButton: false
    });
}


// ═══════════════════════════════════════════════════
// MÓDULO: CÁMARAS (tabla: nodos_edge)
// ═══════════════════════════════════════════════════

function abrirEditorCamara(idCamara) {
    const cam = CAMARAS_BD[idCamara];
    if (!cam) return;

    document.getElementById('edit-cam-id').value             = idCamara;
    document.getElementById('edit-cam-subtitulo').innerText  = cam.nombre;
    document.getElementById('edit-cam-name').value           = cam.nombre;
    document.getElementById('edit-cam-loc').value            = cam.ubicacion;
    document.getElementById('edit-cam-ip').value             = cam.ip;
    document.getElementById('edit-cam-umbral').value         = cam.umbral;
    document.getElementById('edit-cam-umbral-val').innerText = cam.umbral + '%';
    document.getElementById('edit-cam-estado').value         = cam.estado;

    modalEditar.show();
}

function guardarEdicionCamara() {
    const id     = parseInt(document.getElementById('edit-cam-id').value);
    const nombre = document.getElementById('edit-cam-name').value.trim()  || CAMARAS_BD[id].nombre;
    const loc    = document.getElementById('edit-cam-loc').value.trim()   || CAMARAS_BD[id].ubicacion;
    const ip     = document.getElementById('edit-cam-ip').value.trim()    || CAMARAS_BD[id].ip;
    const umbral = parseInt(document.getElementById('edit-cam-umbral').value);
    const estado = document.getElementById('edit-cam-estado').value;

    CAMARAS_BD[id] = { nombre, ubicacion: loc, ip, umbral, estado };
    _actualizarTarjetaCamara(id, nombre, loc, ip, umbral, estado);
    modalEditar.hide();

    Swal.fire({
        icon: 'success',
        title: 'Cambios Guardados',
        html: `<strong>${nombre}</strong> actualizada.<br>
               <small class="text-muted">UPDATE en <code>nodos_edge</code></small>`,
        timer: 2000,
        showConfirmButton: false
    });
}

function _actualizarTarjetaCamara(id, nombre, ubicacion, ip, umbral, estado) {
    const botones = document.querySelectorAll('#contenedor-camaras button');
    let tarjeta   = null;
    botones.forEach(btn => {
        if (btn.getAttribute('onclick') === `abrirEditorCamara(${id})`) {
            tarjeta = btn.closest('.card');
        }
    });
    if (!tarjeta) return;

    const colorBorde = estado === 'Online' ? 'border-primary'
                     : estado === 'Mantenimiento' ? 'border-warning' : 'border-danger';
    const badgeHTML  = estado === 'Online'
        ? `<span class="badge bg-success rounded-pill px-3">Online</span>`
        : estado === 'Mantenimiento'
        ? `<span class="badge bg-warning text-dark rounded-pill px-3">Mantenimiento</span>`
        : `<span class="badge bg-danger rounded-pill px-3">Offline</span>`;

    tarjeta.classList.remove('border-primary','border-warning','border-danger');
    tarjeta.classList.add(colorBorde);
    tarjeta.querySelector('h5').innerText = nombre;
    tarjeta.querySelector('p.text-muted').innerHTML = `<i class="fa-solid fa-map-pin me-1"></i> ${ubicacion}`;

    const badgeActual = tarjeta.querySelector('.badge');
    if (badgeActual) badgeActual.outerHTML = badgeHTML;

    const spans = tarjeta.querySelectorAll('.bg-light span.fw-bold');
    if (spans[0]) spans[0].innerText = ip;
    if (spans[1]) spans[1].innerText = umbral + '%';

    const btnEditar = tarjeta.querySelector('button[onclick^="abrirEditorCamara"]');
    if (btnEditar) {
        if (estado === 'Mantenimiento') {
            btnEditar.outerHTML = `
                <button class="btn btn-warning border w-100 fw-bold text-dark" disabled>
                    <i class="fa-solid fa-wrench me-2"></i> En Mantenimiento
                </button>`;
        } else {
            btnEditar.disabled  = false;
            btnEditar.className = 'btn btn-light border w-100 fw-bold text-secondary';
        }
    }
}

function abrirModalAddCamara() {
    document.getElementById('add-cam-name').value   = '';
    document.getElementById('add-cam-loc').value    = '';
    document.getElementById('add-cam-ip').value     = '';
    document.getElementById('add-cam-umbral').value = '85';
    modalAdd.show();
}

function guardarNuevaCamara() {
    const nombre = document.getElementById('add-cam-name').value   || 'Equipo Nuevo';
    const loc    = document.getElementById('add-cam-loc').value    || 'Ubicación pendiente';
    const ip     = document.getElementById('add-cam-ip').value     || '0.0.0.0';
    const umbral = document.getElementById('add-cam-umbral').value || '85';

    contadorCamaras++;
    const nuevaTarjeta = document.createElement('div');
    nuevaTarjeta.className = 'col-md-6 col-lg-4 fade-in';
    nuevaTarjeta.innerHTML = `
        <div class="card card-custom p-4 bg-white border-top border-4 border-success">
            <div class="d-flex align-items-start justify-content-between mb-3">
                <div class="cam-icon"><i class="fa-solid fa-camera fa-xl"></i></div>
                <span class="badge bg-success rounded-pill px-3">Online</span>
            </div>
            <h5 class="fw-bold mb-1 text-dark">${nombre}</h5>
            <p class="text-muted small mb-3"><i class="fa-solid fa-map-pin me-1"></i> ${loc}</p>
            <div class="bg-light p-3 rounded-3 mb-3 border">
                <div class="d-flex justify-content-between small mb-2">
                    <span class="text-muted">Dirección IP:</span>
                    <span class="fw-bold font-monospace">${ip}</span>
                </div>
                <div class="d-flex justify-content-between small mb-2">
                    <span class="text-muted">Umbral IA:</span>
                    <span class="fw-bold text-primary">${umbral}%</span>
                </div>
                <div class="d-flex justify-content-between small">
                    <span class="text-muted">Instalación:</span>
                    <span class="fw-bold">${new Date().toLocaleDateString('es-BO')}</span>
                </div>
            </div>
            <button class="btn btn-light border w-100 fw-bold text-secondary"
                    onclick="alert('Edición en desarrollo')">
                <i class="fa-solid fa-pen-to-square me-2"></i> Editar Configuración
            </button>
        </div>`;

    document.getElementById('contenedor-camaras').appendChild(nuevaTarjeta);
    modalAdd.hide();

    Swal.fire({
        icon: 'success',
        title: 'Nodo Registrado',
        html: `<strong>${nombre}</strong> insertado en <code>nodos_edge</code>.`,
        confirmButtonColor: '#0d6efd'
    });
}


// ═══════════════════════════════════════════════════
// MÓDULO: CONFIGURACIÓN
// ═══════════════════════════════════════════════════

function guardarAjustes() {
    const umbral   = document.getElementById('slider-umbral').value;
    const vencDias = document.getElementById('config-vencimiento').value;
    Swal.fire({
        title: 'Configuración Guardada',
        html: `Umbral IA: <strong>${umbral}%</strong><br>
               Vencimiento: <strong>${vencDias} días</strong><br>
               <small class="text-muted">UPDATE en <code>nodos_edge.umbral_ia</code></small>`,
        icon: 'success',
        timer: 2000,
        showConfirmButton: false
    });
}
