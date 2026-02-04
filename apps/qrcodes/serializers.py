"""QR Code serializers."""
from rest_framework import serializers
from .models import QRCodeDesign, QRCode, QRCodeScan, QRCodeBatch


class QRCodeDesignSerializer(serializers.ModelSerializer):
    """Serializer for QR code designs."""
    
    class Meta:
        model = QRCodeDesign
        fields = [
            'id', 'restaurant', 'name', 'fill_color', 'back_color',
            'logo', 'logo_size_percent', 'border_size', 'error_correction',
            'box_size', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'restaurant', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['restaurant'] = self.context['restaurant']
        return super().create(validated_data)


class QRCodeSerializer(serializers.ModelSerializer):
    """Serializer for QR codes."""
    
    qr_type_display = serializers.CharField(source='get_qr_type_display', read_only=True)
    target_url = serializers.CharField(source='get_target_url', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    menu_name = serializers.CharField(source='menu.name', read_only=True)
    table_number = serializers.CharField(source='table.number', read_only=True)
    design_name = serializers.CharField(source='design.name', read_only=True)
    
    class Meta:
        model = QRCode
        fields = [
            'id', 'restaurant', 'location', 'location_name', 'name',
            'qr_type', 'qr_type_display', 'menu', 'menu_name', 'table',
            'table_number', 'custom_url', 'wifi_ssid', 'wifi_password',
            'wifi_encryption', 'design', 'design_name', 'qr_image',
            'qr_image_svg', 'short_code', 'target_url', 'scan_count',
            'last_scanned_at', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'restaurant', 'qr_image', 'qr_image_svg', 'short_code',
            'scan_count', 'last_scanned_at', 'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        qr_type = data.get('qr_type', 'menu')
        
        if qr_type == 'menu' and not data.get('menu'):
            raise serializers.ValidationError({
                'menu': 'Menu is required for menu QR codes'
            })
        elif qr_type == 'table' and not data.get('table'):
            raise serializers.ValidationError({
                'table': 'Table is required for table QR codes'
            })
        elif qr_type == 'custom' and not data.get('custom_url'):
            raise serializers.ValidationError({
                'custom_url': 'Custom URL is required for custom QR codes'
            })
        elif qr_type == 'wifi' and not data.get('wifi_ssid'):
            raise serializers.ValidationError({
                'wifi_ssid': 'WiFi SSID is required for WiFi QR codes'
            })
        
        return data
    
    def create(self, validated_data):
        validated_data['restaurant'] = self.context['restaurant']
        qr_code = super().create(validated_data)
        qr_code.generate_qr_image()
        qr_code.save()
        return qr_code


class QRCodeScanSerializer(serializers.ModelSerializer):
    """Serializer for QR code scans."""
    
    class Meta:
        model = QRCodeScan
        fields = [
            'id', 'qr_code', 'user_agent', 'device_type', 'browser', 'os',
            'ip_address', 'country', 'city', 'scanned_at'
        ]


class QRCodeBatchSerializer(serializers.ModelSerializer):
    """Serializer for QR code batches."""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    qr_type_display = serializers.CharField(source='get_qr_type_display', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = QRCodeBatch
        fields = [
            'id', 'restaurant', 'location', 'location_name', 'name',
            'qr_type', 'qr_type_display', 'design', 'generate_for_tables',
            'prefix', 'start_number', 'count', 'status', 'status_display',
            'generated_count', 'download_file', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'restaurant', 'status', 'generated_count', 'download_file',
            'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        validated_data['restaurant'] = self.context['restaurant']
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class QRCodeAnalyticsSerializer(serializers.Serializer):
    """Serializer for QR code analytics."""
    
    total_scans = serializers.IntegerField()
    unique_devices = serializers.IntegerField()
    scans_by_date = serializers.ListField(child=serializers.DictField())
    scans_by_device = serializers.DictField()
    scans_by_country = serializers.DictField()
    top_hours = serializers.ListField(child=serializers.DictField())


class PublicQRCodeSerializer(serializers.ModelSerializer):
    """Serializer for public QR code access."""
    
    target_url = serializers.CharField(source='get_target_url', read_only=True)
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    restaurant_logo = serializers.ImageField(source='restaurant.logo', read_only=True)
    
    class Meta:
        model = QRCode
        fields = [
            'id', 'name', 'qr_type', 'target_url', 'restaurant_name',
            'restaurant_logo'
        ]
