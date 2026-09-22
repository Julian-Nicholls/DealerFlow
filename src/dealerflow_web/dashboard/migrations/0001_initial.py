from django.db import migrations,models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial=True
    dependencies=[]
    operations=[
        migrations.CreateModel(name="ScenarioRecord",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("name",models.CharField(max_length=200)),("source_path",models.CharField(blank=True,max_length=500)),
            ("source_yaml",models.TextField()),("content_sha256",models.CharField(max_length=64,unique=True)),
            ("created_at",models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.CreateModel(name="SimulationRun",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("status",models.CharField(choices=[("RUNNING","Running"),("COMPLETE","Complete"),("FAILED","Failed")],default="RUNNING",max_length=16)),
            ("seed",models.BigIntegerField()),("start_date",models.DateField()),("end_date",models.DateField()),
            ("event_digest",models.CharField(blank=True,max_length=64)),("event_count",models.PositiveIntegerField(default=0)),
            ("summary",models.JSONField(blank=True,default=dict)),("error",models.TextField(blank=True)),
            ("created_at",models.DateTimeField(auto_now_add=True)),("finished_at",models.DateTimeField(blank=True,null=True)),
            ("scenario",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="runs",to="dashboard.scenariorecord")),
        ],options={"ordering":["-created_at"]}),
        migrations.CreateModel(name="SimulationEventRecord",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("sequence",models.PositiveIntegerField()),("simulation_day",models.FloatField()),("occurred_at",models.DateTimeField()),
            ("event_type",models.CharField(max_length=64)),("entity_type",models.CharField(max_length=64)),
            ("entity_id",models.CharField(max_length=128)),("location_id",models.CharField(blank=True,max_length=128)),
            ("correlation_id",models.CharField(blank=True,max_length=128)),("payload",models.JSONField(blank=True,default=dict)),
            ("run",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="events",to="dashboard.simulationrun")),
        ],options={"ordering":["sequence"]}),
        migrations.AddConstraint(model_name="simulationeventrecord",constraint=models.UniqueConstraint(fields=("run","sequence"),name="unique_run_event_sequence")),
        migrations.AddIndex(model_name="simulationeventrecord",index=models.Index(fields=["run","simulation_day"],name="df_run_day_idx")),
        migrations.AddIndex(model_name="simulationeventrecord",index=models.Index(fields=["run","event_type"],name="df_run_type_idx")),
    ]
