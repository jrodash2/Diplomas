class TicketsRouter:
    """
    Envía las consultas del modelo Empleado a la base de datos 'tickets_db'.
    """
    route_app_labels = {'empleados_app'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'tickets_db'
        return None

    def db_for_write(self, model, **hints):
        return None  # Solo lectura

    def allow_relation(self, obj1, obj2, **hints):
        # 🔥 Permitir relaciones entre objetos
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == 'tickets_db'
        return None
