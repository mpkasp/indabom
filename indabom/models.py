from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from djstripe.models import Customer, Subscription


class IndabomUserMeta(models.Model):
    user = models.OneToOneField(User, db_index=True, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)
    subscription = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.SET_NULL)
