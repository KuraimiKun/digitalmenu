"""Promotions URL patterns."""
from django.urls import path
from .views import (
    PromotionViewSet, LoyaltyProgramViewSet, LoyaltyRewardViewSet,
    CustomerLoyaltyView, RedeemRewardView, ApplyReferralView,
    PublicPromotionsView
)

urlpatterns = [
    # Public
    path('public/<slug:restaurant_slug>/', PublicPromotionsView.as_view(), name='public-promotions'),
    
    # Promotions
    path('<slug:restaurant_slug>/promotions/', PromotionViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='promotion-list'),
    path('<slug:restaurant_slug>/promotions/<uuid:pk>/', PromotionViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='promotion-detail'),
    path('<slug:restaurant_slug>/promotions/validate/', PromotionViewSet.as_view({
        'post': 'validate'
    }), name='promotion-validate'),
    path('<slug:restaurant_slug>/promotions/<uuid:pk>/usage/', PromotionViewSet.as_view({
        'get': 'usage_stats'
    }), name='promotion-usage'),
    
    # Loyalty Program
    path('<slug:restaurant_slug>/loyalty/', LoyaltyProgramViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='loyalty-program'),
    path('<slug:restaurant_slug>/loyalty/my-status/', CustomerLoyaltyView.as_view(), name='my-loyalty'),
    path('<slug:restaurant_slug>/loyalty/redeem/', RedeemRewardView.as_view(), name='redeem-reward'),
    path('<slug:restaurant_slug>/loyalty/referral/', ApplyReferralView.as_view(), name='apply-referral'),
    
    # Rewards
    path('<slug:restaurant_slug>/loyalty/<uuid:program_pk>/rewards/', LoyaltyRewardViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='loyalty-rewards'),
]
