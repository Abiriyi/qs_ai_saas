# boq/services/project_service.py

from projects.models import Project


def get_project(project_id):

    return Project.objects.get(id=project_id)