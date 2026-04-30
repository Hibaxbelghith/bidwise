from functools import reduce
from operator import or_

from django.db.models import Q


REMOVED_SOURCE_NAMES = (
    "HiInterns",
    "TunsieTenders",
    "TunisieTenders",
    "TunisieTravail",
)

REMOVED_SOURCE_KEYS = tuple(name.lower() for name in REMOVED_SOURCE_NAMES)


def removed_source_q(field_name):
    return reduce(
        or_,
        (Q(**{f"{field_name}__iexact": source_name}) for source_name in REMOVED_SOURCE_NAMES),
        Q(),
    )

