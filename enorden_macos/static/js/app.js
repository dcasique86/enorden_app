/**
 * Tecnosport - Sistema de Cuentas por Cobrar
 * JavaScript Principal - v2.0
 */

// ==================== CONFIGURACIÓN ====================
const CONFIG = {
    API_BASE: '/api',
    TOAST_DURATION: 4000,
    DEBOUNCE_DELAY: 300,
    CURRENCY_LOCALE: 'es-CO',
    CURRENCY_CODE: 'COP'
};

// ==================== THEME MANAGER ====================
const Theme = {
    init() {
        const toggleBtn = document.getElementById('theme-toggle');
        if (!toggleBtn) return;
        
        toggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            // Efecto sutil de rotación al hacer clic
            toggleBtn.style.transform = 'rotate(360deg)';
            setTimeout(() => {
                toggleBtn.style.transform = '';
            }, 300);
        });
    }
};

// Inicializar tema al cargar el script
Theme.init();

// ==================== UTILIDADES ====================

/**
 * Formatea un número como moneda
 */
function formatCurrency(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return '$0';
    return new Intl.NumberFormat(CONFIG.CURRENCY_LOCALE, {
        style: 'currency',
        currency: CONFIG.CURRENCY_CODE,
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

/**
 * Convierte un valor de input formateado con puntos de miles a un float limpio.
 */
function parseCurrencyInput(value) {
    if (value === null || value === undefined || value === '') return 0;
    // Eliminar todos los puntos (separadores de miles) y convertir a float
    const cleanValue = String(value).replace(/\./g, '');
    return parseFloat(cleanValue) || 0;
}

/**
 * Formatea un elemento input con separadores de miles sobre la marcha
 */
function formatInput(el) {
    let value = el.value.replace(/\D/g, ''); // Remover caracteres que no sean dígitos
    if (value === '') {
        el.value = '';
        return;
    }
    // Formatear usando separadores de miles
    el.value = value.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

/**
 * Configura el formateo de miles dinámico en todos los campos numéricos de dinero
 */
function setupCurrencyInputs() {
    const inputs = document.querySelectorAll(
        "input#monto, input#precio-unitario, input[name='precio_compra'], input[name='precio_venta']"
    );
    
    inputs.forEach(input => {
        // Cambiar dinámicamente tipo a text para admitir caracteres de formato
        if (input.type === 'number') {
            input.type = 'text';
            input.inputMode = 'numeric';
        }
        
        // Formatear valor inicial si lo tuviera
        formatInput(input);
        
        // Escuchar cambios
        input.addEventListener('input', () => {
            formatInput(input);
        });
    });
}

/**
 * Formatea una fecha
 */
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat('es-CO', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    }).format(date);
}

/**
 * Formatea fecha y hora
 */
function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat('es-CO', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

/**
 * Obtiene las iniciales de un nombre
 */
function getInitials(name) {
    if (!name) return '??';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
}

/**
 * Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function lockSubmitButton(form, loadingText = 'Registrando...') {
    const btn = form.querySelector('button[type="submit"]');
    if (!btn || btn.disabled) return null;

    const originalText = btn.textContent;
    btn.disabled = true;
    btn.dataset.originalText = originalText;
    btn.textContent = loadingText;
    return btn;
}

function unlockSubmitButton(btn, fallbackText = null) {
    if (!btn) return;

    btn.disabled = false;
    btn.textContent = fallbackText || btn.dataset.originalText || btn.textContent;
    delete btn.dataset.originalText;
}

/**
 * Escapa HTML para prevenir XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Valida si un cliente tiene teléfono válido
 */
function tieneTelefonoValido(telefono) {
    if (!telefono) return false;
    // Convertir a string si es número
    const telStr = String(telefono).trim();
    return telStr !== '' && telStr !== 'null' && telStr !== 'undefined';
}

/**
 * Formatea teléfono para mostrar
 */
function formatTelefono(telefono) {
    if (!telefono) return 'Sin teléfono';
    const telStr = String(telefono).trim();
    return telStr || 'Sin teléfono';
}

// ==================== API CLIENT ====================

const API = {
    async request(endpoint, options = {}) {
        const url = CONFIG.API_BASE + endpoint;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        const mergedOptions = { ...defaultOptions, ...options };
        if (options.body && typeof options.body === 'object') {
            mergedOptions.body = JSON.stringify(options.body);
        }
        
        try {
            const response = await fetch(url, mergedOptions);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'Error en la solicitud');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },
    
    // Clientes
    getClientes: () => API.request('/clientes'),
    buscarClientes: (q) => API.request(`/clientes/buscar?q=${encodeURIComponent(q)}`),
    getCliente: (id) => API.request(`/clientes/${id}`),
    crearCliente: (data) => API.request('/clientes', { method: 'POST', body: data }),
    actualizarCliente: (id, data) => API.request(`/clientes/${id}`, { method: 'PUT', body: data }),
    eliminarCliente: (id) => API.request(`/clientes/${id}`, { method: 'DELETE' }),
    
    // Movimientos
    getMovimientos: (limite = 100) => API.request(`/movimientos?limite=${limite}`),
    getMovimientosHoy: () => API.request('/movimientos/hoy'),
    getMovimientosCliente: (id) => API.request(`/movimientos/cliente/${id}`),
    crearMovimiento: (data) => API.request('/movimientos', { method: 'POST', body: data }),
    
    // Dashboard y reportes
    getDashboard: () => API.request('/dashboard'),
    getHistorial: (id) => API.request(`/historial/${id}`),
    
    // Proveedores
    getProveedores: () => API.request('/proveedores'),
    buscarProveedores: (q) => API.request(`/proveedores/buscar?q=${encodeURIComponent(q)}`),
    getProveedor: (id) => API.request(`/proveedores/${id}`),
    crearProveedor: (data) => API.request('/proveedores', { method: 'POST', body: data }),
    actualizarProveedor: (id, data) => API.request(`/proveedores/${id}`, { method: 'PUT', body: data }),
    eliminarProveedor: (id) => API.request(`/proveedores/${id}`, { method: 'DELETE' }),
    
    // Movimientos Proveedores
    getMovimientosProveedor: (limite = 100) => API.request(`/movimientos-proveedor?limite=${limite}`),
    getMovimientosProveedorHoy: () => API.request('/movimientos-proveedor/hoy'),
    getMovimientosByProveedor: (id) => API.request(`/movimientos-proveedor/proveedor/${id}`),
    crearMovimientoProveedor: (data) => API.request('/movimientos-proveedor', { method: 'POST', body: data }),
    
    // Dashboard y reportes Proveedores
    getDashboardProveedores: () => API.request('/dashboard-proveedores'),
    getHistorialProveedor: (id) => API.request(`/historial-proveedor/${id}`),

    // Inventario y ventas
    getProductos: () => API.request('/productos'),
    buscarProductos: (q) => API.request(`/productos/buscar?q=${encodeURIComponent(q)}`),
    getProducto: (id) => API.request(`/productos/${id}`),
    crearProducto: (data) => API.request('/productos', { method: 'POST', body: data }),
    actualizarProducto: (id, data) => API.request(`/productos/${id}`, { method: 'PUT', body: data }),
    eliminarProducto: (id) => API.request(`/productos/${id}`, { method: 'DELETE' }),
    getVentas: (limite = 100) => API.request(`/ventas?limite=${limite}`),
    crearVenta: (data) => API.request('/ventas', { method: 'POST', body: data }),
    getDashboardInventario: () => API.request('/dashboard-inventario'),
    
    // Backups
    getBackups: () => API.request('/backups'),
    crearBackup: () => API.request('/backups', { method: 'POST' }),

    // Gastos y Flujo de Caja
    registrarGasto: (data) => API.request('/gastos', { method: 'POST', body: data }),
    getFlujoCaja: (fecha) => API.request(`/dashboard/flujo-caja${fecha ? '?fecha=' + fecha : ''}`)
};

// ==================== TOAST NOTIFICATIONS ====================

const Toast = {
    container: null,
    
    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    },
    
    show(message, type = 'success') {
        this.init();
        
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${icons[type]}</span>
            <span class="toast-message">${escapeHtml(message)}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
        `;
        
        this.container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, CONFIG.TOAST_DURATION);
    },
    
    success: (msg) => Toast.show(msg, 'success'),
    error: (msg) => Toast.show(msg, 'error'),
    warning: (msg) => Toast.show(msg, 'warning')
};

// ==================== MODAL MANAGER ====================

const Modal = {
    current: null,
    
    open(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            this.current = modal;
            document.body.style.overflow = 'hidden';
        }
    },
    
    close(modalId) {
        const modal = modalId ? document.getElementById(modalId) : this.current;
        if (modal) {
            modal.classList.remove('active');
            this.current = null;
            document.body.style.overflow = '';
        }
    },
    
    closeAll() {
        document.querySelectorAll('.modal-overlay.active').forEach(modal => {
            modal.classList.remove('active');
        });
        this.current = null;
        document.body.style.overflow = '';
    }
};

// Cerrar modal al hacer clic fuera
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        Modal.closeAll();
    }
});

// Cerrar modal con Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        Modal.closeAll();
    }
});

// ==================== LOADING STATES ====================

const Loading = {
    show(container, message = 'Cargando...') {
        const el = typeof container === 'string' ? document.getElementById(container) : container;
        if (el) {
            el.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p style="margin-top: 1rem;">${escapeHtml(message)}</p>
                </div>
            `;
        }
    },
    
    hide(container, content) {
        const el = typeof container === 'string' ? document.getElementById(container) : container;
        if (el && content) {
            el.innerHTML = content;
        }
    }
};

// ==================== SKELETON LOADERS ====================

const Skeleton = {
    statCard: () => `
        <div class="stat-card">
            <div class="skeleton" style="width: 48px; height: 48px; border-radius: 10px; margin-bottom: 1rem;"></div>
            <div class="skeleton" style="width: 60%; height: 12px; margin-bottom: 0.5rem;"></div>
            <div class="skeleton" style="width: 80%; height: 28px;"></div>
        </div>
    `,
    
    timelineItem: () => `
        <div class="timeline-item">
            <div class="skeleton" style="width: 40px; height: 40px; border-radius: 50%;"></div>
            <div style="flex: 1;">
                <div class="skeleton" style="width: 60%; height: 16px; margin-bottom: 0.5rem;"></div>
                <div class="skeleton" style="width: 40%; height: 12px;"></div>
            </div>
        </div>
    `,
    
    clienteItem: () => `
        <div class="cliente-item">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <div class="skeleton" style="width: 40px; height: 40px; border-radius: 50%;"></div>
                <div>
                    <div class="skeleton" style="width: 120px; height: 16px; margin-bottom: 0.25rem;"></div>
                    <div class="skeleton" style="width: 80px; height: 12px;"></div>
                </div>
            </div>
            <div class="skeleton" style="width: 80px; height: 20px;"></div>
        </div>
    `
};

// ==================== PÁGINA: DASHBOARD ====================

const Dashboard = {
    async init() {
        this.setupBusquedaRapida();
        await this.loadStats();
        await this.loadMovimientosHoy();
        await this.loadTopDeudores();
        await this.loadClientesSinAbono();
        await this.loadCarteraAntiguedad();
        await this.loadColaCobro();
        await this.loadUltimosAbonos();
        await this.loadTopProveedores();
    },
    
    setupBusquedaRapida() {
        const searchInput = document.getElementById('busqueda-rapida');
        const resultsContainer = document.getElementById('resultados-busqueda-rapida');
        
        if (!searchInput || !resultsContainer) return;
        
        // Cerrar resultados al hacer clic fuera
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-box-dashboard')) {
                resultsContainer.classList.remove('active');
            }
        });
        
        // Búsqueda con debounce
        const debouncedSearch = debounce(async (query) => {
            if (!query.trim()) {
                resultsContainer.classList.remove('active');
                return;
            }
            
            try {
                const { data } = await API.buscarClientes(query);
                
                if (data.length === 0) {
                    resultsContainer.innerHTML = `
                        <div class="sin-resultados">
                            <div class="sin-resultados-icon">🔍</div>
                            <p>No se encontraron clientes con "${escapeHtml(query)}"</p>
                        </div>
                    `;
                } else {
                    resultsContainer.innerHTML = data.map(cliente => {
                        const tieneDeuda = cliente.saldo > 0;
                        const ultimoAbono = cliente.ultimo_abono;
                        
                        return `
                            <a href="/cliente/${cliente.id}" class="resultado-cliente">
                                <div class="resultado-cliente-info">
                                    <div class="resultado-cliente-avatar">${getInitials(cliente.nombre)}</div>
                                    <div class="resultado-cliente-datos">
                                        <h4>${escapeHtml(cliente.nombre)}</h4>
                                        <p>${formatTelefono(cliente.telefono)}</p>
                                    </div>
                                </div>
                                <div class="resultado-cliente-saldo">
                                    <div class="deuda ${!tieneDeuda ? 'sin-deuda' : ''}">${formatCurrency(Math.abs(cliente.saldo))}</div>
                                    ${ultimoAbono ? 
                                        `<div class="ultimo-abono">Últ. abono: ${formatDate(ultimoAbono.fecha)}</div>` : 
                                        `<div class="ultimo-abono">Sin abonos</div>`
                                    }
                                </div>
                            </a>
                        `;
                    }).join('');
                }
                
                resultsContainer.classList.add('active');
                
            } catch (error) {
                console.error('Error en búsqueda:', error);
            }
        }, CONFIG.DEBOUNCE_DELAY);
        
        searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value));
        
        // Búsqueda inmediata al presionar Enter
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                debouncedSearch.cancel && debouncedSearch.cancel();
                debouncedSearch(searchInput.value);
            }
        });
        
        // Mostrar resultados al enfocar si hay texto
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim() && resultsContainer.innerHTML) {
                resultsContainer.classList.add('active');
            }
        });
    },
    
    async loadStats() {
        const container = document.getElementById('stats-container');
        if (!container) return;
        
        try {
            const { data } = await API.getDashboard();
            
            container.innerHTML = `
                <div class="stat-card fade-in">
                    <div class="stat-icon">💰</div>
                    <div class="stat-label">Total Prestado</div>
                    <div class="stat-value">${formatCurrency(data.total_prestado)}</div>
                </div>
                <div class="stat-card success fade-in">
                    <div class="stat-icon">✓</div>
                    <div class="stat-label">Total Recuperado</div>
                    <div class="stat-value text-success">${formatCurrency(data.total_abonado)}</div>
                </div>
                <div class="stat-card danger fade-in">
                    <div class="stat-icon">📊</div>
                    <div class="stat-label">Deuda Activa</div>
                    <div class="stat-value text-danger">${formatCurrency(data.deuda_activa)}</div>
                </div>
                <div class="stat-card fade-in">
                    <div class="stat-icon">👥</div>
                    <div class="stat-label">Clientes Activos</div>
                    <div class="stat-value">${data.clientes_activos}</div>
                </div>
            `;
            
            // Actualizar stats del día si existen los elementos
            const prestamosHoy = document.getElementById('prestamos-hoy');
            const abonosHoy = document.getElementById('abonos-hoy');
            if (prestamosHoy) prestamosHoy.textContent = formatCurrency(data.prestamos_hoy);
            if (abonosHoy) abonosHoy.textContent = formatCurrency(data.abonos_hoy);
            
        } catch (error) {
            container.innerHTML = `
                <div class="stat-card">
                    <p class="text-danger">Error al cargar estadísticas</p>
                    <button class="btn btn-sm btn-secondary mt-1" onclick="Dashboard.loadStats()">Reintentar</button>
                </div>
            `;
        }
    },
    
    async loadMovimientosHoy() {
        const container = document.getElementById('movimientos-lista');
        if (!container) return;
        
        try {
            const { data } = await API.getMovimientosHoy();
            
            if (data.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📝</div>
                        <div class="empty-state-title">Sin movimientos hoy</div>
                        <div class="empty-state-text">Los movimientos del día aparecerán aquí</div>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = `
                <div class="timeline stagger-in">
                    ${data.slice(0, 10).map(mov => `
                        <div class="timeline-item ${mov.tipo}">
                            <div class="timeline-icon">${mov.tipo === 'prestamo' ? '📤' : '📥'}</div>
                            <div class="timeline-content">
                                <div class="timeline-title">${escapeHtml(mov.cliente_nombre)}</div>
                                <div class="timeline-meta">${escapeHtml(mov.descripcion || (mov.tipo === 'prestamo' ? 'Préstamo' : 'Abono'))}</div>
                            </div>
                            <div class="timeline-amount ${mov.tipo === 'prestamo' ? 'negative' : 'positive'}">
                                ${mov.tipo === 'prestamo' ? '+' : '-'}${formatCurrency(mov.monto)}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar movimientos</p>`;
        }
    },
    
    async loadTopDeudores() {
        const container = document.getElementById('top-deudores');
        if (!container) return;
        
        try {
            const { data } = await API.getDashboard();
            const topDeudores = data.top_deudores;
            
            if (topDeudores.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">🎉</div>
                        <div class="empty-state-title">¡Excelente!</div>
                        <div class="empty-state-text">No hay deudas activas</div>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = `
                <div class="clientes-list stagger-in">
                    ${topDeudores.map(cliente => `
                        <div class="cliente-item">
                            <a href="/cliente/${cliente.id}" style="display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; color: inherit; text-decoration: none;">
                                <div class="cliente-avatar">${getInitials(cliente.nombre)}</div>
                                <div style="min-width: 0;">
                                    <div class="cliente-nombre">${escapeHtml(cliente.nombre)}</div>
                                </div>
                            </a>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <div class="cliente-saldo">${formatCurrency(cliente.saldo)}</div>
                                ${cliente.telefono ? `
                                    <button class="btn-whatsapp-small" onclick="event.preventDefault(); event.stopPropagation(); WhatsApp.enviarRecordatorio('${cliente.telefono}', '${escapeHtml(cliente.nombre)}', ${cliente.saldo}, null)" title="Enviar WhatsApp">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar datos</p>`;
        }
    },
    
    async loadClientesSinAbono() {
        const container = document.getElementById('clientes-sin-abono');
        if (!container) return;
        
        try {
            const { data } = await API.getDashboard();
            const clientes = data.clientes_sin_abonos;
            
            if (clientes.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">✓</div>
                        <div class="empty-state-title">Todo al día</div>
                        <div class="empty-state-text">Todos los clientes tienen abonos recientes</div>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = `
                <div class="clientes-list stagger-in">
                    ${clientes.map(cliente => `
                        <div class="cliente-item">
                            <a href="/cliente/${cliente.id}" style="display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; color: inherit; text-decoration: none;">
                                <div class="cliente-avatar">${getInitials(cliente.nombre)}</div>
                                <div style="min-width: 0;">
                                    <div class="cliente-nombre">${escapeHtml(cliente.nombre)}</div>
                                    <div class="cliente-deuda">Sin abono: ${cliente.dias === 'Nunca' ? 'Nunca' : cliente.dias + ' días'}</div>
                                </div>
                            </a>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <div class="cliente-saldo">${formatCurrency(cliente.saldo)}</div>
                                ${cliente.telefono ? `
                                    <button class="btn-whatsapp-small" onclick="event.preventDefault(); event.stopPropagation(); WhatsApp.enviarRecordatorio('${cliente.telefono}', '${escapeHtml(cliente.nombre)}', ${cliente.saldo}, ${cliente.dias === 'Nunca' ? 0 : cliente.dias})" title="Enviar WhatsApp">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar datos</p>`;
        }
    },

    async loadCarteraAntiguedad() {
        const container = document.getElementById('aging-buckets');
        if (!container) return;

        try {
            const { data } = await API.getDashboard();
            const buckets = data.cartera_antiguedad || [];

            if (buckets.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-title">Sin cartera activa</div>
                    </div>
                `;
                return;
            }

            container.innerHTML = `
                <div class="aging-grid">
                    ${buckets.map(bucket => `
                        <div class="aging-bucket">
                            <div class="label">${escapeHtml(bucket.label)}</div>
                            <div class="amount">${formatCurrency(bucket.total || 0)}</div>
                            <div class="count">${bucket.clientes || 0} cliente${bucket.clientes === 1 ? '' : 's'}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al calcular cartera</p>`;
        }
    },

    async loadColaCobro() {
        const container = document.getElementById('collection-queue');
        if (!container) return;

        try {
            const { data } = await API.getDashboard();
            const clientes = data.cola_cobro || [];

            if (clientes.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-title">Sin cobros pendientes</div>
                        <div class="empty-state-text">No hay clientes con saldo activo</div>
                    </div>
                `;
                return;
            }

            container.innerHTML = `
                <div class="collection-list">
                    ${clientes.map(cliente => {
                        const dias = cliente.dias_sin_abonar === null || cliente.dias_sin_abonar === undefined
                            ? 'Sin abonos'
                            : `${cliente.dias_sin_abonar} dias sin abono`;
                        return `
                            <div class="collection-item">
                                <a href="/cliente/${cliente.id}" style="min-width: 0; color: inherit; text-decoration: none;">
                                    <div class="collection-name">${escapeHtml(cliente.nombre)}</div>
                                    <div class="collection-meta">${dias} - ${escapeHtml(cliente.proxima_accion || 'Enviar recordatorio')}</div>
                                </a>
                                <div style="display: flex; align-items: center; gap: 0.75rem;">
                                    <span class="priority-badge ${escapeHtml(cliente.prioridad || 'normal')}">${escapeHtml(cliente.prioridad || 'normal')}</span>
                                    <strong>${formatCurrency(cliente.saldo || 0)}</strong>
                                    ${cliente.telefono ? `
                                        <button class="btn-whatsapp-small" onclick="event.preventDefault(); event.stopPropagation(); WhatsApp.enviarRecordatorio('${cliente.telefono}', '${escapeHtml(cliente.nombre)}', ${cliente.saldo || 0}, ${cliente.dias_sin_abonar || 0})" title="Enviar WhatsApp">
                                            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                        </button>
                                    ` : ''}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al priorizar cobros</p>`;
        }
    },
    
    async loadUltimosAbonos() {
        const container = document.getElementById('ultimos-abonos');
        if (!container) return;
        
        try {
            const { data } = await API.getDashboard();
            const abonos = data.ultimos_abonos;
            
            if (abonos.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">💸</div>
                        <div class="empty-state-title">Sin abonos recientes</div>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = `
                <div class="timeline stagger-in">
                    ${abonos.map(abono => `
                        <div class="timeline-item abono">
                            <div class="timeline-icon">📥</div>
                            <div class="timeline-content">
                                <div class="timeline-title">${escapeHtml(abono.cliente_nombre)}</div>
                                <div class="timeline-meta">${formatDate(abono.fecha)}${abono.descripcion ? ' • ' + escapeHtml(abono.descripcion) : ''}</div>
                            </div>
                            <div class="timeline-amount positive">${formatCurrency(abono.monto)}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar datos</p>`;
        }
    },
    
    async loadTopProveedores() {
        const container = document.getElementById('top-proveedores');
        if (!container) return;
        
        try {
            const { data } = await API.getDashboardProveedores();
            const topAcreedores = data.top_acreedores;
            
            if (topAcreedores.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">✓</div>
                        <div class="empty-state-title">Sin deudas</div>
                        <div class="empty-state-text">No hay deudas con proveedores</div>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = `
                <div class="clientes-list stagger-in">
                    ${topAcreedores.map(proveedor => `
                        <div class="cliente-item">
                            <a href="/proveedor/${proveedor.id}" style="display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; color: inherit; text-decoration: none;">
                                <div class="cliente-avatar" style="background: #ea580c;">${getInitials(proveedor.nombre)}</div>
                                <div style="min-width: 0;">
                                    <div class="cliente-nombre">${escapeHtml(proveedor.nombre)}</div>
                                </div>
                            </a>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <div class="cliente-saldo" style="color: #ea580c;">${formatCurrency(proveedor.saldo)}</div>
                                ${proveedor.telefono ? `
                                    <button class="btn-whatsapp-small" style="background: #ea580c;" onclick="event.preventDefault(); event.stopPropagation(); WhatsApp.open('${proveedor.telefono}', 'Hola ${escapeHtml(proveedor.nombre)},')" title="Enviar WhatsApp">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar datos</p>`;
        }
    }
};

// ==================== PÁGINA: CLIENTES ====================

const Clientes = {
    async init() {
        await this.loadClientes();
        this.setupSearch();
    },
    
    async loadClientes() {
        const container = document.getElementById('clientes-list');
        if (!container) return;
        
        container.innerHTML = Array(5).fill(Skeleton.clienteItem()).join('');
        
        try {
            const { data } = await API.getClientes();
            
            if (data.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">👥</div>
                        <div class="empty-state-title">No hay clientes</div>
                        <div class="empty-state-text">Agrega tu primer cliente para comenzar</div>
                        <button class="btn btn-primary mt-2" onclick="Modal.open('modal-nuevo-cliente')">
                            + Nuevo Cliente
                        </button>
                    </div>
                `;
                return;
            }
            
            // Ordenar por saldo descendente
            data.sort((a, b) => (b.saldo || 0) - (a.saldo || 0));
            
            container.innerHTML = `
                <div class="clientes-list stagger-in">
                    ${data.map(cliente => `
                        <div class="cliente-item stagger-in">
                            <a href="/cliente/${cliente.id}" style="display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; color: inherit; text-decoration: none;">
                                <div class="cliente-avatar">${getInitials(cliente.nombre)}</div>
                                <div style="min-width: 0;">
                                    <div class="cliente-nombre">${escapeHtml(cliente.nombre)}</div>
                                    <div class="cliente-deuda">${formatTelefono(cliente.telefono)}</div>
                                </div>
                            </a>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <div class="cliente-saldo">${formatCurrency(cliente.saldo)}</div>
                                ${cliente.telefono ? `
                                    <button class="btn-whatsapp-small" onclick="event.preventDefault(); event.stopPropagation(); WhatsApp.enviarRecordatorio('${cliente.telefono}', '${escapeHtml(cliente.nombre)}', ${cliente.saldo || 0}, null)" title="Enviar WhatsApp">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `
                <div class="empty-state">
                    <p class="text-danger">Error al cargar clientes</p>
                    <button class="btn btn-secondary mt-1" onclick="Clientes.loadClientes()">Reintentar</button>
                </div>
            `;
        }
    },
    
    setupSearch() {
        const searchInput = document.getElementById('search-clientes');
        if (!searchInput) return;
        
        const debouncedSearch = debounce(async (query) => {
            const container = document.getElementById('clientes-list');
            
            if (!query.trim()) {
                this.loadClientes();
                return;
            }
            
            try {
                const { data } = await API.buscarClientes(query);
                
                if (data.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">🔍</div>
                            <div class="empty-state-title">Sin resultados</div>
                            <div class="empty-state-text">No se encontraron clientes con "${escapeHtml(query)}"</div>
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = `
                    <div class="clientes-list stagger-in">
                        ${data.map(cliente => `
                            <a href="/cliente/${cliente.id}" class="cliente-item">
                                <div class="cliente-info">
                                    <div class="cliente-avatar">${getInitials(cliente.nombre)}</div>
                                    <div>
                                        <div class="cliente-nombre">${escapeHtml(cliente.nombre)}</div>
                                        <div class="cliente-deuda">${formatTelefono(cliente.telefono)}</div>
                                    </div>
                                </div>
                                <div class="cliente-saldo">${formatCurrency(cliente.saldo)}</div>
                            </a>
                        `).join('')}
                    </div>
                `;
            } catch (error) {
                Toast.error('Error en la búsqueda');
            }
        }, CONFIG.DEBOUNCE_DELAY);
        
        searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value));
    },
    
    async crearCliente(formData) {
        try {
            const result = await API.crearCliente(formData);
            Toast.success('Cliente creado exitosamente');
            Modal.closeAll();
            this.loadClientes();
            return result;
        } catch (error) {
            Toast.error(error.message || 'Error al crear cliente');
            throw error;
        }
    }
};

// ==================== PÁGINA: DETALLE CLIENTE ====================

const ClienteDetalle = {
    clienteId: null,
    
    async init(clienteId) {
        this.clienteId = clienteId;
        await this.loadData();
    },
    
    async loadData() {
        const container = document.getElementById('cliente-content');
        if (!container) return;
        
        Loading.show(container, 'Cargando información del cliente...');
        
        try {
            const { data } = await API.getHistorial(this.clienteId);
            const { cliente, resumen, movimientos } = data;
            
            const saldoClass = resumen.saldo > 0 ? 'negative' : (resumen.saldo < 0 ? 'positive' : 'zero');
            const tieneTelefono = tieneTelefonoValido(cliente.telefono);
            const tieneDeuda = resumen.saldo > 0;
            
            container.innerHTML = `
                <div class="fade-in">
                    <!-- Header del cliente -->
                    <div style="text-align: center; margin-bottom: 2rem;">
                        <div class="avatar-lg">${getInitials(cliente.nombre)}</div>
                        <h1 style="margin: 1rem 0 0.5rem;">${escapeHtml(cliente.nombre)}</h1>
                        <p class="text-muted">${formatTelefono(cliente.telefono)}</p>
                        ${tieneTelefono ? `
                            <a href="https://wa.me/${WhatsApp.formatPhone(cliente.telefono)}" target="_blank" 
                               class="btn btn-sm" 
                               style="background: #25D366; color: white; margin-top: 0.5rem;">
                                📱 Contactar por WhatsApp
                            </a>
                        ` : ''}
                    </div>
                    
                    <!-- Saldo grande -->
                    <div class="saldo-grande">
                        <div class="saldo-label">Deuda Actual</div>
                        <div class="saldo-valor ${saldoClass}">${formatCurrency(Math.abs(resumen.saldo))}</div>
                    </div>
                    
                    <!-- Stats del cliente -->
                    <div class="stats-grid" style="margin-bottom: 2rem;">
                        <div class="stat-card">
                            <div class="stat-label">Total Prestado</div>
                            <div class="stat-value">${formatCurrency(resumen.total_prestado)}</div>
                        </div>
                        <div class="stat-card success">
                            <div class="stat-label">Total Abonado</div>
                            <div class="stat-value text-success">${formatCurrency(resumen.total_abonado)}</div>
                        </div>
                    </div>
                    
                    <!-- Acciones -->
                    <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                        <a href="/nuevo-prestamo?cliente=${cliente.id}" class="btn btn-danger btn-lg btn-block">
                            📤 Registrar Préstamo
                        </a>
                        <a href="/nuevo-abono?cliente=${cliente.id}" class="btn btn-success btn-lg btn-block">
                            📥 Registrar Abono
                        </a>
                    </div>
                    
                    <!-- Botón WhatsApp para recordatorio -->
                    ${tieneTelefono && tieneDeuda ? `
                        <button onclick="WhatsApp.enviarRecordatorio('${cliente.telefono}', '${escapeHtml(cliente.nombre)}', ${resumen.saldo}, '')" 
                                class="btn btn-lg btn-block" 
                                style="background: #25D366; color: white; margin-bottom: 2rem;">
                            📱 Enviar recordatorio de deuda por WhatsApp
                        </button>
                    ` : ''}
                    
                    <!-- Historial -->
                    <div class="section">
                        <div class="section-header">
                            <h3 class="section-title">
                                <span class="section-title-icon">📋</span>
                                Historial de Movimientos
                            </h3>
                        </div>
                        
                        ${movimientos.length === 0 ? `
                            <div class="empty-state">
                                <div class="empty-state-icon">📝</div>
                                <div class="empty-state-title">Sin movimientos</div>
                                <div class="empty-state-text">Los movimientos aparecerán aquí</div>
                            </div>
                        ` : `
                            <div style="overflow-x: auto;">
                                <table class="historial-table">
                                    <thead>
                                        <tr>
                                            <th>Fecha</th>
                                            <th>Tipo</th>
                                            <th>Descripción</th>
                                            <th>Monto</th>
                                            <th>Saldo</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${movimientos.map(mov => `
                                            <tr>
                                                <td>${formatDate(mov.fecha)}</td>
                                                <td><span class="badge badge-${mov.tipo}">${mov.tipo}</span></td>
                                                <td>${escapeHtml(mov.descripcion || '-')}</td>
                                                <td class="${mov.tipo === 'prestamo' ? 'text-danger' : 'text-success'}">
                                                    ${mov.tipo === 'prestamo' ? '+' : '-'}${formatCurrency(mov.monto)}
                                                </td>
                                                <td>${formatCurrency(mov.saldo_acumulado)}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        `}
                    </div>
                </div>
            `;
            
        } catch (error) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">❌</div>
                    <div class="empty-state-title">Error</div>
                    <div class="empty-state-text">${escapeHtml(error.message)}</div>
                    <a href="/" class="btn btn-primary mt-2">Volver al inicio</a>
                </div>
            `;
        }
    }
};

// ==================== PÁGINA: NUEVO PRÉSTAMO ====================

const NuevoPrestamo = {
    selectedCliente: null,
    
    async init(clienteId = null) {
        this.setupForm();
        this.setupClienteSearch();
        
        if (clienteId) {
            await this.selectCliente(clienteId);
        }
    },
    
    setupForm() {
        const form = document.getElementById('form-prestamo');
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!this.selectedCliente) {
                Toast.error('Selecciona un cliente');
                return;
            }
            
            const monto = parseCurrencyInput(document.getElementById('monto').value);
            const descripcion = document.getElementById('descripcion').value;
            
            if (!monto || monto <= 0) {
                Toast.error('Ingresa un monto válido');
                return;
            }
            
            try {
                const btn = lockSubmitButton(form);
                if (!btn) return;
                
                // Guardar saldo anterior
                const saldoAnterior = this.selectedCliente.saldo || 0;
                
                await API.crearMovimiento({
                    cliente_id: this.selectedCliente.id,
                    tipo: 'prestamo',
                    descripcion: descripcion || 'Mercancía prestada',
                    monto: monto
                });
                
                const saldoNuevo = saldoAnterior + monto;
                
                Toast.success('Préstamo registrado exitosamente');
                
                // Mostrar panel de confirmación con WhatsApp
                this.mostrarConfirmacion(monto, descripcion || 'Mercancía prestada', saldoAnterior, saldoNuevo);
                
            } catch (error) {
                Toast.error(error.message || 'Error al registrar préstamo');
                const btn = form.querySelector('button[type="submit"]');
                unlockSubmitButton(btn);
                btn.textContent = 'Registrar Préstamo';
            }
        });
    },
    
    mostrarConfirmacion(monto, descripcion, saldoAnterior, saldoNuevo) {
        const container = document.getElementById('form-container');
        if (!container) return;
        
        const tieneTelefono = tieneTelefonoValido(this.selectedCliente.telefono);
        
        container.innerHTML = `
            <div class="fade-in" style="text-align: center; padding: 2rem 0;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">✅</div>
                <h3 style="margin-bottom: 0.5rem;">¡Préstamo Registrado!</h3>
                <p class="text-muted" style="margin-bottom: 2rem;">
                    ${formatCurrency(monto)} agregados a ${escapeHtml(this.selectedCliente.nombre)}
                </p>
                
                <div style="background: var(--bg-main); border-radius: var(--radius-lg); padding: 1.5rem; margin-bottom: 1.5rem;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: left;">
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Mercancía</p>
                            <p style="font-weight: 600;">${escapeHtml(descripcion)}</p>
                        </div>
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Saldo actual</p>
                            <p style="font-weight: 700; font-size: 1.25rem; color: var(--danger);">${formatCurrency(saldoNuevo)}</p>
                        </div>
                    </div>
                </div>
                
                ${tieneTelefono ? `
                    <button onclick="WhatsApp.enviarComprobante('prestamo', '${this.selectedCliente.id}', '${escapeHtml(this.selectedCliente.nombre)}', '${this.selectedCliente.telefono}', ${monto}, '${escapeHtml(descripcion)}', ${saldoAnterior}, ${saldoNuevo})" 
                            class="btn btn-lg btn-block" 
                            style="background: #25D366; color: white; margin-bottom: 0.5rem;">
                        📱 Notificar por WhatsApp
                    </button>
                    <button onclick="WhatsApp.generarComprobante('prestamo', '${escapeHtml(this.selectedCliente.nombre)}', ${monto}, ${saldoNuevo}, '${escapeHtml(descripcion)}')"
                            class="btn btn-lg btn-block"
                            style="background: var(--bg-input); color: var(--text-primary); border: 1px solid var(--border-color); margin-bottom: 1rem;">
                        📸 Descargar comprobante como imagen
                    </button>
                ` : `
                    <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid var(--warning); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1rem;">
                        <p style="font-size: 0.875rem; color: var(--warning);">
                            ⚠️ El cliente no tiene teléfono registrado
                        </p>
                        <button onclick="WhatsApp.generarComprobante('prestamo', '${escapeHtml(this.selectedCliente.nombre)}', ${monto}, ${saldoNuevo}, '${escapeHtml(descripcion)}')"
                                class="btn btn-block mt-1"
                                style="background: var(--bg-input); color: var(--text-primary); border: 1px solid var(--border-color);">
                            📸 Descargar comprobante como imagen
                        </button>
                    </div>
                `}
                
                <div style="display: flex; gap: 1rem;">
                    <a href="/cliente/${this.selectedCliente.id}" class="btn btn-primary btn-lg" style="flex: 1;">
                        Ver Cliente
                    </a>
                    <a href="/" class="btn btn-secondary btn-lg" style="flex: 1;">
                        Dashboard
                    </a>
                </div>
            </div>
        `;
    },
    
    setupClienteSearch() {
        const searchInput = document.getElementById('buscar-cliente');
        const resultsContainer = document.getElementById('resultados-busqueda');
        if (!searchInput || !resultsContainer) {
            console.error('No se encontraron elementos de búsqueda');
            return;
        }
        
        // Función para realizar la búsqueda
        const doSearch = async (query) => {
            resultsContainer.innerHTML = '<div class="search-result-item"><span class="text-muted">Buscando...</span></div>';
            resultsContainer.classList.add('active');
            
            try {
                const { data } = await API.buscarClientes(query);
                
                if (!data || data.length === 0) {
                    resultsContainer.innerHTML = `
                        <div class="search-result-item" style="justify-content: center;">
                            <span class="text-muted">No se encontraron clientes</span>
                        </div>
                    `;
                } else {
                    resultsContainer.innerHTML = data.map(cliente => `
                        <div class="search-result-item" onclick="NuevoPrestamo.selectCliente('${cliente.id}')">
                            <div class="cliente-info">
                                <div class="cliente-avatar">${getInitials(cliente.nombre)}</div>
                                <div>
                                    <div class="cliente-nombre">${escapeHtml(cliente.nombre)}</div>
                                    <div class="cliente-deuda">${formatTelefono(cliente.telefono)}</div>
                                </div>
                            </div>
                            <div class="cliente-saldo">${formatCurrency(cliente.saldo || 0)}</div>
                        </div>
                    `).join('');
                }
                
            } catch (error) {
                console.error('Error en búsqueda:', error);
                resultsContainer.innerHTML = `
                    <div class="search-result-item" style="justify-content: center;">
                        <span class="text-danger">Error al buscar: ${escapeHtml(error.message)}</span>
                    </div>
                `;
            }
        };
        
        // Búsqueda con debounce
        const debouncedSearch = debounce(doSearch, CONFIG.DEBOUNCE_DELAY);
        
        // Búsqueda al escribir
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            if (query) {
                debouncedSearch(query);
            } else {
                resultsContainer.classList.remove('active');
            }
        });
        
        // Mostrar todos al enfocar (si está vacío)
        searchInput.addEventListener('focus', () => {
            const query = searchInput.value.trim();
            if (!query) {
                // Cargar todos los clientes al enfocar
                doSearch('');
            } else {
                resultsContainer.classList.add('active');
            }
        });
        
        // Cerrar resultados al hacer clic fuera
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-box')) {
                resultsContainer.classList.remove('active');
            }
        });
    },
    
    async selectCliente(clienteId) {
        try {
            const { data } = await API.getCliente(clienteId);
            this.selectedCliente = data;
            
            const searchInput = document.getElementById('buscar-cliente');
            const clienteSeleccionado = document.getElementById('cliente-seleccionado');
            const resultsContainer = document.getElementById('resultados-busqueda');
            
            if (searchInput) searchInput.style.display = 'none';
            if (resultsContainer) resultsContainer.classList.remove('active');
            
            if (clienteSeleccionado) {
                clienteSeleccionado.innerHTML = `
                    <div class="cliente-item" style="cursor: default; border-color: var(--primary);">
                        <div class="cliente-info">
                            <div class="cliente-avatar">${getInitials(data.nombre)}</div>
                            <div>
                                <div class="cliente-nombre">${escapeHtml(data.nombre)}</div>
                                <div class="cliente-deuda">Deuda actual: ${formatCurrency(data.saldo || 0)}</div>
                            </div>
                        </div>
                        <button type="button" class="btn btn-ghost" onclick="NuevoPrestamo.clearCliente()">✕</button>
                    </div>
                `;
                clienteSeleccionado.style.display = 'block';
            }
            
            // Focus en monto
            document.getElementById('monto')?.focus();
            
        } catch (error) {
            console.error('Error al seleccionar cliente:', error);
            Toast.error('Error al seleccionar cliente: ' + error.message);
        }
    },
    
    clearCliente() {
        this.selectedCliente = null;
        
        const searchInput = document.getElementById('buscar-cliente');
        const clienteSeleccionado = document.getElementById('cliente-seleccionado');
        
        if (searchInput) {
            searchInput.style.display = 'block';
            searchInput.value = '';
            searchInput.focus();
        }
        
        if (clienteSeleccionado) {
            clienteSeleccionado.style.display = 'none';
        }
    }
};

// ==================== PÁGINA: NUEVO ABONO ====================

const NuevoAbono = {
    selectedCliente: null,
    
    async init(clienteId = null) {
        this.setupForm();
        this.setupClienteSearch();
        
        if (clienteId) {
            await this.selectCliente(clienteId);
        }
    },
    
    setupForm() {
        const form = document.getElementById('form-abono');
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!this.selectedCliente) {
                Toast.error('Selecciona un cliente');
                return;
            }
            
            const monto = parseCurrencyInput(document.getElementById('monto').value);
            const descripcion = document.getElementById('descripcion').value;
            
            if (!monto || monto <= 0) {
                Toast.error('Ingresa un monto válido');
                return;
            }
            
            try {
                const btn = lockSubmitButton(form);
                if (!btn) return;
                
                // Guardar saldo anterior
                const saldoAnterior = this.selectedCliente.saldo || 0;
                
                await API.crearMovimiento({
                    cliente_id: this.selectedCliente.id,
                    tipo: 'abono',
                    descripcion: descripcion || 'Abono',
                    monto: monto
                });
                
                const saldoNuevo = saldoAnterior - monto;
                
                Toast.success('Abono registrado exitosamente');
                
                // Mostrar panel de confirmación con WhatsApp
                this.mostrarConfirmacion(monto, descripcion || 'Abono', saldoAnterior, saldoNuevo);
                
            } catch (error) {
                Toast.error(error.message || 'Error al registrar abono');
                const btn = form.querySelector('button[type="submit"]');
                unlockSubmitButton(btn);
                btn.textContent = 'Registrar Abono';
            }
        });
    },
    
    mostrarConfirmacion(monto, descripcion, saldoAnterior, saldoNuevo) {
        const container = document.getElementById('form-container');
        if (!container) return;
        
        const tieneTelefono = tieneTelefonoValido(this.selectedCliente.telefono);
        const deudaPagada = saldoNuevo <= 0;
        
        container.innerHTML = `
            <div class="fade-in" style="text-align: center; padding: 2rem 0;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">${deudaPagada ? '🎉' : '✅'}</div>
                <h3 style="margin-bottom: 0.5rem;">${deudaPagada ? '¡Deuda Saldada!' : '¡Abono Registrado!'}</h3>
                <p class="text-muted" style="margin-bottom: 2rem;">
                    ${formatCurrency(monto)} recibidos de ${escapeHtml(this.selectedCliente.nombre)}
                </p>
                
                <div style="background: var(--bg-main); border-radius: var(--radius-lg); padding: 1.5rem; margin-bottom: 1.5rem;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: left;">
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Saldo anterior</p>
                            <p style="font-weight: 600;">${formatCurrency(saldoAnterior)}</p>
                        </div>
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Saldo actual</p>
                            <p style="font-weight: 700; font-size: 1.25rem; color: ${saldoNuevo > 0 ? 'var(--danger)' : 'var(--success)'};">${formatCurrency(Math.abs(saldoNuevo))}${saldoNuevo <= 0 ? ' (saldado)' : ''}</p>
                        </div>
                    </div>
                </div>
                
                ${tieneTelefono ? `
                    <button onclick="WhatsApp.enviarComprobante('abono', '${this.selectedCliente.id}', '${escapeHtml(this.selectedCliente.nombre)}', '${this.selectedCliente.telefono}', ${monto}, '${escapeHtml(descripcion)}', ${saldoAnterior}, ${saldoNuevo})" 
                            class="btn btn-lg btn-block" 
                            style="background: #25D366; color: white; margin-bottom: 0.5rem;">
                        📱 Enviar comprobante por WhatsApp
                    </button>
                    <button onclick="WhatsApp.generarComprobante('abono', '${escapeHtml(this.selectedCliente.nombre)}', ${monto}, ${saldoNuevo}, '${escapeHtml(descripcion)}')"
                            class="btn btn-lg btn-block"
                            style="background: var(--bg-input); color: var(--text-primary); border: 1px solid var(--border-color); margin-bottom: 1rem;">
                        📸 Descargar comprobante como imagen
                    </button>
                ` : `
                    <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid var(--warning); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1rem;">
                        <p style="font-size: 0.875rem; color: var(--warning);">
                            ⚠️ El cliente no tiene teléfono registrado
                        </p>
                        <button onclick="WhatsApp.generarComprobante('abono', '${escapeHtml(this.selectedCliente.nombre)}', ${monto}, ${saldoNuevo}, '${escapeHtml(descripcion)}')"
                                class="btn btn-block mt-1"
                                style="background: var(--bg-input); color: var(--text-primary); border: 1px solid var(--border-color);">
                            📸 Descargar comprobante como imagen
                        </button>
                    </div>
                `}
                
                <div style="display: flex; gap: 1rem;">
                    <a href="/cliente/${this.selectedCliente.id}" class="btn btn-primary btn-lg" style="flex: 1;">
                        Ver Cliente
                    </a>
                    <a href="/" class="btn btn-secondary btn-lg" style="flex: 1;">
                        Dashboard
                    </a>
                </div>
            </div>
        `;
    },
    
    setupClienteSearch() {
        const searchInput = document.getElementById('buscar-cliente');
        const resultsContainer = document.getElementById('resultados-busqueda');
        if (!searchInput || !resultsContainer) {
            console.error('No se encontraron elementos de búsqueda');
            return;
        }
        
        // Función para realizar la búsqueda
        const doSearch = async (query) => {
            resultsContainer.innerHTML = '<div class="search-result-item"><span class="text-muted">Buscando...</span></div>';
            resultsContainer.classList.add('active');
            
            try {
                const { data } = await API.buscarClientes(query);
                
                if (!data || data.length === 0) {
                    resultsContainer.innerHTML = `
                        <div class="search-result-item" style="justify-content: center;">
                            <span class="text-muted">No se encontraron clientes</span>
                        </div>
                    `;
                } else {
                    resultsContainer.innerHTML = data.map(cliente => `
                        <div class="search-result-item" onclick="NuevoAbono.selectCliente('${cliente.id}')">
                            <div class="cliente-info">
                                <div class="cliente-avatar">${getInitials(cliente.nombre)}</div>
                                <div>
                                    <div class="cliente-nombre">${escapeHtml(cliente.nombre)}</div>
                                    <div class="cliente-deuda">${formatTelefono(cliente.telefono)}</div>
                                </div>
                            </div>
                            <div class="cliente-saldo">${formatCurrency(cliente.saldo || 0)}</div>
                        </div>
                    `).join('');
                }
                
            } catch (error) {
                console.error('Error en búsqueda:', error);
                resultsContainer.innerHTML = `
                    <div class="search-result-item" style="justify-content: center;">
                        <span class="text-danger">Error al buscar: ${escapeHtml(error.message)}</span>
                    </div>
                `;
            }
        };
        
        // Búsqueda con debounce
        const debouncedSearch = debounce(doSearch, CONFIG.DEBOUNCE_DELAY);
        
        // Búsqueda al escribir
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            if (query) {
                debouncedSearch(query);
            } else {
                resultsContainer.classList.remove('active');
            }
        });
        
        // Mostrar todos al enfocar (si está vacío)
        searchInput.addEventListener('focus', () => {
            const query = searchInput.value.trim();
            if (!query) {
                // Cargar todos los clientes al enfocar
                doSearch('');
            } else {
                resultsContainer.classList.add('active');
            }
        });
        
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-box')) {
                resultsContainer.classList.remove('active');
            }
        });
    },
    
    async selectCliente(clienteId) {
        try {
            const { data } = await API.getCliente(clienteId);
            this.selectedCliente = data;
            
            const searchInput = document.getElementById('buscar-cliente');
            const clienteSeleccionado = document.getElementById('cliente-seleccionado');
            const resultsContainer = document.getElementById('resultados-busqueda');
            
            if (searchInput) searchInput.style.display = 'none';
            if (resultsContainer) resultsContainer.classList.remove('active');
            
            if (clienteSeleccionado) {
                clienteSeleccionado.innerHTML = `
                    <div class="cliente-item" style="cursor: default; border-color: var(--success);">
                        <div class="cliente-info">
                            <div class="cliente-avatar">${getInitials(data.nombre)}</div>
                            <div>
                                <div class="cliente-nombre">${escapeHtml(data.nombre)}</div>
                                <div class="cliente-deuda">Deuda actual: ${formatCurrency(data.saldo || 0)}</div>
                            </div>
                        </div>
                        <button type="button" class="btn btn-ghost" onclick="NuevoAbono.clearCliente()">✕</button>
                    </div>
                `;
                clienteSeleccionado.style.display = 'block';
            }
            
            document.getElementById('monto')?.focus();
            
        } catch (error) {
            console.error('Error al seleccionar cliente:', error);
            Toast.error('Error al seleccionar cliente: ' + error.message);
        }
    },
    
    clearCliente() {
        this.selectedCliente = null;
        
        const searchInput = document.getElementById('buscar-cliente');
        const clienteSeleccionado = document.getElementById('cliente-seleccionado');
        
        if (searchInput) {
            searchInput.style.display = 'block';
            searchInput.value = '';
            searchInput.focus();
        }
        
        if (clienteSeleccionado) {
            clienteSeleccionado.style.display = 'none';
        }
    }
};

// ==================== FORMULARIO NUEVO CLIENTE ====================

async function crearNuevoCliente(form) {
    const nombre = form.nombre.value.trim();
    const telefono = form.telefono.value.trim();
    
    if (!nombre) {
        Toast.error('El nombre es requerido');
        return;
    }
    
    try {
        await Clientes.crearCliente({ nombre, telefono });
        form.reset();
    } catch (error) {
        // Error ya manejado en Clientes.crearCliente
    }
}

// ==================== BACKUP ====================

const Backup = {
    async crear() {
        try {
            Toast.show('Creando backup...', 'warning');
            const result = await API.crearBackup();
            Toast.success('Backup creado exitosamente');
            return result;
        } catch (error) {
            Toast.error('Error al crear backup');
            throw error;
        }
    }
};

// ==================== PAGINA: INVENTARIO ====================

const Inventario = {
    productosCache: [],
    filtroActual: 'todos',
    categoriaActual: null,

    async init() {
        this.setupForm();
        this.setupSearch();
        await this.loadStats();
        await this.loadProductos();
        await this.loadVentas();
    },

    async loadStats() {
        const container = document.getElementById('inventario-stats');
        if (!container) return;
        try {
            const { data } = await API.getDashboardInventario();
            container.innerHTML = `
                <div class="stat-card"><div class="stat-label">Productos activos</div><div class="stat-value">${data.productos_activos || 0}</div></div>
                <div class="stat-card"><div class="stat-label">Valor inventario</div><div class="stat-value">${formatCurrency(data.valor_inventario || 0)}</div></div>
                <div class="stat-card"><div class="stat-label">Ventas hoy</div><div class="stat-value">${formatCurrency(data.ventas_hoy || 0)}</div></div>
                <div class="stat-card"><div class="stat-label">Stock bajo</div><div class="stat-value">${(data.stock_bajo || []).length}</div></div>
            `;
        } catch (error) {
            container.innerHTML = '';
        }
    },

    async loadProductos(query = '') {
        const container = document.getElementById('productos-list');
        if (!container) return;
        try {
            const response = query ? await API.buscarProductos(query) : await API.getProductos();
            this.productosCache = response.data || [];
            this.renderCategorias();
            this.renderProductos();
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar inventario</p>`;
        }
    },

    renderCategorias() {
        const container = document.getElementById('categorias-list');
        if (!container) return;
        
        const inputBusqueda = document.getElementById('search-productos');
        const isBuscando = inputBusqueda && inputBusqueda.value.trim() !== '';
        
        if (isBuscando) {
            container.innerHTML = '';
            return;
        }
        
        const categorias = [...new Set(this.productosCache.map(p => (p.categoria || 'Sin categoria').trim()))].filter(Boolean).sort();
        
        if (categorias.length === 0) {
            container.innerHTML = '<span class="text-muted" style="font-size: 0.85rem;">No hay categorías definidas</span>';
            return;
        }

        container.innerHTML = `
            <button class="btn btn-sm ${this.categoriaActual === null ? 'btn-primary' : 'btn-secondary'}" 
                    onclick="Inventario.setCategoria(null)" 
                    style="border-radius: 20px; white-space: nowrap;">
                🌟 Todas
            </button>
            ${categorias.map(cat => `
                <button class="btn btn-sm ${this.categoriaActual === cat ? 'btn-primary' : 'btn-secondary'}" 
                        onclick="Inventario.setCategoria('${escapeHtml(cat)}')" 
                        style="border-radius: 20px; white-space: nowrap;">
                    ${escapeHtml(cat)}
                </button>
            `).join('')}
        `;
    },

    setCategoria(cat) {
        this.categoriaActual = cat;
        this.renderCategorias();
        this.renderProductos();
    },

    renderProductos() {
        const container = document.getElementById('productos-list');
        if (!container) return;
        
        const inputBusqueda = document.getElementById('search-productos');
        const isBuscando = inputBusqueda && inputBusqueda.value.trim() !== '';

        if (this.categoriaActual === null && !isBuscando) {
            container.innerHTML = `
                <div class="empty-state" style="padding: 3rem 1rem;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">📂</div>
                    <div class="empty-state-title">Selecciona una categoría</div>
                    <div class="empty-state-text">Elige una categoría arriba para ver los productos o usa el buscador.</div>
                </div>
            `;
            return;
        }

        let data = this.productosCache;
        
        if (this.categoriaActual !== null && !isBuscando) {
            data = data.filter(p => (p.categoria || 'Sin categoria').trim() === this.categoriaActual);
        }

        if (this.filtroActual === 'bajo_stock') {
            data = data.filter(p => Number(p.stock || 0) <= Number(p.stock_minimo || 0));
        } else if (this.filtroActual === 'sin_stock') {
            data = data.filter(p => Number(p.stock || 0) === 0);
        }
        
        if (data.length === 0) {
            container.innerHTML = `<div class="empty-state"><div class="empty-state-title">No hay productos</div><div class="empty-state-text">Sin resultados para la vista actual</div></div>`;
            return;
        }
        
        container.innerHTML = `
            <div class="clientes-list stagger-in">
                ${data.map(producto => {
                    const stock = Number(producto.stock || 0);
                    const minimo = Number(producto.stock_minimo || 0);
                    const refBadge = producto.referencia ? `<span class="badge" style="background:#475569; margin-left:0.5rem; font-weight:normal;">Ref: ${escapeHtml(producto.referencia)}</span>` : '';
                    return `
                        <div class="cliente-item">
                            <div class="cliente-info" style="flex:1; min-width:0; cursor:pointer;" onclick="Inventario.abrirEditarProducto('${producto.id}')" title="Editar Producto">
                                <div class="cliente-avatar">PR</div>
                                <div style="min-width:0;">
                                    <div class="cliente-nombre" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(producto.nombre)}${refBadge}</div>
                                    <div class="cliente-deuda">${escapeHtml(producto.categoria || 'Sin categoria')} | Stock: ${stock}</div>
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                ${stock <= minimo ? '<span class="badge badge-prestamo">Stock bajo</span>' : ''}
                                <div class="cliente-saldo">${formatCurrency(producto.precio_venta || 0)}</div>
                                <button class="btn btn-secondary btn-sm" onclick="Inventario.abrirEditarProducto('${producto.id}')" title="Editar Producto" style="padding: 0.25rem 0.5rem; border-radius: 4px;">✏️</button>
                                <button class="btn btn-secondary btn-sm" onclick="Inventario.abrirAjusteStock('${producto.id}')" title="Ajustar Stock" style="padding: 0.25rem 0.5rem; font-weight: bold; border-radius: 4px;">+/-</button>
                                <a href="/nueva-venta?producto=${producto.id}" class="btn btn-success btn-sm">Vender</a>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    },

    setFiltro(filtro) {
        this.filtroActual = filtro;
        document.getElementById('filter-todos')?.classList.replace('btn-primary', 'btn-secondary');
        document.getElementById('filter-bajo')?.classList.replace('btn-primary', 'btn-secondary');
        document.getElementById('filter-sin')?.classList.replace('btn-primary', 'btn-secondary');
        
        const map = {'todos': 'filter-todos', 'bajo_stock': 'filter-bajo', 'sin_stock': 'filter-sin'};
        document.getElementById(map[filtro])?.classList.replace('btn-secondary', 'btn-primary');
        
        this.renderProductos();
    },

    async loadVentas() {
        const container = document.getElementById('ventas-list');
        if (!container) return;
        try {
            const { data } = await API.getVentas(20);
            if (!data || data.length === 0) {
                container.innerHTML = `<div class="empty-state"><div class="empty-state-text">Aun no hay ventas registradas</div></div>`;
                return;
            }
            container.innerHTML = `
                <div style="overflow-x: auto;">
                    <table class="historial-table">
                        <thead><tr><th>Fecha</th><th>Producto</th><th>Cantidad</th><th>Total</th><th>Nota</th><th>Acción</th></tr></thead>
                        <tbody>
                            ${data.map(venta => `
                                <tr>
                                    <td>${formatDate(venta.fecha)}</td>
                                    <td>${escapeHtml(venta.producto_nombre || '-')}</td>
                                    <td>${venta.cantidad}</td>
                                    <td>${formatCurrency(venta.total || 0)}</td>
                                    <td>${escapeHtml(venta.nota || '-')}</td>
                                    <td>
                                        <button class="btn btn-sm" style="background:#ef4444; color:white; padding: 0.25rem 0.5rem;" onclick="Inventario.anularVenta('${venta.id}')" title="Anular venta y restaurar stock">Anular</button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-center">Error al cargar ventas</p>`;
        }
    },

    async anularVenta(ventaId) {
        if (!confirm('¿Seguro que deseas anular esta venta? El producto será devuelto al stock.')) return;
        try {
            await API.request(`/ventas/${ventaId}`, { method: 'DELETE' });
            Toast.success('Venta anulada y stock devuelto exitosamente');
            this.loadStats();
            this.loadProductos(document.getElementById('search-productos').value);
            this.loadVentas();
        } catch(error) {
            Toast.error(error.message || 'Error al anular venta');
        }
    },

    abrirAjusteStock(productoId) {
        document.getElementById('ajuste-producto-id').value = productoId;
        document.getElementById('form-ajustar-stock').reset();
        Modal.open('modal-ajustar-stock');
    },

    abrirEditarProducto(productoId) {
        const producto = this.productosCache.find(p => p.id === productoId);
        if (!producto) return;
        
        document.getElementById('editar-producto-id').value = producto.id;
        document.getElementById('editar-producto-nombre').value = producto.nombre || '';
        document.getElementById('editar-producto-categoria').value = producto.categoria || '';
        document.getElementById('editar-producto-referencia').value = producto.referencia || '';
        document.getElementById('editar-producto-compra').value = producto.precio_compra || 0;
        document.getElementById('editar-producto-venta').value = producto.precio_venta || 0;
        document.getElementById('editar-producto-minimo').value = producto.stock_minimo || 0;
        
        // Formatear inputs monetarios si setupCurrencyInputs los afecta
        const event = new Event('input', { bubbles: true });
        document.getElementById('editar-producto-compra').dispatchEvent(event);
        document.getElementById('editar-producto-venta').dispatchEvent(event);
        
        Modal.open('modal-editar-producto');
    },

    setupSearch() {
        const input = document.getElementById('search-productos');
        if (!input) return;
        const search = debounce((query) => this.loadProductos(query), CONFIG.DEBOUNCE_DELAY);
        input.addEventListener('input', (e) => search(e.target.value));
    },

    setupForm() {
        const form = document.getElementById('form-producto');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const data = Object.fromEntries(new FormData(form).entries());
                data.precio_compra = parseCurrencyInput(data.precio_compra);
                data.precio_venta = parseCurrencyInput(data.precio_venta);
                data.stock = Number(data.stock || 0);
                data.stock_minimo = Number(data.stock_minimo || 0);
                try {
                    const btn = lockSubmitButton(form, 'Guardando...');
                    await API.crearProducto(data);
                    unlockSubmitButton(btn);
                    form.reset();
                    Modal.close('modal-nuevo-producto');
                    Toast.success('Producto creado');
                    await this.loadStats();
                    await this.loadProductos(document.getElementById('search-productos').value);
                } catch (error) {
                    const btn = form.querySelector('button[type="submit"]');
                    unlockSubmitButton(btn);
                    Toast.error(error.message || 'Error al guardar producto');
                }
            });
        }
        
        const formAjuste = document.getElementById('form-ajustar-stock');
        if (formAjuste) {
            formAjuste.addEventListener('submit', async (e) => {
                e.preventDefault();
                const prodId = document.getElementById('ajuste-producto-id').value;
                const accion = document.getElementById('accion_ajuste').value;
                const cantidadInput = Number(formAjuste.querySelector('input[name="cantidad"]').value);
                const nota = formAjuste.querySelector('input[name="nota"]').value;
                
                const cantidadCambio = accion === 'sumar' ? cantidadInput : -cantidadInput;
                try {
                    const btn = lockSubmitButton(formAjuste, 'Ajustando...');
                    await API.request(`/productos/${prodId}/ajustar-stock`, {
                        method: 'POST',
                        body: { cantidad_cambio: cantidadCambio, nota: nota }
                    });
                    unlockSubmitButton(btn);
                    Modal.close('modal-ajustar-stock');
                    Toast.success('Stock ajustado exitosamente');
                    this.loadStats();
                    this.loadProductos(document.getElementById('search-productos').value);
                } catch(error) {
                    unlockSubmitButton(formAjuste.querySelector('button[type="submit"]'));
                    Toast.error(error.message || 'Error ajustando stock');
                }
            });
        }
        
        const formEditar = document.getElementById('form-editar-producto');
        if (formEditar) {
            formEditar.addEventListener('submit', async (e) => {
                e.preventDefault();
                const prodId = document.getElementById('editar-producto-id').value;
                const data = Object.fromEntries(new FormData(formEditar).entries());
                
                // Formatear datos
                data.precio_compra = parseCurrencyInput(data.precio_compra);
                data.precio_venta = parseCurrencyInput(data.precio_venta);
                data.stock_minimo = Number(data.stock_minimo || 0);
                
                try {
                    const btn = lockSubmitButton(formEditar, 'Guardando...');
                    await API.request(`/productos/${prodId}`, {
                        method: 'PUT',
                        body: data
                    });
                    unlockSubmitButton(btn);
                    Modal.close('modal-editar-producto');
                    Toast.success('Producto actualizado');
                    this.loadStats();
                    this.loadProductos(document.getElementById('search-productos').value);
                } catch(error) {
                    unlockSubmitButton(formEditar.querySelector('button[type="submit"]'));
                    Toast.error(error.message || 'Error al actualizar producto');
                }
            });
        }
    }
};

const NuevaVenta = {
    selectedProducto: null,

    async init(productoId = null) {
        this.setupSearch();
        this.setupForm();
        this.setupTotal();
        if (productoId) await this.selectProducto(productoId);
    },

    setupSearch() {
        const input = document.getElementById('buscar-producto');
        const results = document.getElementById('resultados-busqueda');
        if (!input || !results) return;
        const doSearch = async (query) => {
            results.innerHTML = '<div class="search-result-item"><span class="text-muted">Buscando...</span></div>';
            results.classList.add('active');
            try {
                const { data } = await API.buscarProductos(query);
                if (!data || data.length === 0) {
                    results.innerHTML = '<div class="search-result-item"><span class="text-muted">Sin productos</span></div>';
                    return;
                }
                results.innerHTML = data.map(producto => `
                    <div class="search-result-item" onclick="NuevaVenta.selectProducto('${producto.id}')">
                        <div class="cliente-info">
                            <div class="cliente-avatar">PR</div>
                            <div><div class="cliente-nombre">${escapeHtml(producto.nombre)}</div><div class="cliente-deuda">Stock: ${producto.stock || 0}</div></div>
                        </div>
                        <div class="cliente-saldo">${formatCurrency(producto.precio_venta || 0)}</div>
                    </div>
                `).join('');
            } catch (error) {
                results.innerHTML = '<div class="search-result-item"><span class="text-danger">Error al buscar</span></div>';
            }
        };
        const debouncedSearch = debounce(doSearch, CONFIG.DEBOUNCE_DELAY);
        input.addEventListener('input', (e) => debouncedSearch(e.target.value.trim()));
        input.addEventListener('focus', () => doSearch(input.value.trim()));
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-box')) results.classList.remove('active');
        });
    },

    setupForm() {
        const form = document.getElementById('form-venta');
        if (!form) return;
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!this.selectedProducto) {
                Toast.error('Selecciona un producto');
                return;
            }
            const cantidad = Number(document.getElementById('cantidad').value || 0);
            const precioInput = document.getElementById('precio-unitario').value;
            const precio = precioInput === '' ? null : parseCurrencyInput(precioInput);
            const nota = document.getElementById('nota').value;
            try {
                const btn = lockSubmitButton(form, 'Registrando...');
                await API.crearVenta({ producto_id: this.selectedProducto.id, cantidad, precio_unitario: precio, nota });
                unlockSubmitButton(btn);
                Toast.success('Venta registrada');
                window.location.href = '/inventario';
            } catch (error) {
                const btn = form.querySelector('button[type="submit"]');
                unlockSubmitButton(btn);
                Toast.error(error.message || 'Error al registrar venta');
            }
        });
    },

    setupTotal() {
        ['cantidad', 'precio-unitario'].forEach(id => {
            document.getElementById(id)?.addEventListener('input', () => this.updateTotal());
        });
    },

    async selectProducto(productoId) {
        try {
            const { data } = await API.getProducto(productoId);
            this.selectedProducto = data;
            document.getElementById('buscar-producto').style.display = 'none';
            document.getElementById('resultados-busqueda').classList.remove('active');
            document.getElementById('precio-unitario').value = data.precio_venta || 0;
            const selected = document.getElementById('producto-seleccionado');
            selected.innerHTML = `
                <div class="cliente-item" style="cursor: default; border-color: var(--primary);">
                    <div class="cliente-info">
                        <div class="cliente-avatar">PR</div>
                        <div><div class="cliente-nombre">${escapeHtml(data.nombre)}</div><div class="cliente-deuda">Stock disponible: ${data.stock || 0}</div></div>
                    </div>
                    <button type="button" class="btn btn-ghost" onclick="NuevaVenta.clearProducto()">x</button>
                </div>
            `;
            selected.style.display = 'block';
            this.updateTotal();
            document.getElementById('cantidad')?.focus();
        } catch (error) {
            Toast.error('Error al seleccionar producto');
        }
    },

    clearProducto() {
        this.selectedProducto = null;
        const input = document.getElementById('buscar-producto');
        input.style.display = 'block';
        input.value = '';
        document.getElementById('producto-seleccionado').style.display = 'none';
        document.getElementById('precio-unitario').value = '';
        this.updateTotal();
    },

    updateTotal() {
        const cantidad = Number(document.getElementById('cantidad')?.value || 0);
        const precioInput = document.getElementById('precio-unitario')?.value;
        const precio = precioInput === '' ? Number(this.selectedProducto?.precio_venta || 0) : parseCurrencyInput(precioInput);
        const totalEl = document.getElementById('venta-total');
        if (totalEl) totalEl.textContent = formatCurrency(cantidad * precio);
    }
};

// ==================== INICIALIZACIÓN GLOBAL ====================

document.addEventListener('DOMContentLoaded', () => {
    // Configurar formateo dinámico de miles en los inputs monetarios
    setupCurrencyInputs();

    // Detectar página actual y ejecutar init correspondiente
    const page = document.body.dataset.page;
    
    switch (page) {
        case 'dashboard':
            Dashboard.init();
            break;
        case 'clientes':
            Clientes.init();
            break;
        case 'cliente-detalle':
            const clienteId = document.body.dataset.clienteId;
            if (clienteId) ClienteDetalle.init(clienteId);
            break;
        case 'nuevo-prestamo':
            const preClienteId = new URLSearchParams(window.location.search).get('cliente');
            NuevoPrestamo.init(preClienteId);
            break;
        case 'nuevo-abono':
            const abonoClienteId = new URLSearchParams(window.location.search).get('cliente');
            NuevoAbono.init(abonoClienteId);
            break;
        case 'proveedores':
            Proveedores.init();
            break;
        case 'proveedor-detalle':
            const proveedorId = document.body.dataset.proveedorId;
            if (proveedorId) ProveedorDetalle.init(proveedorId);
            break;
        case 'nueva-factura':
            const facProveedorId = new URLSearchParams(window.location.search).get('proveedor');
            NuevaFactura.init(facProveedorId);
            break;
        case 'nuevo-pago-proveedor':
            const pagoProveedorId = new URLSearchParams(window.location.search).get('proveedor');
            NuevoPagoProveedor.init(pagoProveedorId);
            break;
        case 'inventario':
            Inventario.init();
            break;
        case 'nueva-venta':
            const ventaProductoId = new URLSearchParams(window.location.search).get('producto');
            NuevaVenta.init(ventaProductoId);
            break;
    }
});

// ==================== WHATSAPP CLICK-TO-CHAT ====================

const WhatsApp = {
    // Tienda info y plantillas - se cargan dinámicamente
    _config: null,
    
    /**
     * Obtiene la configuración completa desde la API
     */
    async getConfig() {
        if (this._config === null) {
            try {
                const response = await fetch('/api/configuracion');
                const result = await response.json();
                this._config = result.data || {};
            } catch (e) {
                console.error('Error cargando configuración para WhatsApp:', e);
                this._config = {};
            }
        }
        return this._config;
    },
    
    async getTienda() {
        const config = await this.getConfig();
        return config.nombre_tienda || 'Tecnosport';
    },
    
    /**
     * Invalida el caché de configuración
     */
    invalidarCache() {
        this._config = null;
    },
    
    /**
     * Formatea número de teléfono para WhatsApp
     */
    formatPhone(phone) {
        if (!phone) return null;
        
        // Limpiar el número
        let cleaned = phone.toString().replace(/[\s\-\(\)\+]/g, '');
        
        // Si empieza con 57, ya está en formato internacional
        if (cleaned.startsWith('57')) {
            return cleaned;
        }
        
        // Si empieza con 3 (Colombia), agregar 57
        if (cleaned.startsWith('3') && cleaned.length === 10) {
            return '57' + cleaned;
        }
        
        // Si tiene 10 dígitos y no empieza con 3, asumir Colombia
        if (cleaned.length === 10) {
            return '57' + cleaned;
        }
        
        return cleaned;
    },
    
    /**
     * Genera el link de WhatsApp
     */
    generateLink(phone, message) {
        const formattedPhone = this.formatPhone(phone);
        if (!formattedPhone) return null;
        
        const encodedMessage = encodeURIComponent(message);
        return `https://wa.me/${formattedPhone}?text=${encodedMessage}`;
    },
    
    /**
     * Abre WhatsApp con el mensaje
     */
    open(phone, message) {
        const link = this.generateLink(phone, message);
        if (!link) {
            Toast.error('El cliente no tiene teléfono registrado');
            return false;
        }
        window.open(link, '_blank');
        return true;
    },

    /**
     * Motor de plantillas: reemplaza variables en el texto
     */
    replaceVariables(text, data) {
        if (!text) return '';
        
        let result = text;
        const variables = {
            '{nombre}': data.nombre || '',
            '{monto}': data.monto ? formatCurrency(data.monto) : '$0',
            '{saldo}': data.saldo ? formatCurrency(data.saldo) : (data.saldoNuevo ? formatCurrency(data.saldoNuevo) : '$0'),
            '{fecha}': data.fecha || new Date().toLocaleDateString('es-CO', {
                weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
            }),
            '{tienda}': data.tienda || 'Negocio',
            '{descripcion}': data.descripcion || ''
        };

        for (const [key, value] of Object.entries(variables)) {
            // Reemplazo global (usando RegExp para que reemplace todas las ocurrencias)
            const regex = new RegExp(key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
            result = result.replace(regex, value);
        }

        return result;
    },
    
    /**
     * Genera mensaje para comprobante de abono
     */
    async mensajeAbono(nombre, monto, saldoAnterior, saldoNuevo) {
        const config = await this.getConfig();
        const tienda = await this.getTienda();
        
        if (config.whatsapp_template_abono) {
            return this.replaceVariables(config.whatsapp_template_abono, {
                nombre, monto, saldo: saldoNuevo, tienda
            });
        }

        const fecha = new Date().toLocaleDateString('es-CO', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
        
        return `Hola ${nombre}, 👋\n\n✅ *ABONO REGISTRADO*\n\n📅 Fecha: ${fecha}\n💰 Abono: ${formatCurrency(monto)}\n📊 Saldo anterior: ${formatCurrency(saldoAnterior)}\n📊 Saldo actual: ${formatCurrency(saldoNuevo)}\n\nGracias por tu pago. 🙏\n\n_${tienda}_`;
    },
    
    /**
     * Genera mensaje para comprobante de préstamo
     */
    async mensajePrestamo(nombre, descripcion, monto, saldoNuevo) {
        const config = await this.getConfig();
        const tienda = await this.getTienda();

        if (config.whatsapp_template_prestamo) {
            return this.replaceVariables(config.whatsapp_template_prestamo, {
                nombre, monto, descripcion, saldo: saldoNuevo, tienda
            });
        }

        const fecha = new Date().toLocaleDateString('es-CO', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
        
        return `Hola ${nombre}, 👋\n\n📤 *PRÉSTAMO REGISTRADO*\n\n📅 Fecha: ${fecha}\n📦 Mercancía: ${descripcion || 'No especificada'}\n💰 Valor: ${formatCurrency(monto)}\n📊 Saldo actual: ${formatCurrency(saldoNuevo)}\n\nRecuerda que puedes hacer abonos parciales. 😉\n\n_${tienda}_`;
    },
    
    /**
     * Genera mensaje para recordatorio de deuda
     */
    async mensajeRecordatorio(nombre, saldo, diasSinAbono) {
        const config = await this.getConfig();
        const tienda = await this.getTienda();

        if (config.whatsapp_template_recordatorio) {
            return this.replaceVariables(config.whatsapp_template_recordatorio, {
                nombre, saldo, tienda, 
                descripcion: diasSinAbono ? `Han pasado ${diasSinAbono} días desde tu último abono.` : ''
            });
        }

        return `Hola ${nombre}, 👋\n\nTe escribimos de *${tienda}* para recordarte que tienes un saldo pendiente de ${formatCurrency(saldo)}.\n\n${diasSinAbono ? `Han pasado ${diasSinAbono} días desde tu último abono.` : ''}\n\nSi deseas hacer un abono o tienes alguna pregunta, no dudes en respondernos. 🙏\n\n¡Gracias por tu preferencia!`;
    },
    
    /**
     * Envía recordatorio de deuda por WhatsApp
     */
    async enviarRecordatorio(telefono, nombre, saldo, diasSinAbono) {
        const mensaje = await this.mensajeRecordatorio(nombre, saldo, diasSinAbono);
        const enviado = this.open(telefono, mensaje);
        if (enviado) {
            Toast.success('Abriendo WhatsApp...');
        }
    },
    
    /**
     * Envía comprobante por WhatsApp
     */
    async enviarComprobante(tipo, clienteId, nombre, telefono, monto, descripcion, saldoAnterior, saldoNuevo) {
        let mensaje;
        
        if (tipo === 'abono') {
            mensaje = await this.mensajeAbono(nombre, monto, saldoAnterior, saldoNuevo);
        } else {
            mensaje = await this.mensajePrestamo(nombre, descripcion, monto, saldoNuevo);
        }
        
        const enviado = this.open(telefono, mensaje);
        
        if (enviado) {
            Toast.success('Abriendo WhatsApp...');
            this.trackEnvio(1);
        }
    },

    /**
     * Guarda estadísticas de mensajes enviados en localStorage
     */
    trackEnvio(cantidad = 1) {
        const hoy = new Date().toDateString();
        const guardado = localStorage.getItem('wa_fecha_hoy');
        let acum = parseInt(localStorage.getItem('wa_enviados_hoy') || '0');
        if (guardado !== hoy) acum = 0;
        acum += cantidad;
        localStorage.setItem('wa_enviados_hoy', acum);
        localStorage.setItem('wa_fecha_hoy', hoy);
        let total = parseInt(localStorage.getItem('wa_total_enviados') || '0');
        total += cantidad;
        localStorage.setItem('wa_total_enviados', total);
        localStorage.setItem('wa_ultimo_envio', new Date().toISOString());
    },

    /**
     * Genera un comprobante visual como imagen PNG y lo descarga.
     * Parámetros: tipo ('abono'|'prestamo'), nombre, monto, saldoNuevo, descripcion
     */
    async generarComprobante(tipo, nombre, monto, saldoNuevo, descripcion) {
        const config = await this.getConfig();
        const tienda = await this.getTienda();
        const fecha = new Date().toLocaleDateString('es-CO', {
            weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
        });

        const fmt = (v) => new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP', maximumFractionDigits: 0
        }).format(v);

        // Verificar si mostramos el código QR de pago
        const mostrarQR = config.qr_pago_activo && (config.qr_pago_nequi || config.qr_pago_davi || config.qr_pago_bancolombia);

        const W = 480;
        const H = mostrarQR ? 430 : 320;
        
        const canvas = document.createElement('canvas');
        canvas.width = W * 2;   // Resolución doble para nitidez
        canvas.height = H * 2;
        const ctx = canvas.getContext('2d');
        ctx.scale(2, 2);

        // Fondo
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(0, 0, W, H);

        // Barra superior de color
        const isAbono = tipo === 'abono';
        const accentColor = isAbono ? '#25d366' : '#6366f1';
        ctx.fillStyle = accentColor;
        ctx.fillRect(0, 0, W, 6);

        // Ícono y tipo
        ctx.fillStyle = isAbono ? 'rgba(37,211,102,0.12)' : 'rgba(99,102,241,0.12)';
        ctx.beginPath();
        ctx.arc(W / 2, 54, 30, 0, Math.PI * 2);
        ctx.fill();

        ctx.font = 'bold 22px Arial';
        ctx.fillStyle = accentColor;
        ctx.textAlign = 'center';
        ctx.fillText(isAbono ? '✓' : '↑', W / 2, 62);

        // Título
        ctx.font = 'bold 15px Arial';
        ctx.fillStyle = '#f8fafc';
        ctx.fillText(isAbono ? 'ABONO REGISTRADO' : 'PRÉSTAMO REGISTRADO', W / 2, 100);

        // Nombre y tienda
        ctx.font = '13px Arial';
        ctx.fillStyle = '#94a3b8';
        ctx.fillText(nombre + ' · ' + tienda, W / 2, 120);

        // Tarjeta central
        ctx.fillStyle = '#1e293b';
        roundRect(ctx, 24, 134, W - 48, 110, 12);
        ctx.fill();

        // Monto
        ctx.font = 'bold 28px Arial';
        ctx.fillStyle = accentColor;
        ctx.textAlign = 'center';
        ctx.fillText(fmt(monto), W / 2, 170);

        // Labels
        ctx.font = '11px Arial';
        ctx.fillStyle = '#64748b';
        ctx.textAlign = 'left';
        ctx.fillText(isAbono ? 'Abono recibido' : 'Valor del préstamo', 40, 195);
        ctx.textAlign = 'right';
        ctx.fillText('Saldo actual', W - 40, 195);

        ctx.font = 'bold 13px Arial';
        ctx.fillStyle = '#cbd5e1';
        ctx.textAlign = 'left';
        ctx.fillText(fmt(monto), 40, 213);
        ctx.textAlign = 'right';
        ctx.fillStyle = saldoNuevo > 0 ? '#ef4444' : '#25d366';
        ctx.fillText(fmt(saldoNuevo), W - 40, 213);

        // Descripción si existe
        if (descripcion) {
            ctx.font = '11px Arial';
            ctx.fillStyle = '#64748b';
            ctx.textAlign = 'center';
            const desc = descripcion.length > 50 ? descripcion.substring(0, 47) + '...' : descripcion;
            ctx.fillText(desc, W / 2, 233);
        }

        // Renderizar sección de código QR si está activo
        if (mostrarQR) {
            // Línea divisora punteada
            ctx.strokeStyle = '#334155';
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(24, 262);
            ctx.lineTo(W - 24, 262);
            ctx.stroke();
            ctx.setLineDash([]); // Reset dash

            // Crear valor de código QR estructurado para escaneo rápido
            let qrLines = [];
            qrLines.push(`** PAGO EN LINEA - ${tienda.toUpperCase()} **`);
            if (config.qr_pago_nequi) qrLines.push(`Nequi: ${config.qr_pago_nequi}`);
            if (config.qr_pago_davi) qrLines.push(`Daviplata: ${config.qr_pago_davi}`);
            if (config.qr_pago_bancolombia) qrLines.push(`Bancolombia: ${config.qr_pago_bancolombia}`);
            qrLines.push(`Valor sugerido: ${fmt(monto)}`);
            const qrValue = qrLines.join('\n');

            // Dibujar contenedor blanco del QR
            ctx.fillStyle = '#ffffff';
            roundRect(ctx, 36, 280, 106, 106, 10);
            ctx.fill();

            // Dibujar QRious de forma asíncrona
            try {
                if (typeof QRious !== 'undefined') {
                    const qr = new QRious({
                        value: qrValue,
                        size: 200,
                        level: 'H'
                    });
                    
                    const qrImg = new Image();
                    qrImg.src = qr.toDataURL();
                    await new Promise((resolve, reject) => {
                        qrImg.onload = resolve;
                        qrImg.onerror = reject;
                    });
                    
                    ctx.drawImage(qrImg, 40, 284, 98, 98);
                } else {
                    console.error('Librería QRious no está disponible.');
                    ctx.fillStyle = '#1e293b';
                    ctx.fillRect(40, 284, 98, 98);
                    ctx.font = '10px Arial';
                    ctx.fillStyle = '#94a3b8';
                    ctx.textAlign = 'center';
                    ctx.fillText('Error QR', 89, 333);
                }
            } catch (err) {
                console.error('Error dibujando código QR en canvas:', err);
            }

            // Datos de texto al lado derecho del QR
            ctx.font = 'bold 11px Arial';
            ctx.fillStyle = accentColor;
            ctx.textAlign = 'left';
            ctx.fillText('TRANSFERIR A:', 164, 292);

            ctx.font = '12px Arial';
            let textY = 312;
            if (config.qr_pago_nequi) {
                ctx.fillStyle = '#64748b';
                ctx.fillText('• Nequi:', 164, textY);
                ctx.fillStyle = '#f8fafc';
                ctx.font = 'bold 12px Arial';
                ctx.fillText(config.qr_pago_nequi, 224, textY);
                ctx.font = '12px Arial';
                textY += 20;
            }
            if (config.qr_pago_davi) {
                ctx.fillStyle = '#64748b';
                ctx.fillText('• Daviplata:', 164, textY);
                ctx.fillStyle = '#f8fafc';
                ctx.font = 'bold 12px Arial';
                ctx.fillText(config.qr_pago_davi, 240, textY);
                ctx.font = '12px Arial';
                textY += 20;
            }
            if (config.qr_pago_bancolombia) {
                ctx.fillStyle = '#64748b';
                ctx.fillText('• Bancolombia:', 164, textY);
                ctx.fillStyle = '#f8fafc';
                ctx.font = 'bold 12px Arial';
                ctx.fillText(config.qr_pago_bancolombia, 260, textY);
                ctx.font = '12px Arial';
                textY += 20;
            }

            ctx.font = 'italic 10px Arial';
            ctx.fillStyle = '#64748b';
            ctx.fillText('Escanea el QR para copiar datos rápidamente.', 164, 382);
        }

        // Fecha (posicionada en la parte inferior)
        ctx.font = '10px Arial';
        ctx.fillStyle = '#475569';
        ctx.textAlign = 'center';
        ctx.fillText(fecha, W / 2, H - 15);

        // Descargar
        const link = document.createElement('a');
        link.download = `comprobante_${tipo}_${nombre.replace(/\s+/g,'_')}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();

        Toast.success('📸 Comprobante descargado');
    }
};

// Helper para canvas: rectángulo con bordes redondeados
function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
}

// Exportar funciones globales necesarias
window.Modal = Modal;
window.Toast = Toast;
window.Dashboard = Dashboard;
window.Clientes = Clientes;
window.ClienteDetalle = ClienteDetalle;
window.NuevoPrestamo = NuevoPrestamo;
window.NuevoAbono = NuevoAbono;
window.Backup = Backup;
window.WhatsApp = WhatsApp;
window.crearNuevoCliente = crearNuevoCliente;

// ==================== PÁGINA: PROVEEDORES ====================

const Proveedores = {
    async init() {
        await this.loadProveedores();
        this.setupSearch();
    },
    
    async loadProveedores() {
        const container = document.getElementById('proveedores-list');
        if (!container) return;
        
        container.innerHTML = Array(5).fill(Skeleton.clienteItem()).join('');
        
        try {
            const { data } = await API.getProveedores();
            
            if (data.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">🏭</div>
                        <div class="empty-state-title">No hay proveedores</div>
                        <div class="empty-state-text">Agrega tu primer proveedor para comenzar</div>
                        <button class="btn btn-primary mt-2" onclick="Modal.open('modal-nuevo-proveedor')">
                            + Nuevo Proveedor
                        </button>
                    </div>
                `;
                return;
            }
            
            // Ordenar por saldo descendente
            data.sort((a, b) => (b.saldo || 0) - (a.saldo || 0));
            
            container.innerHTML = `
                <div class="clientes-list stagger-in">
                    ${data.map(proveedor => `
                        <div class="cliente-item">
                            <a href="/proveedor/${proveedor.id}" style="display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; color: inherit; text-decoration: none;">
                                <div class="cliente-avatar" style="background: #ea580c;">${getInitials(proveedor.nombre)}</div>
                                <div style="min-width: 0;">
                                    <div class="cliente-nombre">${escapeHtml(proveedor.nombre)}</div>
                                    <div class="cliente-deuda">${formatTelefono(proveedor.telefono)}</div>
                                </div>
                            </a>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <div class="cliente-saldo">${formatCurrency(proveedor.saldo)}</div>
                                ${proveedor.telefono ? `
                                    <button class="btn-whatsapp-small" onclick="event.preventDefault(); event.stopPropagation(); WhatsApp.open('${proveedor.telefono}', 'Hola ${escapeHtml(proveedor.nombre)},')" title="Enviar WhatsApp">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `
                <div class="empty-state">
                    <p class="text-danger">Error al cargar proveedores</p>
                    <button class="btn btn-secondary mt-1" onclick="Proveedores.loadProveedores()">Reintentar</button>
                </div>
            `;
        }
    },
    
    setupSearch() {
        const searchInput = document.getElementById('search-proveedores');
        if (!searchInput) return;
        
        const debouncedSearch = debounce(async (query) => {
            const container = document.getElementById('proveedores-list');
            
            if (!query.trim()) {
                this.loadProveedores();
                return;
            }
            
            try {
                const { data } = await API.buscarProveedores(query);
                
                if (data.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">🔍</div>
                            <div class="empty-state-title">Sin resultados</div>
                            <div class="empty-state-text">No se encontraron proveedores con "${escapeHtml(query)}"</div>
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = `
                    <div class="clientes-list stagger-in">
                        ${data.map(proveedor => `
                            <a href="/proveedor/${proveedor.id}" class="cliente-item">
                                <div class="cliente-info">
                                    <div class="cliente-avatar" style="background: #ea580c;">${getInitials(proveedor.nombre)}</div>
                                    <div>
                                        <div class="cliente-nombre">${escapeHtml(proveedor.nombre)}</div>
                                        <div class="cliente-deuda">${formatTelefono(proveedor.telefono)}</div>
                                    </div>
                                </div>
                                <div class="cliente-saldo">${formatCurrency(proveedor.saldo)}</div>
                            </a>
                        `).join('')}
                    </div>
                `;
            } catch (error) {
                Toast.error('Error en la búsqueda');
            }
        }, CONFIG.DEBOUNCE_DELAY);
        
        searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value));
    },
    
    async crearProveedor(formData) {
        try {
            const result = await API.crearProveedor(formData);
            Toast.success('Proveedor creado exitosamente');
            Modal.closeAll();
            this.loadProveedores();
            return result;
        } catch (error) {
            Toast.error(error.message || 'Error al crear proveedor');
            throw error;
        }
    }
};

// ==================== PÁGINA: DETALLE PROVEEDOR ====================

const ProveedorDetalle = {
    proveedorId: null,
    
    async init(proveedorId) {
        this.proveedorId = proveedorId;
        await this.loadData();
    },
    
    async loadData() {
        const container = document.getElementById('proveedor-content');
        if (!container) return;
        
        Loading.show(container, 'Cargando información del proveedor...');
        
        try {
            const { data } = await API.getHistorialProveedor(this.proveedorId);
            const { proveedor, resumen, movimientos } = data;
            
            const saldoClass = resumen.saldo > 0 ? 'negative' : (resumen.saldo < 0 ? 'positive' : 'zero');
            
            container.innerHTML = `
                <div class="fade-in">
                    <!-- Header del proveedor -->
                    <div style="text-align: center; margin-bottom: 2rem;">
                        <div class="avatar-lg" style="background: #ea580c;">${getInitials(proveedor.nombre)}</div>
                        <h1 style="margin: 1rem 0 0.5rem;">${escapeHtml(proveedor.nombre)}</h1>
                        <p class="text-muted">${formatTelefono(proveedor.telefono)}</p>
                    </div>
                    
                    <!-- Saldo grande -->
                    <div class="saldo-grande">
                        <div class="saldo-label">Deuda con Proveedor</div>
                        <div class="saldo-valor ${saldoClass}">${formatCurrency(Math.abs(resumen.saldo))}</div>
                    </div>
                    
                    <!-- Stats del proveedor -->
                    <div class="stats-grid" style="margin-bottom: 2rem;">
                        <div class="stat-card">
                            <div class="stat-label">Total Facturas</div>
                            <div class="stat-value">${formatCurrency(resumen.total_facturas)}</div>
                        </div>
                        <div class="stat-card success">
                            <div class="stat-label">Total Pagado</div>
                            <div class="stat-value text-success">${formatCurrency(resumen.total_pagado)}</div>
                        </div>
                    </div>
                    
                    <!-- Acciones -->
                    <div style="display: flex; gap: 1rem; margin-bottom: 2rem;">
                        <a href="/nueva-factura?proveedor=${proveedor.id}" class="btn btn-lg btn-block" style="background: #ea580c; color: white;">
                            📄 Registrar Factura
                        </a>
                        <a href="/nuevo-pago-proveedor?proveedor=${proveedor.id}" class="btn btn-success btn-lg btn-block">
                            💸 Registrar Pago
                        </a>
                    </div>
                    
                    <!-- Historial -->
                    <div class="section">
                        <div class="section-header">
                            <h3 class="section-title">
                                <span class="section-title-icon">📋</span>
                                Historial de Movimientos
                            </h3>
                        </div>
                        
                        ${movimientos.length === 0 ? `
                            <div class="empty-state">
                                <div class="empty-state-icon">📝</div>
                                <div class="empty-state-title">Sin movimientos</div>
                                <div class="empty-state-text">Los movimientos aparecerán aquí</div>
                            </div>
                        ` : `
                            <div style="overflow-x: auto;">
                                <table class="historial-table">
                                    <thead>
                                        <tr>
                                            <th>Fecha</th>
                                            <th>Tipo</th>
                                            <th>Descripción</th>
                                            <th>Monto</th>
                                            <th>Saldo</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${movimientos.map(mov => `
                                            <tr>
                                                <td>${formatDate(mov.fecha)}</td>
                                                <td><span class="badge" style="background: ${mov.tipo === 'factura' ? '#ea580c' : '#059669'}; color: white;">${mov.tipo}</span></td>
                                                <td>${escapeHtml(mov.descripcion || '-')}</td>
                                                <td class="${mov.tipo === 'factura' ? 'text-danger' : 'text-success'}">
                                                    ${mov.tipo === 'factura' ? '+' : '-'}${formatCurrency(mov.monto)}
                                                </td>
                                                <td>${formatCurrency(mov.saldo_acumulado)}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        `}
                    </div>
                </div>
            `;
            
        } catch (error) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">❌</div>
                    <div class="empty-state-title">Error</div>
                    <div class="empty-state-text">${escapeHtml(error.message)}</div>
                    <a href="/" class="btn btn-primary mt-2">Volver al inicio</a>
                </div>
            `;
        }
    }
};

// ==================== PÁGINA: NUEVA FACTURA ====================

const NuevaFactura = {
    selectedProveedor: null,
    
    async init(proveedorId = null) {
        this.setupForm();
        this.setupProveedorSearch();
        
        if (proveedorId) {
            await this.selectProveedor(proveedorId);
        }
    },
    
    setupForm() {
        const form = document.getElementById('form-factura');
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!this.selectedProveedor) {
                Toast.error('Selecciona un proveedor');
                return;
            }
            
            const monto = parseCurrencyInput(document.getElementById('monto').value);
            const descripcion = document.getElementById('descripcion').value;
            const fecha = document.getElementById('fecha').value;
            
            if (!monto || monto <= 0) {
                Toast.error('Ingresa un monto válido');
                return;
            }
            
            try {
                const btn = lockSubmitButton(form);
                if (!btn) return;
                
                const saldoAnterior = this.selectedProveedor.saldo || 0;
                
                await API.crearMovimientoProveedor({
                    proveedor_id: this.selectedProveedor.id,
                    tipo: 'factura',
                    descripcion: descripcion || 'Factura de proveedor',
                    monto: monto,
                    fecha: fecha || null
                });
                
                const saldoNuevo = saldoAnterior + monto;
                
                Toast.success('Factura registrada exitosamente');
                this.mostrarConfirmacion(monto, descripcion || 'Factura de proveedor', saldoAnterior, saldoNuevo);
                
            } catch (error) {
                Toast.error(error.message || 'Error al registrar factura');
                const btn = form.querySelector('button[type="submit"]');
                unlockSubmitButton(btn);
                btn.textContent = '📄 Registrar Factura';
            }
        });
    },
    
    mostrarConfirmacion(monto, descripcion, saldoAnterior, saldoNuevo) {
        const container = document.getElementById('form-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="fade-in" style="text-align: center; padding: 2rem 0;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">✅</div>
                <h3 style="margin-bottom: 0.5rem;">¡Factura Registrada!</h3>
                <p class="text-muted" style="margin-bottom: 2rem;">
                    ${formatCurrency(monto)} agregados a la deuda con ${escapeHtml(this.selectedProveedor.nombre)}
                </p>
                
                <div style="background: var(--bg-main); border-radius: var(--radius-lg); padding: 1.5rem; margin-bottom: 1.5rem;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: left;">
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Concepto</p>
                            <p style="font-weight: 600;">${escapeHtml(descripcion)}</p>
                        </div>
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Deuda actual</p>
                            <p style="font-weight: 700; font-size: 1.25rem; color: #ea580c;">${formatCurrency(saldoNuevo)}</p>
                        </div>
                    </div>
                </div>
                
                <div style="display: flex; gap: 1rem;">
                    <a href="/proveedor/${this.selectedProveedor.id}" class="btn btn-primary btn-lg" style="flex: 1;">
                        Ver Proveedor
                    </a>
                    <a href="/" class="btn btn-secondary btn-lg" style="flex: 1;">
                        Dashboard
                    </a>
                </div>
            </div>
        `;
    },
    
    setupProveedorSearch() {
        const searchInput = document.getElementById('buscar-proveedor');
        const resultsContainer = document.getElementById('resultados-busqueda');
        if (!searchInput || !resultsContainer) return;
        
        const debouncedSearch = debounce(async (query) => {
            if (!query.trim()) {
                resultsContainer.classList.remove('active');
                return;
            }
            
            try {
                const { data } = await API.buscarProveedores(query);
                
                if (data.length === 0) {
                    resultsContainer.innerHTML = `<div class="search-result-empty">No se encontraron proveedores</div>`;
                } else {
                    resultsContainer.innerHTML = data.map(proveedor => `
                        <div class="search-result-item" onclick="NuevaFactura.selectProveedor('${proveedor.id}', '${escapeHtml(proveedor.nombre)}', ${proveedor.saldo || 0})">
                            <div class="search-result-name">${escapeHtml(proveedor.nombre)}</div>
                            <div class="search-result-info">${formatTelefono(proveedor.telefono)} • Deuda: ${formatCurrency(proveedor.saldo || 0)}</div>
                        </div>
                    `).join('');
                }
                
                resultsContainer.classList.add('active');
                
            } catch (error) {
                console.error('Error buscando proveedores:', error);
            }
        }, CONFIG.DEBOUNCE_DELAY);
        
        searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value));
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim()) {
                resultsContainer.classList.add('active');
            }
        });
    },
    
    async selectProveedor(proveedorId, nombre, saldo) {
        if (nombre === undefined) {
            try {
                const { data } = await API.getProveedor(proveedorId);
                nombre = data.nombre;
                saldo = data.saldo || 0;
            } catch (error) {
                Toast.error("Error al cargar proveedor");
                return;
            }
        }
        this.selectedProveedor = { id: proveedorId, nombre: nombre, saldo: saldo };
        
        const container = document.getElementById('proveedor-seleccionado');
        const searchInput = document.getElementById('buscar-proveedor');
        const resultsContainer = document.getElementById('resultados-busqueda');
        
        if (container) {
            container.innerHTML = `
                <div class="proveedor-selected">
                    <div class="proveedor-selected-avatar" style="background: #ea580c;">${getInitials(nombre)}</div>
                    <div class="proveedor-selected-info">
                        <div class="proveedor-selected-name">${escapeHtml(nombre)}</div>
                        <div class="proveedor-selected-saldo">Deuda actual: ${formatCurrency(saldo)}</div>
                    </div>
                    <button type="button" class="btn btn-sm btn-secondary" onclick="NuevaFactura.clearProveedor()">Cambiar</button>
                </div>
            `;
            container.style.display = 'block';
        }
        
        if (searchInput) searchInput.style.display = 'none';
        if (resultsContainer) resultsContainer.classList.remove('active');
    },
    
    clearProveedor() {
        this.selectedProveedor = null;
        
        const container = document.getElementById('proveedor-seleccionado');
        const searchInput = document.getElementById('buscar-proveedor');
        
        if (container) container.style.display = 'none';
        if (searchInput) {
            searchInput.style.display = 'block';
            searchInput.value = '';
            searchInput.focus();
        }
    }
};

// ==================== PÁGINA: NUEVO PAGO PROVEEDOR ====================

const NuevoPagoProveedor = {
    selectedProveedor: null,
    
    async init(proveedorId = null) {
        this.setupForm();
        this.setupProveedorSearch();
        
        if (proveedorId) {
            await this.selectProveedor(proveedorId);
        }
    },
    
    setupForm() {
        const form = document.getElementById('form-pago-proveedor');
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!this.selectedProveedor) {
                Toast.error('Selecciona un proveedor');
                return;
            }
            
            const monto = parseCurrencyInput(document.getElementById('monto').value);
            const descripcion = document.getElementById('descripcion').value;
            const fecha = document.getElementById('fecha').value;
            
            if (!monto || monto <= 0) {
                Toast.error('Ingresa un monto válido');
                return;
            }
            
            try {
                const btn = lockSubmitButton(form);
                if (!btn) return;
                
                const saldoAnterior = this.selectedProveedor.saldo || 0;
                
                await API.crearMovimientoProveedor({
                    proveedor_id: this.selectedProveedor.id,
                    tipo: 'pago',
                    descripcion: descripcion || 'Pago a proveedor',
                    monto: monto,
                    fecha: fecha || null
                });
                
                const saldoNuevo = saldoAnterior - monto;
                
                Toast.success('Pago registrado exitosamente');
                this.mostrarConfirmacion(monto, descripcion || 'Pago a proveedor', saldoAnterior, saldoNuevo);
                
            } catch (error) {
                Toast.error(error.message || 'Error al registrar pago');
                const btn = form.querySelector('button[type="submit"]');
                unlockSubmitButton(btn);
                btn.textContent = '💸 Registrar Pago';
            }
        });
    },
    
    mostrarConfirmacion(monto, descripcion, saldoAnterior, saldoNuevo) {
        const container = document.getElementById('form-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="fade-in" style="text-align: center; padding: 2rem 0;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">✅</div>
                <h3 style="margin-bottom: 0.5rem;">¡Pago Registrado!</h3>
                <p class="text-muted" style="margin-bottom: 2rem;">
                    ${formatCurrency(monto)} pagados a ${escapeHtml(this.selectedProveedor.nombre)}
                </p>
                
                <div style="background: var(--bg-main); border-radius: var(--radius-lg); padding: 1.5rem; margin-bottom: 1.5rem;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: left;">
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Concepto</p>
                            <p style="font-weight: 600;">${escapeHtml(descripcion)}</p>
                        </div>
                        <div>
                            <p class="text-muted" style="font-size: 0.875rem; margin-bottom: 0.25rem;">Deuda restante</p>
                            <p style="font-weight: 700; font-size: 1.25rem; color: ${saldoNuevo > 0 ? '#ea580c' : '#059669'};">${formatCurrency(saldoNuevo)}</p>
                        </div>
                    </div>
                </div>
                
                <div style="display: flex; gap: 1rem;">
                    <a href="/proveedor/${this.selectedProveedor.id}" class="btn btn-primary btn-lg" style="flex: 1;">
                        Ver Proveedor
                    </a>
                    <a href="/" class="btn btn-secondary btn-lg" style="flex: 1;">
                        Dashboard
                    </a>
                </div>
            </div>
        `;
    },
    
    setupProveedorSearch() {
        const searchInput = document.getElementById('buscar-proveedor');
        const resultsContainer = document.getElementById('resultados-busqueda');
        if (!searchInput || !resultsContainer) return;
        
        const debouncedSearch = debounce(async (query) => {
            if (!query.trim()) {
                resultsContainer.classList.remove('active');
                return;
            }
            
            try {
                const { data } = await API.buscarProveedores(query);
                
                if (data.length === 0) {
                    resultsContainer.innerHTML = `<div class="search-result-empty">No se encontraron proveedores</div>`;
                } else {
                    resultsContainer.innerHTML = data.map(proveedor => `
                        <div class="search-result-item" onclick="NuevoPagoProveedor.selectProveedor('${proveedor.id}', '${escapeHtml(proveedor.nombre)}', ${proveedor.saldo || 0})">
                            <div class="search-result-name">${escapeHtml(proveedor.nombre)}</div>
                            <div class="search-result-info">${formatTelefono(proveedor.telefono)} • Deuda: ${formatCurrency(proveedor.saldo || 0)}</div>
                        </div>
                    `).join('');
                }
                
                resultsContainer.classList.add('active');
                
            } catch (error) {
                console.error('Error buscando proveedores:', error);
            }
        }, CONFIG.DEBOUNCE_DELAY);
        
        searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value));
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim()) {
                resultsContainer.classList.add('active');
            }
        });
    },
    
    async selectProveedor(proveedorId, nombre, saldo) {
        if (nombre === undefined) {
            try {
                const { data } = await API.getProveedor(proveedorId);
                nombre = data.nombre;
                saldo = data.saldo || 0;
            } catch (error) {
                Toast.error("Error al cargar proveedor");
                return;
            }
        }
        this.selectedProveedor = { id: proveedorId, nombre: nombre, saldo: saldo };
        
        const container = document.getElementById('proveedor-seleccionado');
        const searchInput = document.getElementById('buscar-proveedor');
        const resultsContainer = document.getElementById('resultados-busqueda');
        
        if (container) {
            container.innerHTML = `
                <div class="proveedor-selected">
                    <div class="proveedor-selected-avatar" style="background: #ea580c;">${getInitials(nombre)}</div>
                    <div class="proveedor-selected-info">
                        <div class="proveedor-selected-name">${escapeHtml(nombre)}</div>
                        <div class="proveedor-selected-saldo">Deuda actual: ${formatCurrency(saldo)}</div>
                    </div>
                    <button type="button" class="btn btn-sm btn-secondary" onclick="NuevoPagoProveedor.clearProveedor()">Cambiar</button>
                </div>
            `;
            container.style.display = 'block';
        }
        
        if (searchInput) searchInput.style.display = 'none';
        if (resultsContainer) resultsContainer.classList.remove('active');
    },
    
    clearProveedor() {
        this.selectedProveedor = null;
        
        const container = document.getElementById('proveedor-seleccionado');
        const searchInput = document.getElementById('buscar-proveedor');
        
        if (container) container.style.display = 'none';
        if (searchInput) {
            searchInput.style.display = 'block';
            searchInput.value = '';
            searchInput.focus();
        }
    }
};

// Función global para crear nuevo proveedor
function crearNuevoProveedor(form) {
    const formData = {
        nombre: form.nombre.value,
        telefono: form.telefono.value || ''
    };
    Proveedores.crearProveedor(formData);
}

// Exportar funciones globales de proveedores
window.Proveedores = Proveedores;
window.ProveedorDetalle = ProveedorDetalle;
window.NuevaFactura = NuevaFactura;
window.NuevoPagoProveedor = NuevoPagoProveedor;
window.crearNuevoProveedor = crearNuevoProveedor;

// ==================== APP SWITCHER (ODOO-STYLE) ====================

const AppSwitcher = {
    overlay: null,
    toggleBtn: null,
    closeBtn: null,
    searchInput: null,
    isOpen: false,

    init() {
        this.overlay   = document.getElementById('app-switcher-overlay');
        this.toggleBtn = document.getElementById('app-switcher-toggle');
        this.closeBtn  = document.getElementById('app-switcher-close');
        this.searchInput = document.getElementById('app-switcher-search-input');

        if (!this.overlay || !this.toggleBtn) return;

        // Abrir / cerrar al hacer clic en el botón de 9 puntos
        this.toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.isOpen ? this.close() : this.open();
        });

        // Botón "×" interno
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.close());
        }

        // Cerrar al hacer clic fuera del overlay (en el fondo)
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) this.close();
        });

        // Tecla Escape cierra el overlay
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });

        // Filtro de búsqueda dentro del overlay
        if (this.searchInput) {
            this.searchInput.addEventListener('input', (e) => {
                this.filterApps(e.target.value.toLowerCase().trim());
            });
        }

        // Resaltar la app activa según la URL actual
        this.highlightActiveApp();
    },

    open() {
        if (!this.overlay) return;
        this.overlay.classList.add('active');
        this.isOpen = true;
        document.body.style.overflow = 'hidden';

        // Enfocar el campo de búsqueda del overlay automáticamente
        setTimeout(() => {
            if (this.searchInput) {
                this.searchInput.value = '';
                this.filterApps('');
                this.searchInput.focus();
            }
        }, 150);

        // Animar el botón de 9 puntos
        if (this.toggleBtn) {
            this.toggleBtn.classList.add('active');
        }
    },

    close() {
        if (!this.overlay) return;
        this.overlay.classList.remove('active');
        this.isOpen = false;
        document.body.style.overflow = '';

        if (this.toggleBtn) {
            this.toggleBtn.classList.remove('active');
        }
    },

    filterApps(query) {
        const cards = this.overlay ? this.overlay.querySelectorAll('.odoo-card') : [];
        cards.forEach(card => {
            const label = (card.querySelector('.odoo-label')?.textContent || '').toLowerCase();
            const match = !query || label.includes(query);
            card.style.display = match ? '' : 'none';
            card.style.opacity = match ? '1' : '0';
        });
    },

    highlightActiveApp() {
        const currentPath = window.location.pathname;
        const cards = document.querySelectorAll('#app-switcher-overlay .odoo-card');
        cards.forEach(card => {
            const href = card.getAttribute('href');
            if (href && (href === currentPath || (href !== '/' && currentPath.startsWith(href)))) {
                card.classList.add('active-app');
            }
        });
    }
};

// ==================== GLOBAL SEARCH (BUSCADOR CRUZADO) ====================

const GlobalSearch = {
    input: null,
    resultsPanel: null,
    isLoading: false,
    currentQuery: '',

    init() {
        this.input = document.getElementById('global-search');
        this.resultsPanel = document.getElementById('global-search-results');

        if (!this.input || !this.resultsPanel) return;

        // Shortcut Ctrl+K / Cmd+K para enfocar el buscador
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.input.focus();
                this.input.select();
            }
            // Esc cierra resultados si el buscador está enfocado
            if (e.key === 'Escape' && document.activeElement === this.input) {
                this.hideResults();
                this.input.blur();
            }
        });

        // Búsqueda con debounce mientras el usuario escribe
        const debouncedSearch = debounce((query) => this.search(query), CONFIG.DEBOUNCE_DELAY);

        this.input.addEventListener('input', (e) => {
            const q = e.target.value.trim();
            this.currentQuery = q;
            if (!q) {
                this.hideResults();
                return;
            }
            this.showSkeleton();
            debouncedSearch(q);
        });

        // Mostrar resultados previos al re-enfocar si hay texto
        this.input.addEventListener('focus', () => {
            if (this.currentQuery) {
                this.resultsPanel.classList.add('visible');
            }
        });

        // Ocultar panel al hacer clic fuera
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.global-search-container')) {
                this.hideResults();
            }
        });

        // Navegación con teclado (↑ ↓ Enter)
        this.input.addEventListener('keydown', (e) => this.handleKeyboard(e));
    },

    async search(query) {
        if (!query) return;
        this.isLoading = true;

        try {
            // Búsqueda paralela en clientes y productos
            const [clientesRes, productosRes] = await Promise.allSettled([
                API.buscarClientes(query),
                API.buscarProductos(query)
            ]);

            const clientes  = clientesRes.status  === 'fulfilled' ? (clientesRes.value?.data  || []) : [];
            const productos = productosRes.status === 'fulfilled' ? (productosRes.value?.data || []) : [];

            this.renderResults(query, clientes, productos);
        } catch (err) {
            console.error('GlobalSearch error:', err);
            this.showError();
        } finally {
            this.isLoading = false;
        }
    },

    renderResults(query, clientes, productos) {
        if (!this.resultsPanel) return;

        const totalResults = clientes.length + productos.length;

        if (totalResults === 0) {
            this.resultsPanel.innerHTML = `
                <div class="gs-empty">
                    <div class="gs-empty-icon">🔍</div>
                    <div class="gs-empty-text">No se encontraron resultados para "<strong>${escapeHtml(query)}</strong>"</div>
                    <div class="gs-empty-hint">Prueba con otro nombre o término</div>
                </div>
            `;
            this.resultsPanel.classList.add('visible');
            return;
        }

        let html = '';

        // ---- Sección Clientes ----
        if (clientes.length > 0) {
            html += `<div class="gs-section-header">👥 Clientes (${clientes.length})</div>`;
            html += clientes.slice(0, 5).map(c => {
                const tieneDeuda = c.saldo > 0;
                return `
                    <a href="/cliente/${c.id}" class="gs-result-item gs-result-cliente" data-id="${c.id}">
                        <div class="gs-result-avatar gs-avatar-crm">${getInitials(c.nombre)}</div>
                        <div class="gs-result-info">
                            <div class="gs-result-name">${this.highlight(escapeHtml(c.nombre), query)}</div>
                            <div class="gs-result-meta">${formatTelefono(c.telefono)}</div>
                        </div>
                        <div class="gs-result-badge ${tieneDeuda ? 'gs-badge-danger' : 'gs-badge-success'}">
                            ${tieneDeuda ? formatCurrency(c.saldo) : '✓ Al día'}
                        </div>
                    </a>
                `;
            }).join('');

            if (clientes.length > 5) {
                html += `<a href="/clientes?q=${encodeURIComponent(query)}" class="gs-see-more">Ver los ${clientes.length} clientes encontrados →</a>`;
            }
        }

        // ---- Sección Productos ----
        if (productos.length > 0) {
            html += `<div class="gs-section-header">📦 Productos / Inventario (${productos.length})</div>`;
            html += productos.slice(0, 5).map(p => {
                const stockOk = (p.stock || 0) > 0;
                return `
                    <a href="/inventario?q=${encodeURIComponent(p.nombre)}" class="gs-result-item gs-result-producto" data-id="${p.id}">
                        <div class="gs-result-avatar gs-avatar-inventory">📦</div>
                        <div class="gs-result-info">
                            <div class="gs-result-name">${this.highlight(escapeHtml(p.nombre), query)}</div>
                            <div class="gs-result-meta">${p.categoria || 'Sin categoría'} · PV: ${formatCurrency(p.precio_venta || 0)}</div>
                        </div>
                        <div class="gs-result-badge ${stockOk ? 'gs-badge-success' : 'gs-badge-warning'}">
                            ${stockOk ? `Stock: ${p.stock}` : 'Sin stock'}
                        </div>
                    </a>
                `;
            }).join('');

            if (productos.length > 5) {
                html += `<a href="/inventario?q=${encodeURIComponent(query)}" class="gs-see-more">Ver los ${productos.length} productos encontrados →</a>`;
            }
        }

        // Pie del panel: acceso rápido a módulos
        html += `
            <div class="gs-footer">
                <span class="gs-footer-label">Ir a módulo:</span>
                <a href="/clientes" class="gs-footer-link">👥 CRM</a>
                <a href="/inventario" class="gs-footer-link">📦 Inventario</a>
                <a href="/proveedores" class="gs-footer-link">🏭 Compras</a>
                <a href="/gastos" class="gs-footer-link">💸 Gastos</a>
            </div>
        `;

        this.resultsPanel.innerHTML = html;
        this.resultsPanel.classList.add('visible');
    },

    showSkeleton() {
        if (!this.resultsPanel) return;
        this.resultsPanel.innerHTML = `
            <div class="gs-skeleton-wrap">
                <div class="gs-section-header skeleton" style="width: 120px; height: 14px; border-radius: 6px;"></div>
                ${[1,2,3].map(() => `
                    <div class="gs-result-item" style="pointer-events:none; gap: 0.75rem;">
                        <div class="skeleton" style="width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;"></div>
                        <div style="flex:1;">
                            <div class="skeleton" style="width: 55%; height: 14px; border-radius: 4px; margin-bottom: 6px;"></div>
                            <div class="skeleton" style="width: 35%; height: 11px; border-radius: 4px;"></div>
                        </div>
                        <div class="skeleton" style="width: 65px; height: 22px; border-radius: 10px;"></div>
                    </div>
                `).join('')}
            </div>
        `;
        this.resultsPanel.classList.add('visible');
    },

    showError() {
        if (!this.resultsPanel) return;
        this.resultsPanel.innerHTML = `
            <div class="gs-empty">
                <div class="gs-empty-icon">⚠️</div>
                <div class="gs-empty-text">Error al realizar la búsqueda</div>
                <div class="gs-empty-hint">Comprueba tu conexión e intenta de nuevo</div>
            </div>
        `;
        this.resultsPanel.classList.add('visible');
    },

    hideResults() {
        if (this.resultsPanel) {
            this.resultsPanel.classList.remove('visible');
        }
    },

    /**
     * Resalta la coincidencia del query dentro de un texto HTML
     */
    highlight(text, query) {
        if (!query) return text;
        try {
            const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`(${escaped})`, 'gi');
            return text.replace(regex, '<mark class="gs-highlight">$1</mark>');
        } catch {
            return text;
        }
    },

    /**
     * Navegación por teclado dentro del panel de resultados
     */
    handleKeyboard(e) {
        const items = this.resultsPanel
            ? Array.from(this.resultsPanel.querySelectorAll('.gs-result-item'))
            : [];
        if (!items.length) return;

        const focused = this.resultsPanel.querySelector('.gs-result-item.focused');
        let idx = focused ? items.indexOf(focused) : -1;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (focused) focused.classList.remove('focused');
            idx = (idx + 1) % items.length;
            items[idx].classList.add('focused');
            items[idx].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (focused) focused.classList.remove('focused');
            idx = (idx - 1 + items.length) % items.length;
            items[idx].classList.add('focused');
            items[idx].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'Enter') {
            if (focused) {
                e.preventDefault();
                window.location.href = focused.getAttribute('href');
            }
        }
    }
};

// ==================== INICIALIZACIÓN GLOBAL ====================

document.addEventListener('DOMContentLoaded', () => {
    AppSwitcher.init();
    GlobalSearch.init();
});

// Exportar módulos globales de UI
window.AppSwitcher = AppSwitcher;
window.GlobalSearch = GlobalSearch;
