# Pra pruebas 
from app import app
from inventory import Inventario

# El contexto de la app es necesario para que SQLAlchemy funcione
with app.app_context():
    n = Inventario.exportar_bd_a_json()
    print(f"Exportados {n} productos a datos/datos.json")

    afectados = Inventario.importar_json_a_bd(sobrescribir_si_duplicado=True)
    print(f"Registros importados/actualizados: {afectados}")
