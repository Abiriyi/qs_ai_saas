"""
URL configuration for qs_ai_saas project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from audit.views import audit_trail
from core.views import auth_page, dashboard, healthz, home, project_detail, project_pricing_review, project_workflow
from tribunal.views import tribunal_case_detail, tribunal_dashboard

urlpatterns = [
    path('', home, name='home'),
    path('healthz/', healthz, name='healthz'),
    path('login/', auth_page, name='login'),

    # Password reset. Django's built-in views handle token generation,
    # single-use links and expiry; we supply app-styled templates.
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            success_url="/password-reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="password_reset_confirm.html",
            success_url="/password-reset/complete/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),

    path('dashboard/', dashboard, name='dashboard'),
    path('projects/new/', project_workflow, name='project_workflow'),
    path('projects/<uuid:pk>/', project_detail, name='project_detail'),
    path('projects/<uuid:pk>/pricing/', project_pricing_review, name='project_pricing_review'),
    path('audit/', audit_trail, name='audit_trail'),
    path('tribunal/', tribunal_dashboard, name='tribunal_dashboard'),
    path('tribunal/<uuid:pk>/', tribunal_case_detail, name='tribunal_case_detail'),
    path('admin/', admin.site.urls),

    path(
        "api/documents/",
        include("documents.api.urls")
    ),
    path(
        "api/boq/",
        include("boq.api.urls")
    ),
    path(
        "api/audit/",
        include("audit.api.urls")
    ),
    path(
        "api/tribunal/",
        include("tribunal.api.urls")
    ),
]
