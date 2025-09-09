from models import db, Producto
import json
import os

 # rutas 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(BASE_DIR, "datos")
JSON_PATH = os.path.join(JSON_DIR, "datos.json")

class Inventario:
    """
    - Usa un diccionario {id: Producto} para accesos O(1).
    - Mantiene un set con nombres en minúsculas para validar duplicados rápidamente.
    - Devuelve listas ordenadas usando list/tuplas según convenga.
    """
    def __init__(self, productos_dict=None):
        self.productos = productos_dict or {}  # dict[int, Producto]
        self.nombres = set(p.nombre.lower() for p in self.productos.values())

    @classmethod
    def cargar_desde_bd(cls):
        productos = Producto.query.all()              # -> list[Producto]
        productos_dict = {p.id: p for p in productos} # dict por id
        return cls(productos_dict)

    # --- CRUD ---
    def agregar(self, nombre: str, cantidad: int, precio: float) -> Producto:
        if nombre.lower() in self.nombres:
            raise ValueError('Ya existe un producto con ese nombre.')
        p = Producto(nombre=nombre.strip(), cantidad=int(cantidad), precio=float(precio))
        db.session.add(p)
        db.session.commit()
        self.productos[p.id] = p
        self.nombres.add(p.nombre.lower())
        return p

    def eliminar(self, id: int) -> bool:
        p = self.productos.get(id) or Producto.query.get(id)
        if not p:
            return False
        db.session.delete(p)
        db.session.commit()
        self.productos.pop(id, None)
        self.nombres.discard(p.nombre.lower())
        return True

    def actualizar(self, id: int, nombre=None, cantidad=None, precio=None) -> Producto | None:
        p = self.productos.get(id) or Producto.query.get(id)
        if not p:
            return None
        if nombre is not None:
            nuevo = nombre.strip()
            if nuevo.lower() != p.nombre.lower() and nuevo.lower() in self.nombres:
                raise ValueError('Ya existe otro producto con ese nombre.')
            self.nombres.discard(p.nombre.lower())
            p.nombre = nuevo
            self.nombres.add(p.nombre.lower())
        if cantidad is not None:
            p.cantidad = int(cantidad)
        if precio is not None:
            p.precio = float(precio)
        db.session.commit()
        self.productos[p.id] = p
        return p

    # --- Consultas con colecciones ---
    def buscar_por_nombre(self, q: str):
        q = q.lower()
        # list comprehension: filtra del dict de cache
        return sorted([p for p in self.productos.values() if q in p.nombre.lower()],
                      key=lambda x: x.nombre)

    def listar_todos(self):
        return sorted(self.productos.values(), key=lambda x: x.nombre)
    
   
     # --- JSON <-> BD ---
    @staticmethod
    def _asegurar_directorio_json():
        os.makedirs(JSON_DIR, exist_ok=True)

    @classmethod
    def cargar_desde_json(cls) -> "Inventario":
        """
        Crea un Inventario desde datos/datos.json (NO toca la BD).
        Estructura esperada:
        { "productos": [ {"id":1,"nombre":"...","cantidad":10,"precio":2.5}, ... ] }
        """
        if not os.path.exists(JSON_PATH):
            # Si no existe, devuelve inventario vacío
            return cls(productos_dict={})
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        productos = data.get("productos", [])
        # OJO: aquí no creamos objetos de la clase Producto (SQLAlchemy), solo dicts
        # Para mantener la interfaz, devolveremos un inventario con objetos Producto "simples"
        # creados en memoria (sin sesión). Alternativa: usa importar_json_a_bd()
        productos_dict = {}
        for item in productos:
            p = Producto(
                id=item.get("id"),
                nombre=item["nombre"],
                cantidad=int(item["cantidad"]),
                precio=float(item["precio"]),
            )
            productos_dict[p.id] = p
        return cls(productos_dict)

    @classmethod
    def importar_json_a_bd(cls, sobrescribir_si_duplicado: bool = False) -> int:
        """
        Lee datos/datos.json e inserta/actualiza en la BD.
        - Si 'sobrescribir_si_duplicado' es True, actualiza cantidad/precio/nombre si el nombre ya existe.
        - Retorna cuántos registros fueron insertados/actualizados.
        """
        if not os.path.exists(JSON_PATH):
            return 0

        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        productos = data.get("productos", [])
        afectados = 0

        for item in productos:
            nombre = item["nombre"].strip()
            cantidad = int(item["cantidad"])
            precio = float(item["precio"])

            # buscar por nombre (único)
            existente = Producto.query.filter(
                db.func.lower(Producto.nombre) == nombre.lower()
            ).first()

            if existente:
                if sobrescribir_si_duplicado:
                    existente.nombre = nombre
                    existente.cantidad = cantidad
                    existente.precio = precio
                    afectados += 1
                # si no se sobrescribe, lo ignoramos
            else:
                nuevo = Producto(nombre=nombre, cantidad=cantidad, precio=precio)
                db.session.add(nuevo)
                afectados += 1

        db.session.commit()
        return afectados

    @classmethod
    def exportar_bd_a_json(cls) -> int:
        """
        Exporta TODOS los productos de la BD a datos/datos.json.
        Retorna el número de productos exportados.
        """
        cls._asegurar_directorio_json()

        productos = Producto.query.order_by(Producto.nombre.asc()).all()
        payload = {
            "productos": [
                {
                    "id": p.id,
                    "nombre": p.nombre,
                    "cantidad": int(p.cantidad),
                    "precio": float(p.precio),
                }
                for p in productos
            ]
        }
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
        return len(productos)

    @classmethod
    def inicializar_bd_desde_json_si_vacia(cls) -> int:
        """
        Si la tabla está vacía, carga datos desde datos.json.
        Útil en el arranque de la app para presembrar datos.
        """
        tiene = db.session.query(db.exists().where(Producto.id.isnot(None))).scalar()
        if tiene:
            return 0
        return cls.importar_json_a_bd(sobrescribir_si_duplicado=False)