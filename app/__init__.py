
import os
from flask import Flask
from dotenv import load_dotenv
from sqlalchemy import inspect, text
from config import Config, DevelopmentConfig, ProductionConfig
from app.extensions import db, login_manager, mail

load_dotenv()

def create_app(config_name=None):
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')

    config_name = config_name or os.environ.get('FLASK_CONFIG', 'development')
    config_class = ProductionConfig if config_name == 'production' else DevelopmentConfig
    app.config.from_object(config_class)

    if config_name == 'production':
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key or secret_key in {'dev-secret-key', 'votre_cle_secrete_ici'}:
            raise RuntimeError('SECRET_KEY doit être défini en production.')
        if not os.environ.get('ADMIN_PASSWORD'):
            raise RuntimeError('ADMIN_PASSWORD doit être défini en production.')

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    database_url = os.environ.get('DATABASE_URL')
    if config_name == 'production' and not database_url:
        raise RuntimeError('DATABASE_URL doit être défini en production.')
    if config_name == 'production' and database_url.startswith('sqlite:'):
        raise RuntimeError('Une base PostgreSQL persistante est requise en production.')
    if not database_url:
        database_url = f'sqlite:///{os.path.join(base_dir, "phenix.db")}'
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    if os.environ.get('VERCEL') == '1':
        app.config['UPLOAD_FOLDER'] = os.path.join('/tmp', 'phenix-uploads')
    else:
        app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'uploads')
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', app.config['MAIL_SERVER'])
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', app.config['MAIL_PORT']))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', str(app.config['MAIL_USE_TLS'])) == 'True'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get(
        'MAIL_DEFAULT_SENDER', app.config['MAIL_DEFAULT_SENDER'])
    app.config['SESSION_COOKIE_SECURE'] = config_name == 'production'

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    
    from app.auth import auth_bp
    from app.routes import routes_bp
    from app.admin_routes import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()
        _migrate_stagiaire_columns()
    
    return app


def _migrate_stagiaire_columns():
    """Ajoute les colonnes manquantes dans les bases locales existantes."""
    from app.models import Stagiaire

    inspector = inspect(db.engine)
    if 'stagiaires' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('stagiaires')}
    for column in Stagiaire.__table__.columns:
        if column.name in columns or column.primary_key:
            continue

        definition = column.type.compile(dialect=db.engine.dialect)
        default = column.default.arg if column.default and not callable(column.default.arg) else None
        if isinstance(default, bool):
            definition += ' DEFAULT FALSE' if default else ' DEFAULT FALSE'
        elif isinstance(default, int):
            definition += f' DEFAULT {default}'

        db.session.execute(text(
            f'ALTER TABLE stagiaires ADD COLUMN "{column.name}" {definition}'
        ))

    db.session.execute(text(
        """
        UPDATE stagiaires
        SET dossiers_deposes = TRUE
        WHERE (dossiers_deposes IS NULL OR dossiers_deposes = FALSE)
        AND (
            dossier_complet = TRUE
            OR (photo IS NOT NULL AND cv IS NOT NULL
                AND lettre_demande IS NOT NULL AND dernier_diplome IS NOT NULL)
        )
        """
    ))
    db.session.commit()
