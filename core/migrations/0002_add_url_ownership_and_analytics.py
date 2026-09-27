from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def delete_ownerless_urls(apps, schema_editor):
    # V1 URLs have no owner and are intentionally discarded before ownership is required.
    shortened_url = apps.get_model('core', 'ShortenedURL')
    shortened_url.objects.using(schema_editor.connection.alias).filter(
        owner__isnull=True
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='shortenedurl',
            name='owner',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='shortened_urls',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='shortenedurl',
            name='click_count',
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='shortenedurl',
            name='last_clicked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            delete_ownerless_urls,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='shortenedurl',
            name='owner',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='shortened_urls',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
