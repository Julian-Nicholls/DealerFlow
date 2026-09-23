from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("runs/baseline/", views.create_baseline_run, name="create-baseline-run"),
    path("runs/<int:pk>/", views.run_detail, name="run-detail"),
    path("api/runs/<int:pk>/replay/", views.run_replay_api, name="run-replay-api"),
    path("api/runs/<int:pk>/inspect/", views.run_inspect_api, name="run-inspect-api"),
]
