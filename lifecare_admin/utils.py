import csv

from django.http import HttpResponse

def export_to_csv(queryset, field_mappings, filename="export.csv"):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(list(field_mappings.keys()))

    for obj in queryset:
        row = []
        for attr in field_mappings.values():
            if callable(attr):
                val = attr(obj)
            elif '__' in attr:
                parts = attr.split('__')
                val = obj
                for p in parts:
                    val = getattr(val, p, None) if val else None
            else:
                val = getattr(obj, attr, '')

            row.append(val)
        writer.writerow(row)

    return response