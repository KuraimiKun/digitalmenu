"""Promotions serializers."""
from rest_framework import serializers
from .models import (
    Promotion, PromotionUsage, LoyaltyProgram, LoyaltyTier,
    LoyaltyReward, CustomerLoyalty, LoyaltyTransaction
)


class PromotionSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Promotion
        fields = [
            'id', 'name', 'description', 'code',
            'discount_type', 'discount_value',
            'minimum_order', 'maximum_discount',
            'usage_limit', 'usage_limit_per_customer', 'times_used',
            'start_date', 'end_date', 'status', 'is_valid',
            'apply_to_dine_in', 'apply_to_takeout', 'apply_to_delivery',
            'first_order_only', 'created_at'
        ]
        read_only_fields = ['id', 'times_used', 'is_valid', 'created_at']


class PromotionListSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Promotion
        fields = [
            'id', 'name', 'code', 'discount_type', 'discount_value',
            'status', 'is_valid', 'start_date', 'end_date'
        ]


class PromotionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = [
            'name', 'description', 'code', 'discount_type', 'discount_value',
            'minimum_order', 'maximum_discount', 'usage_limit',
            'usage_limit_per_customer', 'start_date', 'end_date',
            'applicable_items', 'applicable_categories', 'applicable_locations',
            'apply_to_dine_in', 'apply_to_takeout', 'apply_to_delivery',
            'first_order_only', 'free_item', 'buy_quantity', 'get_quantity'
        ]


class ValidatePromoCodeSerializer(serializers.Serializer):
    code = serializers.CharField()
    order_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    order_type = serializers.ChoiceField(
        choices=['dine_in', 'takeout', 'delivery'],
        required=False
    )


class PromotionUsageSerializer(serializers.ModelSerializer):
    promotion_name = serializers.CharField(source='promotion.name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = PromotionUsage
        fields = [
            'id', 'promotion', 'promotion_name', 'order',
            'order_number', 'discount_applied', 'created_at'
        ]


class LoyaltyTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyTier
        fields = [
            'id', 'name', 'min_points', 'color', 'icon',
            'points_multiplier', 'discount_percentage',
            'free_delivery', 'priority_support', 'exclusive_items', 'position'
        ]


class LoyaltyRewardSerializer(serializers.ModelSerializer):
    reward_item_name = serializers.CharField(source='reward_item.name', read_only=True)
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = LoyaltyReward
        fields = [
            'id', 'name', 'description', 'image', 'points_required',
            'reward_type', 'reward_item', 'reward_item_name',
            'discount_value', 'discount_type', 'is_active',
            'quantity_available', 'quantity_redeemed', 'valid_until',
            'is_available'
        ]
    
    def get_is_available(self, obj):
        if not obj.is_active:
            return False
        if obj.quantity_available and obj.quantity_redeemed >= obj.quantity_available:
            return False
        if obj.valid_until and obj.valid_until < timezone.now():
            return False
        return True


class LoyaltyProgramSerializer(serializers.ModelSerializer):
    tiers = LoyaltyTierSerializer(many=True, read_only=True)
    rewards = LoyaltyRewardSerializer(many=True, read_only=True)
    
    class Meta:
        model = LoyaltyProgram
        fields = [
            'id', 'name', 'description',
            'points_per_dollar', 'points_per_visit',
            'signup_bonus', 'referral_bonus', 'birthday_bonus',
            'is_active', 'tiers', 'rewards'
        ]


class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = LoyaltyTransaction
        fields = [
            'id', 'transaction_type', 'points', 'description',
            'order', 'order_number', 'created_at'
        ]


class CustomerLoyaltySerializer(serializers.ModelSerializer):
    program = LoyaltyProgramSerializer(read_only=True)
    current_tier = LoyaltyTierSerializer(read_only=True)
    recent_transactions = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomerLoyalty
        fields = [
            'id', 'program', 'points_balance', 'points_earned_total',
            'points_redeemed_total', 'current_tier', 'referral_code',
            'joined_at', 'recent_transactions'
        ]
    
    def get_recent_transactions(self, obj):
        transactions = obj.transactions.all()[:10]
        return LoyaltyTransactionSerializer(transactions, many=True).data


class RedeemRewardSerializer(serializers.Serializer):
    reward_id = serializers.UUIDField()


class ReferralSerializer(serializers.Serializer):
    referral_code = serializers.CharField()
