"""Core signals for user-related events."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Handle post-user creation tasks."""
    if created:
        # Additional user setup can be done here
        pass
