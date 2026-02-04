"""Menu admin configuration."""
from django.contrib import admin
from .models import (
    Menu, Category, MenuItem, MenuItemVariant,
    ModifierGroup, Modifier, MenuItemModifierGroup,
    MenuTheme, MenuTranslation, CategoryTranslation, MenuItemTranslation
)


class CategoryInline(admin.TabularInline):
    model = Category
    extra = 0
    fields = ['name', 'position', 'is_visible']


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0
    fields = ['name', 'price', 'status', 'position', 'is_featured']


class MenuItemVariantInline(admin.TabularInline):
    model = MenuItemVariant
    extra = 0


class ModifierInline(admin.TabularInline):
    model = Modifier
    extra = 0


@admin.register(MenuTheme)
class MenuThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_premium', 'is_active']
    list_filter = ['is_premium', 'is_active']
    search_fields = ['name']


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'menu_type', 'status', 'is_active', 'position']
    list_filter = ['status', 'menu_type', 'is_active', 'restaurant']
    search_fields = ['name', 'restaurant__name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CategoryInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'menu', 'position', 'is_visible']
    list_filter = ['is_visible', 'menu__restaurant']
    search_fields = ['name', 'menu__name']
    inlines = [MenuItemInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'status', 'is_featured', 'position']
    list_filter = ['status', 'is_featured', 'is_vegetarian', 'is_vegan', 'category__menu__restaurant']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [MenuItemVariantInline]


@admin.register(ModifierGroup)
class ModifierGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'selection_type', 'is_required']
    list_filter = ['selection_type', 'is_required', 'restaurant']
    search_fields = ['name']
    inlines = [ModifierInline]


@admin.register(Modifier)
class ModifierAdmin(admin.ModelAdmin):
    list_display = ['name', 'group', 'price', 'is_available']
    list_filter = ['is_available', 'group']
    search_fields = ['name']
