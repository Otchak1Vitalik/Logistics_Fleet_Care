"""
Пакетне завантаження пов'язаних документів.

Замість окремого запиту до БД для кожного елемента списку (проблема «N+1 запитів»)
всі потрібні документи вибираються одним запитом з оператором $in.
"""
from bson import ObjectId
from bson.errors import InvalidId


def fetch_by_ids(collection, ids):
    """Повертає словник {str(_id): документ} для заданих ідентифікаторів."""
    object_ids = set()
    for value in ids:
        if not value:
            continue
        try:
            object_ids.add(ObjectId(value))
        except (InvalidId, TypeError):
            continue
    if not object_ids:
        return {}
    result = {}
    for doc in collection.find({'_id': {'$in': list(object_ids)}}, {'password_hash': 0}):
        doc['_id'] = str(doc['_id'])
        result[doc['_id']] = doc
    return result
