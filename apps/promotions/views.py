"""Promotions views."""
from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.restaurants.models import Restaurant
from .models import (
    Promotion, PromotionUsage, LoyaltyProgram, LoyaltyTier,
    LoyaltyReward, CustomerLoyalty, LoyaltyTransaction
)
from .serializers import (
    PromotionSerializer, PromotionListSerializer, PromotionCreateSerializer,
    ValidatePromoCodeSerializer, PromotionUsageSerializer,
    LoyaltyProgramSerializer, LoyaltyTierSerializer, LoyaltyRewardSerializer,
    CustomerLoyaltySerializer, LoyaltyTransactionSerializer,
    RedeemRewardSerializer, ReferralSerializer
)


class PromotionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing promotions."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        if restaurant_slug:
            return Promotion.objects.filter(restaurant__slug=restaurant_slug)
        return Promotion.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PromotionListSerializer
        if self.action == 'create':
            return PromotionCreateSerializer
        return PromotionSerializer
    
    def perform_create(self, serializer):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        serializer.save(restaurant=restaurant)
    
    @action(detail=False, methods=['post'])
    def validate(self, request, restaurant_slug=None):
        """Validate a promo code."""
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        serializer = ValidatePromoCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['code']
        order_total = serializer.validated_data['order_total']
        order_type = serializer.validated_data.get('order_type')
        
        try:
            promotion = Promotion.objects.get(
                restaurant=restaurant,
                code__iexact=code
            )
        except Promotion.DoesNotExist:
            return Response(
                {'valid': False, 'error': 'Invalid promo code'},
                status=status.HTTP_200_OK
            )
        
        customer = request.user if request.user.is_authenticated else None
        can_use, error = promotion.can_use(customer, order_total, order_type)
        
        if not can_use:
            return Response(
                {'valid': False, 'error': error},
                status=status.HTTP_200_OK
            )
        
        discount = promotion.calculate_discount(order_total)
        
        return Response({
            'valid': True,
            'promotion': PromotionSerializer(promotion).data,
            'discount_amount': discount
        })
    
    @action(detail=True, methods=['get'])
    def usage_stats(self, request, restaurant_slug=None, pk=None):
        """Get usage statistics for a promotion."""
        promotion = self.get_object()
        
        usages = PromotionUsage.objects.filter(promotion=promotion)
        total_uses = usages.count()
        total_discount = sum(u.discount_applied for u in usages)
        
        return Response({
            'total_uses': total_uses,
            'total_discount_given': total_discount,
            'remaining_uses': promotion.usage_limit - total_uses if promotion.usage_limit else None
        })


class LoyaltyProgramViewSet(viewsets.ModelViewSet):
    """ViewSet for managing loyalty programs."""
    serializer_class = LoyaltyProgramSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        if restaurant_slug:
            return LoyaltyProgram.objects.filter(restaurant__slug=restaurant_slug)
        return LoyaltyProgram.objects.none()
    
    def perform_create(self, serializer):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        serializer.save(restaurant=restaurant)


class LoyaltyTierViewSet(viewsets.ModelViewSet):
    """ViewSet for managing loyalty tiers."""
    serializer_class = LoyaltyTierSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        program_id = self.kwargs.get('program_pk')
        return LoyaltyTier.objects.filter(program_id=program_id)
    
    def perform_create(self, serializer):
        program_id = self.kwargs.get('program_pk')
        program = get_object_or_404(LoyaltyProgram, pk=program_id)
        serializer.save(program=program)


class LoyaltyRewardViewSet(viewsets.ModelViewSet):
    """ViewSet for managing loyalty rewards."""
    serializer_class = LoyaltyRewardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        program_id = self.kwargs.get('program_pk')
        return LoyaltyReward.objects.filter(program_id=program_id)
    
    def perform_create(self, serializer):
        program_id = self.kwargs.get('program_pk')
        program = get_object_or_404(LoyaltyProgram, pk=program_id)
        serializer.save(program=program)


class CustomerLoyaltyView(generics.RetrieveAPIView):
    """Get customer's loyalty status."""
    serializer_class = CustomerLoyaltySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        
        program = get_object_or_404(LoyaltyProgram, restaurant=restaurant)
        
        membership, created = CustomerLoyalty.objects.get_or_create(
            customer=self.request.user,
            program=program
        )
        
        # Add signup bonus if new
        if created and program.signup_bonus > 0:
            membership.add_points(program.signup_bonus, 'Signup bonus')
        
        return membership


class RedeemRewardView(generics.GenericAPIView):
    """Redeem a loyalty reward."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, restaurant_slug):
        serializer = RedeemRewardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        program = get_object_or_404(LoyaltyProgram, restaurant=restaurant)
        
        membership = get_object_or_404(
            CustomerLoyalty,
            customer=request.user,
            program=program
        )
        
        reward = get_object_or_404(
            LoyaltyReward,
            pk=serializer.validated_data['reward_id'],
            program=program,
            is_active=True
        )
        
        # Check if reward is available
        if reward.quantity_available and reward.quantity_redeemed >= reward.quantity_available:
            return Response(
                {'error': 'Reward is no longer available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if reward.valid_until and reward.valid_until < timezone.now():
            return Response(
                {'error': 'Reward has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check points
        if membership.points_balance < reward.points_required:
            return Response(
                {'error': 'Insufficient points'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Redeem
        membership.redeem_points(reward.points_required, f'Redeemed: {reward.name}')
        reward.quantity_redeemed += 1
        reward.save()
        
        return Response({
            'success': True,
            'message': f'Successfully redeemed {reward.name}',
            'remaining_points': membership.points_balance
        })


class ApplyReferralView(generics.GenericAPIView):
    """Apply a referral code."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, restaurant_slug):
        serializer = ReferralSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
        program = get_object_or_404(LoyaltyProgram, restaurant=restaurant)
        
        # Get referrer
        try:
            referrer_membership = CustomerLoyalty.objects.get(
                referral_code=serializer.validated_data['referral_code'],
                program=program
            )
        except CustomerLoyalty.DoesNotExist:
            return Response(
                {'error': 'Invalid referral code'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already a member
        membership, created = CustomerLoyalty.objects.get_or_create(
            customer=request.user,
            program=program
        )
        
        if not created and membership.referred_by:
            return Response(
                {'error': 'Referral already applied'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if referrer_membership.customer == request.user:
            return Response(
                {'error': 'Cannot refer yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Apply referral
        membership.referred_by = referrer_membership
        membership.save()
        
        # Add bonus points
        if program.referral_bonus > 0:
            membership.add_points(program.referral_bonus, 'Referral bonus')
            referrer_membership.add_points(program.referral_bonus, f'Referred {request.user.email}')
        
        return Response({
            'success': True,
            'message': 'Referral applied successfully',
            'bonus_points': program.referral_bonus
        })


class PublicPromotionsView(generics.ListAPIView):
    """Public list of active promotions."""
    serializer_class = PromotionListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        restaurant_slug = self.kwargs.get('restaurant_slug')
        now = timezone.now()
        return Promotion.objects.filter(
            restaurant__slug=restaurant_slug,
            status=Promotion.Status.ACTIVE,
            start_date__lte=now,
            end_date__gte=now
        )
