# Demo Barber Club — Plataforma Web Integral para Barberías de Lujo

![Open Graph](/static/img/og/og-image.webp)

Plataforma web comercial completa para barberías y salones masculinos de alta gama. Desarrollada para sorprender a dueños de negocios en presentaciones comerciales, con funcionamiento en tiempo real, arquitectura modular, diseño editorial oscuro minimalista y facilidad de personalización para cada cliente.

---

## 🌟 Características Principales

### 1. Sitio Web Público de Lujo (Inspirado en viggomhc.cl)
- **Estética Editorial Oscura**: Paleta refinada en negro carbón (`#0A0A0A`), superficies (`#141414`), acento dorado satinado (`#C9A24B`) y textos en marfil cálido (`#F5F0E6`).
- **Hero a Pantalla Completa**: Video de fondo en bucle o imagen con parallax, tipografía de gran escala con acento cursivo serif, botones CTA primarios con brillo animado (*shimmer*) e indicador de scroll.
- **Micro-interacciones y Animaciones**:
  * Preloader con animación de tijeras y fade out suave.
  * Barra de progreso de lectura en el borde superior.
  * Cinta continua en movimiento (*marquee*) con especialidades.
  * Contadores numéricos animados (años, clientes, cortes, barberos).
  * Efecto de inclinación 3D leve (*tilt*) y elevación en tarjetas.
  * Acordeón de preguntas frecuentes con animación fluida.
  * Modal lightbox para visualización de la galería.
  * Carrusel de testimonios de clientes con autoplay y pausa.
  * Respeto a accesibilidad y `prefers-reduced-motion`.
- **Botones Flotantes de Contacto Directo**:
  * **WhatsApp** (`#25D366`) con animación de pulso, tooltip y mensaje prellenado codificado.
  * **Instagram** con degradado oficial y enlace al perfil.
  * Ocultables dinámicamente si el campo está vacío en el dashboard.

### 2. Motor de Reservas Inteligente (Sin Recarga de Página)
- **Flujo en 6 Pasos con Barra de Progreso**:
  1. Selección de Sucursal (Providencia, Las Condes, Vitacura).
  2. Selección de Servicio (duración, precio CLP, categoría).
  3. Selección de Master Barber o "Cualquier barbero disponible".
  4. Selector de Fecha y Horarios disponibles calculados dinámicamente.
  5. Datos de contacto del cliente (con login automático o reserva express como invitado).
  6. Voucher de resumen y confirmación atómica.
- **Algoritmo de Disponibilidad en Tiempo Real**:
  * Resta citas existentes, descansos configurables (ej. 10 min) y pausas de colación.
  * Comprueba turnos y bloqueos de agenda en **todas** las sucursales donde atiende el barbero (imposibilita el solapamiento de horarios entre diferentes sedes).
  * Asignación inteligente: si se elige "Cualquier barbero", asigna automáticamente al profesional con menor carga del día.
  * **Prevención de colisiones**: Transacciones atómicas (`transaction.atomic`) y bloqueo a nivel de base de datos (`select_for_update`).
  * Notificación en pantalla y correo de confirmación con botón **"Agregar a Google Calendar"** y enlace directo a WhatsApp.

### 3. Cuentas de Usuario y Jerarquía de Administración
- Modelo personalizado con correo electrónico como identificador único.
- **Cuatro roles con alcance validado en el servidor**:
  * **ADMIN_MAESTRO**: Control total de la plataforma. Dispone de un selector global de sucursal en el encabezado del panel ("Todas las sedes" o una sede específica) que filtra KPIs, gráficos, listados y reportes. Es el único que puede crear/editar sucursales, crear administradores de sede y asignarles sedes, editar la configuración global del sitio y gestionar el catálogo base.
  * **ADMIN_SUCURSAL**: Administrador local con una o más sedes asignadas (`sucursales_asignadas`). Solo puede ver y gestionar reservas, agenda, barberos asignados, stock, pedidos y ventas de SUS sucursales. La restricción está protegida en backend con `AlcanceSucursalMixin` y `validar_pertenencia_objeto` (retorna HTTP 403 ante cualquier intento de acceso directo por URL).
  * **BARBERO**: Redirección directa tras el inicio de sesión a su agenda interactiva (`/panel/agenda/`). Acceso exclusivo a sus citas y horarios.
  * **CLIENTE**: Historial de citas, notas y pedidos en `/mi-cuenta/`.
- Protección contra ataques de fuerza bruta en el login y recuperación de clave por correo.

### 4. Tienda Online e Inventario Multi-Sucursal
- Catálogo de productos de grooming masculino (pomadas, aceites, champús, ceras, perfumes) con SKU, precios y costo para cálculo de márgenes.
- **Stock por Sucursal (`StockSucursal`)**: Cada producto mantiene existencias independientes en cada sede física.
- **Auditoría Inmutable (`MovimientoStock`)**: Todo cambio en el stock se realiza a través de movimientos transaccionales (`transaction.atomic`) y bloqueo pesimista (`select_for_update`), imposibilitando saldos negativos:
  * `ENTRADA`: Compra o reposición directa por sede.
  * `SALIDA`: Merma, daño o uso interno en la barbería.
  * `AJUSTE`: Inventario físico periódico.
  * `VENTA`: Descuento automático al confirmar pedidos en tienda para retiro local.
  * `DEVOLUCION`: Restitución inmediata del stock si un pedido es cancelado desde el panel.
  * `TRASLADO`: Movimiento entre dos sedes que conserva con exactitud el total global del producto.
- Panel de inventario con filtros por estado (`OK`, `BAJO`, `AGOTADO`), buscador, alertas en dashboard, contador en el menú lateral y exportación completa a CSV.

### 5. Agenda de Barberos: Horarios Multi-Tramo y Bloqueos
- **Horarios Semanales Flexibles**:
  * Configuración por día (Lunes a Domingo) con múltiples tramos horarios (ej. 10:00–14:00 y 15:00–20:00), definiendo la colación de forma natural entre tramos.
  * Botones rápidos para "Agregar tramo", "Copiar Lunes a toda la semana" y "Copiar horario a otro barbero".
  * Validaciones en el servidor: `hora_inicio < hora_fin`, prevención de solapamientos internos y detección de colisiones entre sucursales diferentes para el mismo profesional.
  * Detección preventiva de reservas futuras afectadas con solicitud de confirmación antes de aplicar cambios.
- **Bloqueos de Intervalos y Recurrentes**:
  * Bloqueo manual por barbero o para toda la sucursal, por rango de horas o día completo, con motivo (capacitación, vacaciones, permiso, feriado) y recurrencia semanal opcional.
  * Sincronización inmediata con el motor público: las horas bloqueadas desaparecen al instante del agendamiento del cliente y de la opción "Cualquier barbero".

### 6. Dashboard de Administración Propio (`/panel/`)
- **KPIs Comerciales con Selector Global**: Ingresos, reservas, ocupación, ticket promedio y alertas de stock bajo según la sede activa o consolidado.
- **Comparativo de Sucursales (Exclusivo ADMIN_MAESTRO)**: Tabla comparativa de rendimiento entre sedes con ingresos, citas, horas atendidas, ticket promedio y productos críticos.
- **Gráficos Interactivos con Chart.js**: Ingresos diarios, reservas por sede, servicios más solicitados y rendimiento por barbero.
- **Control de Citas y Pedidos**: Tablas con cambio de estado rápido, trazabilidad de stock y exportación a CSV con UTF-8 BOM.

---

## 📸 Capturas de Pantalla

| Portada Editorial | Flujo de Reserva en 6 Pasos |
| :---: | :---: |
| ![Portada](docs/screenshots/portada_desktop.webp) | ![Reserva](docs/screenshots/flujo_reserva.webp) |

| Dashboard Comercial (Chart.js) | Agenda Personal del Barbero |
| :---: | :---: |
| ![Dashboard](docs/screenshots/dashboard_kpis.webp) | ![Agenda](docs/screenshots/agenda_barbero.webp) |

---

## 🛠 Stack Tecnológico

- **Backend**: Django 5.x / 6.x (Python 3.12+)
- **Base de Datos**: SQLite (desarrollo local) / PostgreSQL (preparado para producción con variables en `.env`)
- **Estilos**: Tailwind CSS 3.4 (Tailwind CLI nativo con `tailwind.config.js`)
- **Interactividad**: JavaScript Vanilla (ES6+, modular, sin dependencias pesadas)
- **Visualización de Datos**: Chart.js 4.x
- **Gestión Multimedia**: Pillow (WebP, Favicons, Open Graph) y Python-Dotenv

---

## 📦 Requisitos Previos

- Python 3.10 o superior.
- Node.js 18+ y npm (para compilación de estilos Tailwind).
- Git.

---

## 🚀 Instalación y Puesta en Marcha

### 1. Clonar el Repositorio
```bash
git clone https://github.com/tu-usuario/demo-barber.git
cd demo-barber
```

### 2. Activar Entorno Virtual de Python
En Windows:
```powershell
.\env\Scripts\activate
```
En Linux / macOS:
```bash
source env/bin/activate
```

### 3. Instalar Dependencias de Python
```bash
pip install -r requirements.txt
```

### 4. Instalar Dependencias de Node (Tailwind CLI)
```bash
npm install
```

### 5. Configurar Variables de Entorno
Copia el archivo de ejemplo y revisa las variables:
```bash
cp .env.example .env
```

### 6. Ejecutar Migraciones
```bash
python manage.py migrate
```

### 7. Cargar Datos de Demostración
Puebla la base de datos de forma idempotente con sucursales, administradores de sede, barberos, horarios multi-tramo, bloqueos, stock por sede y movimientos históricos:
```bash
python manage.py cargar_demo
```

### 8. Compilar Estilos CSS
Para compilar una vez (modo producción minificado):
```bash
npm run build
```
Para desarrollo continuo con auto-recarga de estilos:
```bash
npm run dev
```

### 9. Iniciar el Servidor de Desarrollo
```bash
python manage.py runserver
```

Abre tu navegador en: **`http://127.0.0.1:8000/`**

---

## 👥 Cuentas de Acceso de Demostración

| Rol | Correo Electrónico | Contraseña | Alcance / Permisos | Destino Post Login |
| :--- | :--- | :--- | :--- | :--- |
| **ADMIN_MAESTRO** | `admin@demobarberclub.cl` | `admin123` | Control total, selector global, configuración y catálogo base | `/panel/` |
| **ADMIN_SUCURSAL** | `admin.providencia@demobarberclub.cl` | `admin123` | Exclusivo Sede Providencia (agenda, barberos, stock, pedidos) | `/panel/` |
| **ADMIN_SUCURSAL** | `admin.lascondes@demobarberclub.cl` | `admin123` | Exclusivo Sede Las Condes (agenda, barberos, stock, pedidos) | `/panel/` |
| **ADMIN_SUCURSAL** | `admin.vitacura@demobarberclub.cl` | `admin123` | Exclusivo Sede Vitacura (agenda, barberos, stock, pedidos) | `/panel/` |
| **BARBERO** | `barbero@demobarberclub.cl` | `barbero123` | Su propia agenda y registro de atenciones | `/panel/agenda/` |
| **CLIENTE** | `cliente@demobarberclub.cl` | `cliente123` | Historial de citas, pedidos y perfil personal | `/mi-cuenta/` |

---

## 📁 Estructura del Proyecto

```text
demo-barber/
├── barberos/             # Perfiles de barberos y asignación de sucursales
├── catalogo/             # Servicios, precios base, categorías y template tags
├── contenido/            # ConfiguracionSitio, testimonios, FAQ, galería, blog y comando cargar_demo
├── cuentas/              # Usuario personalizado, roles, login, registro y decoradores
├── demo_barber/          # Configuración Django, settings, urls maestras, wsgi y asgi
├── docs/                 # Documentación técnica y capturas de pantalla
├── panel/                # Dashboard administrativo, KPIs, gráficos Chart.js y reportes
├── reservas/             # Motor de disponibilidad, bloqueos, turnos y flujo en pasos
├── static/               # Assets compilados (CSS, imágenes de demo WebP, logos SVG, favicon)
│   ├── css/              # input.css y output.css compilado
│   ├── img/              # Fotos de servicios, barberos, sucursales, productos y galería
│   └── video/            # Video de fondo para el hero
├── templates/            # Plantillas HTML en Django con diseño editorial
│   ├── cuentas/          # Login, registro, perfil, recuperación
│   ├── panel/            # Dashboard, agenda barbero, reservas, ventas, configuración
│   ├── reservas/         # Agendamiento por pasos, voucher de confirmación
│   ├── sitio/            # Inicio, landing por sucursal, blog y contacto
│   └── tienda/           # Catálogo, producto detalle, carrito y checkout
├── tienda/               # Productos, inventario, pedidos, pasarelas de pago
├── manage.py
├── package.json          # Scripts de Tailwind CSS
├── requirements.txt      # Dependencias fijadas de Python
├── tailwind.config.js    # Tokens de diseño y colores
└── .env.example          # Plantilla de variables de entorno
```

---

## 🎨 Cómo Personalizar para una Nueva Barbería

Toda la plataforma ha sido concebida para adaptarse a cualquier cliente en minutos:

1. **Desde el Panel de Control (`/panel/configuracion/`)**:
   - Cambia el **Nombre del Negocio**, eslogan y descripción.
   - Actualiza el **Número de WhatsApp** (con código de país) y el usuario de **Instagram**. Si se vacía un campo, el botón flotante correspondiente se oculta automáticamente.
   - Edita los **Textos del Hero** (antetítulo, titular grande, texto en cursiva y llamados a la acción).
   - Ajusta las **Políticas de Reserva**: horas mínimas para agendar, tiempo límite de cancelación sin costo, días máximos a futuro y descanso entre citas.
   - Activa o desactiva el **Banner Superior de Promociones**.
2. **Colores y Tipografía**:
   - Variables centralizadas en `tailwind.config.js` y `static/css/input.css`:
     * Fondo principal: `#0A0A0A`
     * Acento dorado de conversión: `#C9A24B` (hover `#DDB968`)
     * Superficies: `#141414` / `#1C1C1C`
     * Texto marfil: `#F5F0E6`
3. **Logotipo e Imágenes**:
   - Reemplaza el archivo vectorial en `static/img/logo/logo.svg`.
   - Carga las fotos de tus propios barberos, servicios y productos desde sus respectivas secciones en el Dashboard (`/panel/barberos/`, `/panel/servicios/`, etc.).

---

## 🧪 Pruebas Automáticas (Testing)

El sistema incluye una suite integral de 14 pruebas automáticas que verifican exhaustivamente:
1. **Alcance y Seguridad por Sede**: `ADMIN_SUCURSAL` no puede ver ni editar datos de otra sucursal (retorna HTTP 403 en acceso directo por URL a barberos, agenda y pedidos, y querysets estrictamente filtrados).
2. **Selector Global del ADMIN_MAESTRO**: Vista consolidada y filtrado dinámico en KPIs, gráficos y listados al seleccionar una sede o "Todas".
3. **Validación de Tramos Horarios**: `hora_inicio < hora_fin`, prevención de solapamientos el mismo día y detección de colisiones entre sucursales para el mismo barbero.
4. **Bloqueos de Intervalo**: Eliminación exacta e inmediata de los horarios bloqueados del motor público de reservas.
5. **Seguridad de Stock y Auditoría**: Imposibilidad de saldo negativo, conservación exacta del stock total en traslados inter-sucursales y restitución automática de stock (`DEVOLUCION`) al cancelar pedidos.
6. **Control de Acceso por Roles**: Usuarios con rol `CLIENTE` y `BARBERO` reciben HTTP 403 Forbidden al intentar ingresar a módulos de administración.
7. **Disponibilidad y Concurrencia**: Prevención de doble reserva simultánea con bloqueos a nivel de base de datos.

Ejecutar la suite completa de pruebas:
```bash
python manage.py test
```

---

## 🚀 Despliegue en Producción

1. Configurar variables en `.env`:
   - `DEBUG=False`
   - `SECRET_KEY=clave-secreta-robusta-de-produccion`
   - `ALLOWED_HOSTS=tudominio.cl,www.tudominio.cl`
   - Configuración de base de datos PostgreSQL (`DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`).
   - Configuración SMTP para envío real de correos de confirmación.
2. Compilar assets estáticos:
   ```bash
   npm run build
   python manage.py collectstatic --noinput
   ```
3. Servidor de aplicaciones recomendado: **Gunicorn** o **Uvicorn** detrás de un proxy inverso **Nginx** con certificado SSL Let's Encrypt.

---

## 🗺 Hoja de Ruta (Próximas Mejoras)

- [ ] Integración de pasarela de pago Webpay Plus (Transbank) y Flow mediante la clase `PasarelaPagoInterface`.
- [ ] Envío automático de recordatorios por WhatsApp Business API y SMS 2 horas antes de la cita.
- [ ] Sistema de puntos y fidelización por visitas acumuladas.
- [ ] Selección de música ambiental por sucursal conectada a Spotify API.

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.
