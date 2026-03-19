from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import connections


@receiver(post_save, sender=User)
def sync_user_create_update(sender, instance, created, **kwargs):
    """
    Sincroniza el usuario hacia Scompras cuando se crea o se actualiza en Tickets.
    """
    try:
        cursor = connections['scompras_db'].cursor()

        cursor.execute("""
            INSERT INTO auth_user (
                id, password, last_login,
                is_superuser, username, first_name, last_name,
                email, is_staff, is_active, date_joined
            )
            VALUES (
                %s, %s, NULL,
                %s, %s, %s, %s,
                %s, %s, %s, NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                password = EXCLUDED.password,
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                email = EXCLUDED.email,
                is_active = EXCLUDED.is_active;
        """, [
            instance.id,
            instance.password,
            instance.is_superuser,
            instance.username,
            instance.first_name,
            instance.last_name,
            instance.email,
            instance.is_staff,
            instance.is_active
        ])

        print(f"✔ Usuario sincronizado a Scompras: {instance.username}")

    except Exception as e:
        print("❌ ERROR sincronizando usuario en SCOMPRAS:", e)



@receiver(post_delete, sender=User)
def sync_user_delete(sender, instance, **kwargs):
    """
    Elimina también el usuario en Scompras cuando se borra en Tickets.
    """
    try:
        cursor = connections['scompras_db'].cursor()
        cursor.execute("DELETE FROM auth_user WHERE id = %s", [instance.id])
        print(f"✔ Usuario eliminado también en Scompras: {instance.username}")

    except Exception as e:
        print("❌ ERROR eliminando usuario en SCOMPRAS:", e)



from django.db import connections
from django.contrib.auth.models import User

def sync_user_to_apps(user, accesos):

    # ------------------------------
    # SCOMPRAS
    # ------------------------------
    if accesos.get('acceso_scompras'):
        try:
            cursor = connections['scompras_db'].cursor()
            cursor.execute("""
                INSERT INTO auth_user (id, username, first_name, last_name, email, password, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (id) DO NOTHING;
            """, [
                user.id, user.username, user.first_name, user.last_name,
                user.email, user.password
            ])
        except Exception as e:
            print("Error sincronizando usuario a Scompras:", e)
    else:
        try:
            cursor = connections['scompras_db'].cursor()
            cursor.execute("UPDATE auth_user SET is_active = FALSE WHERE id = %s", [user.id])
        except:
            pass

    # ------------------------------
    # MÁS APLICACIONES EN EL FUTURO
    # ------------------------------
