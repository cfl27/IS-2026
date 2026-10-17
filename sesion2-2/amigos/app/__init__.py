from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Importamos el diccionario de configuraciones
from config import app_config

# Crear el objeto db que servirá para conectar con la base de datos
db = SQLAlchemy()


def create_app(config_name):
    # Creamos la aplicación Flask
    app = Flask(__name__, instance_relative_config=True)

    # Cargamos la configuración general
    app.config.from_object(app_config[config_name])

    # Cargamos la configuración privada de instance/config.py
    app.config.from_pyfile('config.py')

    # Inicializamos SQLAlchemy con esta aplicación
    db.init_app(app)

    migrate = Migrate(app, db)
    from app import models

    # Ruta de prueba
    @app.route('/amigos')
    def hola_mundo():
        from app.models import Amigo

        amigos = Amigo.query.all()

        return render_template(
            'tabla_amigos.html',
            amigos=amigos
        )   
    return app