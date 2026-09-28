"""Strip spreadsheet float tails ("2530710047.0") from stored matric and
phone numbers.

A student whose cleaned matric number already belongs to another student
row is the same person uploaded twice (in the August data: MUT ND II
uploaded twice, and 64 students in both AGT ND I and AHPT ND I). The record
without the float tail is kept, any name, email or phone it lacks is filled
from the duplicate, and the ".0" duplicate is deleted with its seat rows.
Regenerate the distribution afterwards.
"""

from django.db import migrations
from django.db.models import Q

from ems.identifiers import clean_number_text


MERGED_FIELDS = ("first_name", "last_name", "email", "phone")


def _blank(value) -> bool:
    return (value or "").strip().lower() in ("", "nan", "none")


def clean(apps, schema_editor):
    Student = apps.get_model("ems", "Student")
    dirty = list(
        Student.objects.filter(
            Q(matric_no__regex=r"^\d+\.0+$") | Q(phone__regex=r"^\d+\.0+$")
        )
    )
    if not dirty:
        return
    cleaned = {s.id: clean_number_text(s.matric_no) for s in dirty}
    kept = {
        s.matric_no: s
        for s in Student.objects.filter(matric_no__in=set(cleaned.values()))
        .exclude(id__in=cleaned.keys())
    }
    duplicates, to_update = [], []
    # Rows whose matric number is already clean (only the phone was dirty)
    # go first, so they are the record kept, never their ".0" twin.
    dirty.sort(key=lambda s: cleaned[s.id] != s.matric_no)
    for s in dirty:
        new_matric = cleaned[s.id]
        original = kept.get(new_matric)
        if original is not None:
            # Same person uploaded twice: keep the clean record and fill in
            # anything it is missing from the duplicate.
            for field in MERGED_FIELDS:
                if _blank(getattr(original, field)) and not _blank(getattr(s, field)):
                    setattr(original, field, clean_number_text(getattr(s, field)))
            duplicates.append(s)
            continue
        s.matric_no = new_matric
        s.phone = clean_number_text(s.phone)
        kept[new_matric] = s
        to_update.append(s)
    Student.objects.bulk_update(to_update, ["matric_no", "phone"], batch_size=500)
    originals = {kept[cleaned[d.id]].id: kept[cleaned[d.id]] for d in duplicates}
    Student.objects.bulk_update(list(originals.values()), MERGED_FIELDS, batch_size=500)
    Student.objects.filter(id__in=[d.id for d in duplicates]).delete()
    if duplicates:
        print(
            f"\n  Deleted {len(duplicates)} duplicate student record(s) whose "
            "matric number only differed by a float tail; the clean record "
            "was kept. Regenerate the distribution."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("ems", "0016_timetable_seating_rule"),
    ]

    operations = [
        migrations.RunPython(clean, migrations.RunPython.noop),
    ]
