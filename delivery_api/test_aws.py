import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'delivery_api.settings')
django.setup()

from products.models import Product
from users.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

print("Iniciando prueba de AWS S3...")

# 1. Verificar variables de entorno
print(f"AWS_BUCKET: {os.getenv('AWS_STORAGE_BUCKET_NAME')}")
if not os.getenv('AWS_ACCESS_KEY_ID'):
    print("❌ ERROR: AWS_ACCESS_KEY_ID no está configurado en el .env")

# 2. Buscar o crear un producto
product = Product.objects.first()

if not product:
    print("No hay productos. Creando uno de prueba...")
    restaurante = User.objects.filter(user_type='restaurant').first()
    if restaurante:
        product = Product.objects.create(
            restaurant=restaurante,
            name="Producto de Prueba AWS",
            description="Prueba",
            price=10.00
        )
        print("✅ Producto creado.")
    else:
        print("❌ No hay restaurantes para asignar el producto.")
        exit()

# 3. Subir la imagen
if product:
    print("Subiendo imagen a S3...")
    image_content = b'fake image data'
    image_file = SimpleUploadedFile('test_aws.jpg', image_content, content_type='image/jpeg')
    
    product.image.save('test_aws.jpg', image_file)
    print("✅ Imagen subida con éxito.")
    print("URL de la imagen:", product.image.url)