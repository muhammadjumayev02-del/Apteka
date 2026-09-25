from django.db import migrations


def preserve(apps, schema_editor):
    Medicine = apps.get_model('catalog', 'Medicine')
    Batch = apps.get_model('catalog', 'Batch')
    Placement = apps.get_model('catalog', 'Placement')
    for medicine in Medicine.objects.all().iterator():
        batch, _ = Batch.objects.get_or_create(medicine=medicine, number='Boshlang‘ich partiya')
        Placement.objects.filter(medicine=medicine, batch__isnull=True).update(batch=batch)


class Migration(migrations.Migration):
    dependencies = [('catalog', '0002_batch_sale_shift_stocktransfer_and_more')]
    operations = [migrations.RunPython(preserve, migrations.RunPython.noop)]
