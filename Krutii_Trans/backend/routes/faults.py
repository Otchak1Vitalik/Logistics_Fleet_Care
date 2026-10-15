"""
Маршрути управління звітами про несправності
"""
import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, g, send_from_directory, current_app
from bson import ObjectId
from marshmallow import ValidationError
from werkzeug.utils import secure_filename

from extensions import mongo
from middleware.auth_middleware import require_auth, require_role
from models.fault import FaultSchema, FaultCreateSchema, FaultUpdateSchema
from services.doc_generator import generate_doc_number

# Дозволені розширення файлів
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'faults')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

faults_bp = Blueprint('faults', __name__)
fault_schema = FaultSchema()
faults_schema = FaultSchema(many=True)
create_schema = FaultCreateSchema()
update_schema = FaultUpdateSchema()


def enrich_fault(fault):
    """Додає пов'язані дані до звіту."""
    if fault.get('vehicle_id'):
        vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(fault['vehicle_id'])})
        if vehicle:
            vehicle['_id'] = str(vehicle['_id'])
            fault['vehicle'] = vehicle

    if fault.get('reported_by'):
        reporter = mongo.db.users.find_one({'_id': ObjectId(fault['reported_by'])})
        if reporter:
            reporter['_id'] = str(reporter['_id'])
            if 'password_hash' in reporter:
                del reporter['password_hash']
            fault['reporter'] = reporter

    if fault.get('acknowledged_by'):
        mechanic = mongo.db.users.find_one({'_id': ObjectId(fault['acknowledged_by'])})
        if mechanic:
            mechanic['_id'] = str(mechanic['_id'])
            if 'password_hash' in mechanic:
                del mechanic['password_hash']
            fault['mechanic'] = mechanic

    return fault


@faults_bp.route('', methods=['GET'])
@require_auth
def get_faults():
    """
    Отримання списку звітів про несправності.
    Водії бачать тільки свої, механіки та керівники - всі.
    """
    status = request.args.get('status')
    vehicle_id = request.args.get('vehicle_id')
    severity = request.args.get('severity')
    category = request.args.get('category')

    query = {}

    if g.current_user['role'] == 'driver':
        query['reported_by'] = g.current_user['_id']

    if status:
        query['status'] = status
    if vehicle_id:
        query['vehicle_id'] = vehicle_id
    if severity:
        query['severity'] = severity
    if category:
        query['category'] = category

    faults = list(mongo.db.fault_reports.find(query).sort('report_date', -1))

    for fault in faults:
        fault['_id'] = str(fault['_id'])
        enrich_fault(fault)

    return jsonify({
        'success': True,
        'faults': faults,
        'total': len(faults)
    })


@faults_bp.route('/<fault_id>', methods=['GET'])
@require_auth
def get_fault(fault_id):
    """
    Отримання конкретного звіту.
    """
    try:
        fault = mongo.db.fault_reports.find_one({'_id': ObjectId(fault_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not fault:
        return jsonify({
            'success': False,
            'error': 'Звіт не знайдено.'
        }), 404

    # Водій може бачити тільки свої звіти
    if g.current_user['role'] == 'driver' and fault.get('reported_by') != g.current_user['_id']:
        return jsonify({
            'success': False,
            'error': 'Доступ заборонено.'
        }), 403

    fault['_id'] = str(fault['_id'])
    enrich_fault(fault)

    return jsonify({
        'success': True,
        'fault': fault
    })


@faults_bp.route('', methods=['POST'])
@require_auth
@require_role('driver')
def create_fault():
    """
    Створення звіту про несправність (тільки водії).
    Водій може повідомляти тільки про несправності авто, на яке має активну путівку.
    """
    try:
        data = create_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({
            'success': False,
            'error': 'Помилка валідації.',
            'details': err.messages
        }), 400

    # Перевірка існування авто
    vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(data['vehicle_id'])})
    if not vehicle:
        return jsonify({
            'success': False,
            'error': 'Транспортний засіб не знайдено.'
        }), 400

    # Перевірка чи водій має активну путівку на це авто
    active_waybill = mongo.db.waybills.find_one({
        'driver_id': g.current_user['_id'],
        'vehicle_id': data['vehicle_id'],
        'status': {'$in': ['issued', 'active']}
    })
    if not active_waybill:
        return jsonify({
            'success': False,
            'error': 'Ви можете повідомляти про несправності тільки закріпленого за вами транспорту.'
        }), 403

    doc_number = generate_doc_number(mongo.db, 'fault')

    fault_doc = {
        'number': doc_number,
        'vehicle_id': data['vehicle_id'],
        'reported_by': g.current_user['_id'],
        'report_date': datetime.utcnow(),
        'category': data['category'],
        'severity': data['severity'],
        'description': data['description'],
        'odometer': data.get('odometer') or vehicle.get('odometer'),
        'status': 'new',
        'photos': [],  # Масив шляхів/URL до фото
        'acknowledged_by': None,
        'acknowledged_at': None,
        'resolution': None,
        'resolved_at': None,
        'rejection_reason': None,
        'repair_id': None,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

    result = mongo.db.fault_reports.insert_one(fault_doc)
    fault_doc['_id'] = str(result.inserted_id)
    enrich_fault(fault_doc)

    # Сповіщення механікам про нову несправність
    from services.alert_engine import create_alert
    severity_labels = {'low': 'низька', 'medium': 'середня', 'high': 'висока', 'critical': 'критична'}
    alert_type = 'critical' if data['severity'] == 'critical' else 'warning' if data['severity'] == 'high' else 'info'
    create_alert(
        mongo.db,
        alert_type=alert_type,
        category='fault',
        title=f'Нова несправність: {vehicle["plate_number"]}',
        message=f'Серйозність: {severity_labels.get(data["severity"], data["severity"])}. {data["description"][:80]}',
        recipient_role='mechanic',
        related_type='fault',
        related_id=str(result.inserted_id)
    )

    return jsonify({
        'success': True,
        'message': f'Звіт {doc_number} створено.',
        'fault': fault_doc
    }), 201


@faults_bp.route('/<fault_id>', methods=['PUT'])
@require_auth
@require_role('mechanic', 'manager')
def update_fault(fault_id):
    """
    Оновлення звіту про несправність.
    """
    try:
        data = update_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({
            'success': False,
            'error': 'Помилка валідації.',
            'details': err.messages
        }), 400

    try:
        fault = mongo.db.fault_reports.find_one({'_id': ObjectId(fault_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not fault:
        return jsonify({
            'success': False,
            'error': 'Звіт не знайдено.'
        }), 404

    new_status = data.get('status')
    current_status = fault.get('status')

    update_data = {k: v for k, v in data.items() if v is not None}
    update_data['updated_at'] = datetime.utcnow()

    # Логіка переходів статусів
    if new_status == 'acknowledged' and current_status == 'new':
        update_data['acknowledged_by'] = g.current_user['_id']
        update_data['acknowledged_at'] = datetime.utcnow()

    if new_status == 'resolved':
        if not data.get('resolution'):
            return jsonify({
                'success': False,
                'error': 'Вкажіть опис рішення.'
            }), 400
        update_data['resolved_at'] = datetime.utcnow()

    if new_status == 'rejected':
        if not data.get('rejection_reason'):
            return jsonify({
                'success': False,
                'error': 'Вкажіть причину відхилення.'
            }), 400

    mongo.db.fault_reports.update_one(
        {'_id': ObjectId(fault_id)},
        {'$set': update_data}
    )

    updated_fault = mongo.db.fault_reports.find_one({'_id': ObjectId(fault_id)})
    updated_fault['_id'] = str(updated_fault['_id'])
    enrich_fault(updated_fault)

    return jsonify({
        'success': True,
        'message': 'Звіт оновлено.',
        'fault': updated_fault
    })


@faults_bp.route('/pending', methods=['GET'])
@require_auth
@require_role('mechanic', 'manager')
def get_pending_faults():
    """
    Отримання несправностей, що потребують уваги.
    """
    faults = list(mongo.db.fault_reports.find({
        'status': {'$in': ['new', 'acknowledged']}
    }).sort([('severity', -1), ('report_date', 1)]))

    for fault in faults:
        fault['_id'] = str(fault['_id'])
        enrich_fault(fault)

    return jsonify({
        'success': True,
        'faults': faults,
        'total': len(faults)
    })


@faults_bp.route('/statistics', methods=['GET'])
@require_auth
@require_role('manager')
def fault_statistics():
    """
    Статистика по несправностях.
    """
    # По статусах
    by_status = list(mongo.db.fault_reports.aggregate([
        {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
    ]))

    # По категоріях
    by_category = list(mongo.db.fault_reports.aggregate([
        {'$group': {'_id': '$category', 'count': {'$sum': 1}}}
    ]))

    # По критичності
    by_severity = list(mongo.db.fault_reports.aggregate([
        {'$group': {'_id': '$severity', 'count': {'$sum': 1}}}
    ]))

    # Найпроблемніші авто
    by_vehicle = list(mongo.db.fault_reports.aggregate([
        {'$group': {'_id': '$vehicle_id', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 5}
    ]))

    # Збагачуємо даними про авто
    for item in by_vehicle:
        if item['_id']:
            vehicle = mongo.db.vehicles.find_one({'_id': ObjectId(item['_id'])})
            if vehicle:
                item['vehicle'] = {
                    'plate_number': vehicle['plate_number'],
                    'brand': vehicle['brand'],
                    'model': vehicle['model']
                }

    return jsonify({
        'success': True,
        'by_status': by_status,
        'by_category': by_category,
        'by_severity': by_severity,
        'by_vehicle': by_vehicle
    })


@faults_bp.route('/<fault_id>/photos', methods=['POST'])
@require_auth
def upload_photo(fault_id):
    """
    Завантаження фото до несправності.
    Підтримує: файл (multipart) або URL.
    """
    try:
        fault = mongo.db.fault_reports.find_one({'_id': ObjectId(fault_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not fault:
        return jsonify({
            'success': False,
            'error': 'Звіт не знайдено.'
        }), 404

    # Водій може додавати фото тільки до своїх звітів
    if g.current_user['role'] == 'driver' and fault.get('reported_by') != g.current_user['_id']:
        return jsonify({
            'success': False,
            'error': 'Доступ заборонено.'
        }), 403

    photos = fault.get('photos', [])

    # Якщо це URL
    if request.is_json:
        data = request.get_json()
        photo_url = data.get('url')
        if photo_url:
            if not photo_url.startswith(('http://', 'https://')):
                return jsonify({
                    'success': False,
                    'error': 'Невірний формат URL.'
                }), 400
            photos.append(photo_url)
    # Якщо це файл
    elif 'photo' in request.files:
        file = request.files['photo']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Файл не вибрано.'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Дозволені формати: PNG, JPG, JPEG, GIF, WEBP.'
            }), 400

        # Генеруємо унікальне ім'я файлу
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{fault_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Зберігаємо файл
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file.save(filepath)

        # Зберігаємо відносний шлях
        photos.append(f"/api/faults/uploads/{filename}")
    else:
        return jsonify({
            'success': False,
            'error': 'Надішліть файл або URL.'
        }), 400

    # Оновлюємо запис
    mongo.db.fault_reports.update_one(
        {'_id': ObjectId(fault_id)},
        {'$set': {'photos': photos, 'updated_at': datetime.utcnow()}}
    )

    return jsonify({
        'success': True,
        'message': 'Фото додано.',
        'photos': photos
    })


@faults_bp.route('/<fault_id>/photos/<int:photo_index>', methods=['DELETE'])
@require_auth
def delete_photo(fault_id, photo_index):
    """
    Видалення фото з несправності.
    """
    try:
        fault = mongo.db.fault_reports.find_one({'_id': ObjectId(fault_id)})
    except:
        return jsonify({
            'success': False,
            'error': 'Невірний формат ID.'
        }), 400

    if not fault:
        return jsonify({
            'success': False,
            'error': 'Звіт не знайдено.'
        }), 404

    # Водій може видаляти фото тільки зі своїх звітів
    if g.current_user['role'] == 'driver' and fault.get('reported_by') != g.current_user['_id']:
        return jsonify({
            'success': False,
            'error': 'Доступ заборонено.'
        }), 403

    photos = fault.get('photos', [])

    if photo_index < 0 or photo_index >= len(photos):
        return jsonify({
            'success': False,
            'error': 'Фото не знайдено.'
        }), 404

    # Видаляємо файл якщо це локальний файл
    photo_path = photos[photo_index]
    if photo_path.startswith('/api/faults/uploads/'):
        filename = photo_path.split('/')[-1]
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)

    # Видаляємо з масиву
    photos.pop(photo_index)

    mongo.db.fault_reports.update_one(
        {'_id': ObjectId(fault_id)},
        {'$set': {'photos': photos, 'updated_at': datetime.utcnow()}}
    )

    return jsonify({
        'success': True,
        'message': 'Фото видалено.',
        'photos': photos
    })


@faults_bp.route('/uploads/<filename>', methods=['GET'])
def get_photo(filename):
    """
    Отримання завантаженого фото.
    """
    return send_from_directory(UPLOAD_FOLDER, filename)
