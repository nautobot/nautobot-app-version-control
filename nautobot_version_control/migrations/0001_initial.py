from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Branch",
            fields=[
                ("name", models.TextField(primary_key=True, serialize=False)),
                ("hash", models.TextField()),
                ("latest_committer", models.TextField()),
                ("latest_committer_email", models.TextField()),
                ("latest_commit_date", models.DateTimeField()),
                ("latest_commit_message", models.TextField()),
            ],
            options={
                "verbose_name_plural": "branches",
                "db_table": "dolt_branches",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="Commit",
            fields=[
                ("commit_hash", models.TextField(primary_key=True, serialize=False)),
                ("committer", models.TextField()),
                ("email", models.TextField()),
                ("date", models.DateTimeField()),
                ("message", models.TextField()),
            ],
            options={
                "verbose_name_plural": "commits",
                "db_table": "dolt_log",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="CommitAncestor",
            fields=[
                ("commit_hash", models.TextField(primary_key=True, serialize=False)),
                ("parent_hash", models.TextField()),
                ("parent_index", models.IntegerField()),
            ],
            options={
                "verbose_name_plural": "commit_ancestors",
                "db_table": "dolt_commit_ancestors",
                "managed": False,
            },
        ),
    ]
