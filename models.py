from django.db import models
from django.core.exceptions import FieldError
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor
from django.db.models.expressions import Combinable

from functools import wraps

import uuid


def disable_for_loaddata(signal_handler):
    """
    Decorator that turns off signal handlers when loading fixture data.
    """

    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        if kwargs["raw"]:
            return
        signal_handler(*args, **kwargs)

    return wrapper


OperationAPIState = models.TextChoices("State", "NOT_STARTED RUNNING SUCCEEDED FAILED")


class APICounterField(models.PositiveIntegerField):
    """
    A `PositiveIntegerField` for a counter field.
    """

    def clean(self, value, model_instance):
        """Convert the value's type and run validation."""

        # Add support for F() expressions
        if isinstance(value, Combinable):
            return value

        return super().clean(value, model_instance)


class APIModel(models.Model):
    """
    Intentionally simple parent class for all API models.
    """

    DISABLE_UPDATE_FIELDS = tuple(["uuid", "created_at"])
    AUTO_UPDATE_FIELDS = tuple(["last_modified_at"])

    # 通用唯一标识符
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    # 创建时间 ISO 标准字符串
    created_at = models.DateTimeField(auto_now_add=True)
    # 最近修改时间 ISO 标准字符串
    last_modified_at = models.DateTimeField(auto_now=True)
    # 是否被标记为`已删除`
    is_deleted = models.BooleanField(default=False)

    def update(self, **kwargs):
        """Update the object based on the `kwargs` provided."""

        update_fields = [field for field in self.AUTO_UPDATE_FIELDS]
        for field, value in kwargs.items():
            if field in self.DISABLE_UPDATE_FIELDS:
                raise FieldError(f"The field {field} is a disable update field.")

            # models.ForeignKey
            # TODO: models.OneToOneField
            # TODO: models.ManyToManyField
            if isinstance(
                getattr(self._meta.concrete_model, field), ForwardManyToOneDescriptor
            ):
                field = f"{field}_id"

            setattr(self, field, value)
            update_fields.append(field)

        self.full_clean()
        self.save(update_fields=update_fields, force_update=True)
        self.refresh_from_db()

    def delete(self, using=None, keep_parents=False):
        """Delete the object by just set its `is_deleted` field to True."""

        self.update(is_deleted=True)

    class Meta:
        abstract = True
