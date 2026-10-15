"""
KRUTII TRANS - Головний модуль Flask застосунку
"""
from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from extensions import mongo, jwt, limiter, scheduler


def create_app():
    """Фабрика застосунку Flask"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ініціалізація розширень
    mongo.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)

    # JWT callbacks
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'success': False,
            'error': 'Токен авторизації прострочено. Увійдіть знову.'
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'success': False,
            'error': 'Недійсний токен авторизації.'
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'success': False,
            'error': 'Необхідна авторизація.'
        }), 401

    # Реєстрація blueprints
    from routes.auth import auth_bp
    from routes.users import users_bp
    from routes.vehicles import vehicles_bp
    from routes.waybills import waybills_bp
    from routes.fuel import fuel_bp
    from routes.faults import faults_bp
    from routes.repairs import repairs_bp
    from routes.alerts import alerts_bp
    from routes.reports import reports_bp
    from routes.settings import settings_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(vehicles_bp, url_prefix='/api/vehicles')
    app.register_blueprint(waybills_bp, url_prefix='/api/waybills')
    app.register_blueprint(fuel_bp, url_prefix='/api/fuel')
    app.register_blueprint(faults_bp, url_prefix='/api/faults')
    app.register_blueprint(repairs_bp, url_prefix='/api/repairs')
    app.register_blueprint(alerts_bp, url_prefix='/api/alerts')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')

    # Запуск планувальника
    from services.alert_engine import setup_scheduler
    setup_scheduler(scheduler, app)
    scheduler.start()

    # Health check endpoint
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'service': 'KRUTII TRANS'})

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
