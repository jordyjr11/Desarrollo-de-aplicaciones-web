from flask import Flask, render_template, redirect, url_for, flash, request, send_file
from datetime import datetime
from models import db, Producto
from forms import ProductoForm
from inventory import Inventario
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventario.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-secret-key'

db.init_app(app)

# Inyectar "now" para usar {{ now().year }} en templates
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}

with app.app_context():
    db.create_all()
    inventario = Inventario.cargar_desde_bd()


# --- Rutas ---
@app.route('/')
def index():
    return render_template('index.html', title='Inicio')


@app.route('/about')
def about():
    return render_template('about.html', title='Acerca de')


@app.route('/productos')
def listar_productos():
    q = request.args.get('q', '').strip()
    productos = inventario.buscar_por_nombre(q) if q else inventario.listar_todos()
    return render_template('products/list.html', title='Productos', productos=productos, q=q)


@app.route('/productos/nuevo', methods=['GET', 'POST'])
def crear_producto():
    form = ProductoForm()
    if form.validate_on_submit():
        try:
            inventario.agregar(
                nombre=form.nombre.data,
                cantidad=form.cantidad.data,
                precio=form.precio.data
            )
            flash('Producto agregado correctamente.', 'success')
            return redirect(url_for('listar_productos'))
        except ValueError as e:
            form.nombre.errors.append(str(e))
    return render_template('products/form.html', title='Nuevo producto', form=form, modo='crear')


@app.route('/productos/<int:pid>/editar', methods=['GET', 'POST'])
def editar_producto(pid):
    prod = Producto.query.get_or_404(pid)
    form = ProductoForm(obj=prod)
    if form.validate_on_submit():
        try:
            inventario.actualizar(
                id=pid,
                nombre=form.nombre.data,
                cantidad=form.cantidad.data,
                precio=form.precio.data
            )
            flash('Producto actualizado.', 'success')
            return redirect(url_for('listar_productos'))
        except ValueError as e:
            form.nombre.errors.append(str(e))
    return render_template('products/form.html', title='Editar producto', form=form, modo='editar')


@app.route('/productos/<int:pid>/eliminar', methods=['POST'])
def eliminar_producto(pid):
    ok = inventario.eliminar(pid)
    flash('Producto eliminado.' if ok else 'Producto no encontrado.', 'info' if ok else 'warning')
    return redirect(url_for('listar_productos'))


# --- Rutas JSON ---
@app.route('/exportar-json')
def exportar_json():
    """Exporta la BD a JSON y lo ofrece como descarga"""
    ruta_archivo = Inventario.exportar_bd_a_json()
    if os.path.exists(ruta_archivo):
        flash("Productos exportados correctamente ✅", "success")
        return send_file(ruta_archivo, as_attachment=True)
    else:
        flash("Error al exportar productos ❌", "danger")
        return redirect(url_for('listar_productos'))


@app.route('/importar-json')
def importar_json():
    """Importa desde datos.json a la BD"""
    afectados = Inventario.importar_json_a_bd(sobrescribir_si_duplicado=True)
    flash(f"Registros importados/actualizados: {afectados}", "success")
    return redirect(url_for('listar_productos'))


if __name__ == '__main__':
    app.run(debug=True)

