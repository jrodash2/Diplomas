class TicketsRouter:
    
    def db_for_read(self, model, **hints):
        # Todo se lee del default
        return 'default'

    def db_for_write(self, model, **hints):
        # Todo se escribe en default
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Django nunca debe crear tablas en scompras_db
        if db == 'scompras_db':
            return False
        return True
