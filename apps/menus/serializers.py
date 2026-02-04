"""Menu serializers with drag-and-drop builder support."""
from rest_framework import serializers
from .models import (
    Menu, Category, MenuItem, MenuItemVariant,
    ModifierGroup, Modifier, MenuItemModifierGroup,
    MenuTheme, MenuTranslation, CategoryTranslation, MenuItemTranslation
)


class MenuThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuTheme
        fields = [
            'id', 'name', 'slug', 'description', 'preview_image',
            'styles', 'primary_color', 'secondary_color',
            'background_color', 'text_color', 'accent_color',
            'heading_font', 'body_font', 'is_premium'
        ]


class ModifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modifier
        fields = [
            'id', 'name', 'price', 'is_default', 'is_available', 'position'
        ]


class ModifierGroupSerializer(serializers.ModelSerializer):
    modifiers = ModifierSerializer(many=True, read_only=True)
    
    class Meta:
        model = ModifierGroup
        fields = [
            'id', 'name', 'description', 'selection_type',
            'is_required', 'min_selections', 'max_selections',
            'modifiers', 'position'
        ]


class MenuItemVariantSerializer(serializers.ModelSerializer):
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = MenuItemVariant
        fields = [
            'id', 'name', 'price_adjustment', 'total_price',
            'is_default', 'is_available', 'position'
        ]


class MenuItemModifierGroupSerializer(serializers.ModelSerializer):
    group = ModifierGroupSerializer(read_only=True)
    group_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = MenuItemModifierGroup
        fields = [
            'id', 'group', 'group_id', 'is_required',
            'min_selections', 'max_selections', 'position'
        ]


class MenuItemSerializer(serializers.ModelSerializer):
    variants = MenuItemVariantSerializer(many=True, read_only=True)
    modifier_groups = MenuItemModifierGroupSerializer(many=True, read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'slug', 'description',
            'price', 'compare_price', 'currency',
            'image', 'thumbnail', 'gallery',
            'status', 'is_featured', 'is_new', 'is_popular',
            'is_spicy', 'spicy_level',
            'is_vegetarian', 'is_vegan', 'is_gluten_free',
            'is_halal', 'is_kosher', 'allergens',
            'calories', 'nutritional_info', 'prep_time',
            'track_inventory', 'inventory_count',
            'position', 'tags',
            'is_on_sale', 'discount_percentage',
            'variants', 'modifier_groups',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']


class MenuItemListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for menu item lists."""
    
    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'slug', 'price', 'image',
            'status', 'is_featured', 'position'
        ]


class CategorySerializer(serializers.ModelSerializer):
    items = MenuItemListSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(source='items.count', read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'image',
            'position', 'is_visible',
            'available_from', 'available_until',
            'items', 'item_count'
        ]
        read_only_fields = ['id', 'slug']


class CategoryListSerializer(serializers.ModelSerializer):
    """Lightweight category serializer."""
    item_count = serializers.IntegerField(source='items.count', read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'position', 'is_visible', 'item_count']


class MenuSerializer(serializers.ModelSerializer):
    categories = CategoryListSerializer(many=True, read_only=True)
    theme = MenuThemeSerializer(read_only=True)
    theme_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Menu
        fields = [
            'id', 'name', 'slug', 'description',
            'menu_type', 'status',
            'theme', 'theme_id', 'custom_styles',
            'header_image', 'background_image',
            'is_active', 'available_from', 'available_until', 'available_days',
            'position', 'layout_config',
            'categories', 'locations',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']


class MenuListSerializer(serializers.ModelSerializer):
    """Lightweight menu serializer for lists."""
    category_count = serializers.IntegerField(source='categories.count', read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Menu
        fields = [
            'id', 'name', 'slug', 'menu_type', 'status',
            'is_active', 'position', 'category_count', 'item_count'
        ]
    
    def get_item_count(self, obj):
        return MenuItem.objects.filter(category__menu=obj).count()


class MenuCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating menus."""
    
    class Meta:
        model = Menu
        fields = [
            'name', 'description', 'menu_type',
            'theme', 'header_image', 'background_image',
            'available_from', 'available_until', 'available_days',
            'locations'
        ]


class MenuBuilderSerializer(serializers.ModelSerializer):
    """Full serializer for menu builder with nested data."""
    categories = CategorySerializer(many=True, read_only=True)
    theme = MenuThemeSerializer(read_only=True)
    
    class Meta:
        model = Menu
        fields = [
            'id', 'name', 'slug', 'description',
            'menu_type', 'status',
            'theme', 'custom_styles',
            'header_image', 'background_image',
            'is_active', 'available_from', 'available_until', 'available_days',
            'position', 'layout_config',
            'categories'
        ]


class MenuReorderSerializer(serializers.Serializer):
    """Serializer for reordering menu items (drag-and-drop)."""
    items = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField())
    )
    
    def validate_items(self, value):
        for item in value:
            if 'id' not in item or 'position' not in item:
                raise serializers.ValidationError(
                    "Each item must have 'id' and 'position'"
                )
        return value


class CategoryReorderSerializer(serializers.Serializer):
    """Serializer for reordering categories."""
    categories = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField())
    )


class MenuItemBulkUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating menu items."""
    item_ids = serializers.ListField(child=serializers.UUIDField())
    action = serializers.ChoiceField(choices=[
        'activate', 'deactivate', 'feature', 'unfeature',
        'mark_available', 'mark_out_of_stock', 'delete'
    ])


class MenuPublishSerializer(serializers.Serializer):
    """Serializer for publishing a menu."""
    locations = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )


# Translation serializers
class MenuTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuTranslation
        fields = ['id', 'language', 'name', 'description']


class CategoryTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryTranslation
        fields = ['id', 'language', 'name', 'description']


class MenuItemTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItemTranslation
        fields = ['id', 'language', 'name', 'description']
