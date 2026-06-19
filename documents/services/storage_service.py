# documents/services/storage_service.py

from django.core.files.storage import default_storage

class StorageService:

    @staticmethod
    def save(path, file_obj):
        return default_storage.save(path, file_obj)

    @staticmethod
    def open(path):
        return default_storage.open(path)

    @staticmethod
    def exists(path):
        return default_storage.exists(path)

    @staticmethod
    def delete(path):
        return default_storage.delete(path)