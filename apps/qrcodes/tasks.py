"""QR Code async tasks."""
import zipfile
from io import BytesIO
from celery import shared_task
from django.core.files.base import ContentFile


@shared_task
def generate_qr_batch(batch_id):
    """Generate a batch of QR codes."""
    from .models import QRCode, QRCodeBatch
    from apps.restaurants.models import Table
    
    try:
        batch = QRCodeBatch.objects.select_related(
            'restaurant', 'location', 'design'
        ).get(pk=batch_id)
    except QRCodeBatch.DoesNotExist:
        return
    
    batch.status = 'generating'
    batch.save()
    
    try:
        qr_codes = []
        
        if batch.generate_for_tables:
            # Generate for all tables at location
            tables = Table.objects.filter(
                location=batch.location,
                is_active=True
            )
            
            for table in tables:
                qr_code = QRCode.objects.create(
                    restaurant=batch.restaurant,
                    location=batch.location,
                    name=f"{batch.name} - Table {table.number}",
                    qr_type='table',
                    table=table,
                    design=batch.design,
                )
                qr_code.generate_qr_image()
                qr_code.save()
                qr_codes.append(qr_code)
        else:
            # Generate numbered QR codes
            for i in range(batch.count):
                number = batch.start_number + i
                name = f"{batch.prefix}{number}" if batch.prefix else f"{batch.name} #{number}"
                
                qr_code = QRCode.objects.create(
                    restaurant=batch.restaurant,
                    location=batch.location,
                    name=name,
                    qr_type=batch.qr_type,
                    design=batch.design,
                )
                qr_code.generate_qr_image()
                qr_code.save()
                qr_codes.append(qr_code)
        
        # Create ZIP file with all QR codes
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for qr_code in qr_codes:
                if qr_code.qr_image:
                    # Add QR code image to ZIP
                    filename = f"{qr_code.name.replace(' ', '_')}.png"
                    zf.writestr(filename, qr_code.qr_image.read())
        
        zip_buffer.seek(0)
        
        # Save ZIP file
        batch.download_file.save(
            f"qr_batch_{batch.id}.zip",
            ContentFile(zip_buffer.getvalue()),
            save=False
        )
        
        batch.status = 'completed'
        batch.generated_count = len(qr_codes)
        batch.save()
        
    except Exception as e:
        batch.status = 'failed'
        batch.save()
        raise
