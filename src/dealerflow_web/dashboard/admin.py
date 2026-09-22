from django.contrib import admin
from .models import ScenarioRecord,SimulationRun,SimulationEventRecord
admin.site.register(ScenarioRecord); admin.site.register(SimulationRun); admin.site.register(SimulationEventRecord)
