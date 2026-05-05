from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflict."
    default_code = "conflict"


def handler(exc, context):
    """Uniform error envelope: {detail, errors?}.

    `detail` is a single human-readable message, `errors` (optional) is a
    field -> list[message] map suitable for react-hook-form `setError`.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    if isinstance(data, dict):
        if "detail" in data and len(data) == 1:
            response.data = {"detail": str(data["detail"])}
        else:
            field_errors = {}
            non_field = []
            for key, value in data.items():
                if isinstance(value, list):
                    str_values = [str(v) for v in value]
                else:
                    str_values = [str(value)]
                if key in ("non_field_errors", "detail"):
                    non_field.extend(str_values)
                else:
                    field_errors[key] = str_values
            detail = (
                "; ".join(non_field)
                if non_field
                else "Validation failed."
            )
            envelope = {"detail": detail}
            if field_errors:
                envelope["errors"] = field_errors
            response.data = envelope
    elif isinstance(data, list):
        response.data = {"detail": "; ".join(str(item) for item in data)}
    else:
        response.data = {"detail": str(data)}

    return response
