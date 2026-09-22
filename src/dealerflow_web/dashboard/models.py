from django.db import models

class ScenarioRecord(models.Model):
    name=models.CharField(max_length=200)
    source_path=models.CharField(max_length=500,blank=True)
    source_yaml=models.TextField()
    content_sha256=models.CharField(max_length=64,unique=True)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name

class SimulationRun(models.Model):
    class Status(models.TextChoices):
        RUNNING="RUNNING","Running"; COMPLETE="COMPLETE","Complete"; FAILED="FAILED","Failed"
    scenario=models.ForeignKey(ScenarioRecord,on_delete=models.PROTECT,related_name="runs")
    status=models.CharField(max_length=16,choices=Status.choices,default=Status.RUNNING)
    seed=models.BigIntegerField(); start_date=models.DateField(); end_date=models.DateField()
    event_digest=models.CharField(max_length=64,blank=True); event_count=models.PositiveIntegerField(default=0)
    summary=models.JSONField(default=dict,blank=True); error=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True); finished_at=models.DateTimeField(null=True,blank=True)
    class Meta: ordering=["-created_at"]
    def __str__(self): return f"{self.scenario.name} #{self.pk or 'new'}"

class SimulationEventRecord(models.Model):
    run=models.ForeignKey(SimulationRun,on_delete=models.CASCADE,related_name="events")
    sequence=models.PositiveIntegerField(); simulation_day=models.FloatField(); occurred_at=models.DateTimeField()
    event_type=models.CharField(max_length=64); entity_type=models.CharField(max_length=64); entity_id=models.CharField(max_length=128)
    location_id=models.CharField(max_length=128,blank=True); correlation_id=models.CharField(max_length=128,blank=True)
    payload=models.JSONField(default=dict,blank=True)
    class Meta:
        ordering=["sequence"]
        constraints=[models.UniqueConstraint(fields=["run","sequence"],name="unique_run_event_sequence")]
        indexes=[models.Index(fields=["run","simulation_day"],name="df_run_day_idx"),models.Index(fields=["run","event_type"],name="df_run_type_idx")]
