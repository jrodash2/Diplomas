import smtplib
import traceback

smtp_server = "smtp.gmail.com"
port = 587
sender_email = "informatica@upcv.gob.gt"
password = "xtdj nvwz ymyw lqyr"  # App password

try:
    print("➡️ Iniciando conexión con el servidor SMTP...")
    server = smtplib.SMTP(smtp_server, port)
    server.ehlo()
    server.starttls()
    server.login(sender_email, password)
    print("✅ Conexión y autenticación exitosas.")
except Exception as e:
    print("❌ Error al conectarse o autenticar:")
    traceback.print_exc()
finally:
    try:
        server.quit()
    except:
        pass
