"""
Módulo de control de alcance y filtrado por sucursales para el panel de administración.
Garantiza que ADMIN_SUCURSAL solo acceda a datos de sus sucursales asignadas en el servidor,
mientras que ADMIN_MAESTRO puede alternar entre 'Todas' o una sede específica.
"""
from django.core.exceptions import PermissionDenied
from sucursales.models import Sucursal


def obtener_sucursales_permitidas(usuario):
    """
    Retorna el QuerySet de sucursales a las que tiene acceso administrativo el usuario.
    - ADMIN_MAESTRO / superuser: Todas las sucursales activas.
    - ADMIN_SUCURSAL: Solo las sucursales asignadas en su perfil.
    - Otros roles: QuerySet vacío.
    """
    if not usuario or not usuario.is_authenticated:
        return Sucursal.objects.none()

    if usuario.es_admin_maestro:
        return Sucursal.objects.filter(activa=True).order_by('orden', 'nombre')

    if usuario.es_admin_sucursal:
        return usuario.sucursales_asignadas.filter(activa=True).order_by('orden', 'nombre')

    return Sucursal.objects.none()


def obtener_sucursal_activa_id(request):
    """
    Determina la sucursal activa en la sesión o querystring del panel:
    - Para ADMIN_MAESTRO: Permite None (Todas las sedes / consolidado) o el ID de una sede específica.
    - Para ADMIN_SUCURSAL: Forzado siempre a estar dentro de sus sucursales permitidas.
    """
    usuario = request.user
    if not usuario.is_authenticated or not usuario.es_administrador:
        return None

    sucursales_permitidas = obtener_sucursales_permitidas(usuario)
    permitidas_ids = list(sucursales_permitidas.values_list('id', flat=True))

    if not permitidas_ids:
        return None

    # 1. Comprobar parámetro GET explícito
    param = request.GET.get('sucursal') or request.GET.get('sucursal_global')
    if param is not None:
        param = str(param).strip()
        if usuario.es_admin_maestro and (param == '' or param.lower() == 'all' or param == '0'):
            request.session['panel_sucursal_id'] = None
            return None
        try:
            suc_id = int(param)
            if suc_id in permitidas_ids:
                request.session['panel_sucursal_id'] = suc_id
                return suc_id
            elif not usuario.es_admin_maestro:
                raise PermissionDenied("No tienes acceso a la sucursal solicitada.")
        except ValueError:
            pass

    # 2. Comprobar sesión existente
    sesion_id = request.session.get('panel_sucursal_id')
    if sesion_id is not None:
        if sesion_id in permitidas_ids:
            return sesion_id
        elif usuario.es_admin_maestro:
            # Si la sucursal de la sesión ya no existe o no está activa
            request.session['panel_sucursal_id'] = None
            return None

    # 3. Para ADMIN_SUCURSAL con asignaciones, si no hay selección válida, tomar la primera
    if usuario.es_admin_sucursal and permitidas_ids:
        request.session['panel_sucursal_id'] = permitidas_ids[0]
        return permitidas_ids[0]

    return None


def validar_acceso_sucursal(usuario, sucursal_o_id):
    """
    Valida en el servidor que el usuario tenga permiso para ver, editar o borrar
    un registro perteneciente a una sucursal específica.
    Lanza PermissionDenied (HTTP 403) si no está autorizado.
    """
    if not usuario or not usuario.is_authenticated:
        raise PermissionDenied("Se requiere autenticación.")

    if usuario.es_admin_maestro:
        return True

    if not usuario.es_admin_sucursal:
        raise PermissionDenied("No posees permisos de administración.")

    sucursal_id = sucursal_o_id.id if hasattr(sucursal_o_id, 'id') else int(sucursal_o_id)
    sucursales_permitidas_ids = usuario.sucursales_asignadas.values_list('id', flat=True)

    if sucursal_id not in sucursales_permitidas_ids:
        raise PermissionDenied("Acceso denegado: este registro pertenece a una sede fuera de tu alcance administrativo.")

    return True


def aplicar_alcance_queryset(queryset, request, campo_sucursal='sucursal'):
    """
    Filtra un QuerySet aplicando las restricciones de sede del usuario y la sede activa:
    - Si ADMIN_SUCURSAL: Limita estrictamente a sus sedes asignadas.
    - Si se ha seleccionado una sede específica en el panel, filtra por esa sede.
    """
    usuario = request.user
    if not usuario.is_authenticated or not usuario.es_administrador:
        return queryset.none()

    sucursales_permitidas = obtener_sucursales_permitidas(usuario)
    if not sucursales_permitidas.exists():
        return queryset.none()

    # Si es ADMIN_SUCURSAL, siempre restringir al conjunto de sus sedes
    if usuario.es_admin_sucursal:
        filtro_base = {f"{campo_sucursal}__in": sucursales_permitidas}
        queryset = queryset.filter(**filtro_base)

    # Si hay una sede activa seleccionada en el panel, filtrar por esa específica
    sucursal_activa_id = obtener_sucursal_activa_id(request)
    if sucursal_activa_id:
        try:
            field = queryset.model._meta.get_field(campo_sucursal)
            if field.many_to_many or field.one_to_many:
                filtro_activa = {f"{campo_sucursal}__id": sucursal_activa_id}
            else:
                filtro_activa = {f"{campo_sucursal}_id": sucursal_activa_id}
        except Exception:
            filtro_activa = {f"{campo_sucursal}_id": sucursal_activa_id}
        queryset = queryset.filter(**filtro_activa)

    return queryset


def validar_pertenencia_objeto(usuario, objeto, campo_sucursal='sucursal'):
    """
    Valida que el objeto pertenezca a una sucursal permitida para el usuario; si no, lanza 403.
    Soporta relaciones directas (ForeignKey) y ManyToMany (ej. Barberos).
    """
    if not usuario or not usuario.is_authenticated:
        raise PermissionDenied("Se requiere autenticación.")

    if usuario.es_admin_maestro:
        return True

    if not usuario.es_admin_sucursal:
        raise PermissionDenied("No posees permisos de administración.")

    permitidas = usuario.sucursales_asignadas.all()
    permitidas_ids = set(permitidas.values_list('id', flat=True))

    # Caso 1: Atributo directo de sucursal (ej: reserva.sucursal, stock.sucursal)
    sucursal = getattr(objeto, campo_sucursal, None)
    if sucursal is not None:
        sucursal_id = sucursal.id if hasattr(sucursal, 'id') else sucursal
        if sucursal_id not in permitidas_ids:
            raise PermissionDenied("Acceso denegado: este registro pertenece a una sede fuera de tu alcance administrativo.")
        return True

    # Caso 2: Objeto con relación ManyToMany con sucursales (ej. Barbero)
    if hasattr(objeto, 'sucursales'):
        obj_sucursales_ids = set(objeto.sucursales.values_list('id', flat=True))
        if not obj_sucursales_ids.intersection(permitidas_ids):
            raise PermissionDenied("Acceso denegado: este profesional no está asignado a ninguna de tus sedes.")
        return True

    return True


class AlcanceSucursalMixin:
    """
    Mixin para vistas basadas en clases que filtra automáticamente QuerySets
    y valida pertenencia de objetos por sucursal.
    """
    campo_sucursal = 'sucursal'

    def get_queryset(self):
        qs = super().get_queryset()
        return aplicar_alcance_queryset(qs, self.request, self.campo_sucursal)

    def check_object_permissions(self, request, obj):
        if hasattr(super(), 'check_object_permissions'):
            super().check_object_permissions(request, obj)
        validar_pertenencia_objeto(request.user, obj, self.campo_sucursal)
