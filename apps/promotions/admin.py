"""Promotions admin configuration."""
from django.contrib import admin
from .models import (
    Promotion, PromotionUsage, LoyaltyProgram, LoyaltyTier,
    LoyaltyReward, CustomerLoyalty, LoyaltyTransaction
)


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'restaurant', 'discount_type', 'discount_value',
        'status', 'times_used', 'start_date', 'end_date'
    ]
    list_filter = ['status', 'discount_type', 'restaurant']
    search_fields = ['name', 'code']
    filter_horizontal = ['applicable_items', 'applicable_categories', 'applicable_locations']


@admin.register(PromotionUsage)
class PromotionUsageAdmin(admin.ModelAdmin):
    list_display = ['promotion', 'customer', 'order', 'discount_applied', 'created_at']
    list_filter = ['promotion', 'created_at']


class LoyaltyTierInline(admin.TabularInline):
    model = LoyaltyTier
    extra = 0


class LoyaltyRewardInline(admin.TabularInline):
    model = LoyaltyReward
    extra = 0


@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    list_display = ['restaurant', 'name', 'points_per_dollar', 'is_active']
    list_filter = ['is_active']
    inlines = [LoyaltyTierInline, LoyaltyRewardInline]


@admin.register(CustomerLoyalty)
class CustomerLoyaltyAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'program', 'points_balance', 'points_earned_total',
        'current_tier', 'joined_at'
    ]
    list_filter = ['program', 'current_tier']
    search_fields = ['customer__email', 'referral_code']


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ['membership', 'transaction_type', 'points', 'description', 'created_at']
    list_filter = ['transaction_type', 'created_at']
