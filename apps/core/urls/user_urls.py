"""User management URL patterns."""
from django.urls import path
from ..views import (
    UserProfileView,
    SubscriptionPlanListView,
    UserSubscriptionView,
    current_user_restaurants,
)

urlpatterns = [
    path('me/', UserProfileView.as_view(), name='user_profile'),
    path('me/restaurants/', current_user_restaurants, name='user_restaurants'),
    path('me/subscription/', UserSubscriptionView.as_view(), name='user_subscription'),
    path('plans/', SubscriptionPlanListView.as_view(), name='subscription_plans'),
]
