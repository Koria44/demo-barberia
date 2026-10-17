"""
Módulo de pasarelas de pago para Demo Barber Club.
Define una interfaz desacoplada para facilitar la integración de Webpay Plus, Flow,
Mercado Pago o pagos locales.
"""
from abc import ABC, abstractmethod


class PasarelaPagoInterface(ABC):
    """
    Clase abstracta que define el contrato obligatorio para cualquier
    procesador de pagos que se conecte a la plataforma.
    """

    @abstractmethod
    def iniciar_transaccion(self, pedido, url_retorno: str):
        """
        Inicia la transacción con la pasarela.
        Debe retornar una tupla (url_redireccion, token_o_identificador).
        """
        pass

    @abstractmethod
    def confirmar_transaccion(self, token: str):
        """
        Valida y confirma el resultado de la transacción enviada por la pasarela.
        Debe retornar un dict con { 'exito': bool, 'codigo_autorizacion': str, 'monto': int }
        """
        pass


class PasarelaPagoLocal(PasarelaPagoInterface):
    """
    Implementación por defecto: Pago directo en el local físico al retirar o atenderse.
    """
    def iniciar_transaccion(self, pedido, url_retorno: str):
        return url_retorno, f"LOCAL-{pedido.codigo_pedido}"

    def confirmar_transaccion(self, token: str):
        return {
            'exito': True,
            'codigo_autorizacion': 'AUTORIZADO-LOCAL',
            'mensaje': 'Pago acordado para liquidar directamente en el local.'
        }


class PasarelaFlowPlaceholder(PasarelaPagoInterface):
    """
    Placeholder listo para conectar Flow (Chile) vía API REST.
    Solo requiere agregar FLOW_API_KEY y FLOW_SECRET_KEY en .env.
    """
    def iniciar_transaccion(self, pedido, url_retorno: str):
        # En producción: invocar endpoint POST /api/payment/create de Flow
        return url_retorno, f"FLOW-TOKEN-PENDIENTE-{pedido.codigo_pedido}"

    def confirmar_transaccion(self, token: str):
        # En producción: invocar endpoint GET /api/payment/getStatus de Flow
        return {
            'exito': True,
            'codigo_autorizacion': 'FLOW-DEMO',
            'mensaje': 'Transacción simulada Flow aprobada.'
        }
