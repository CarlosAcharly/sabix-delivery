#!/bin/bash

echo "=================================================="
echo "🚀 Actualizando Delivery API en VPS"
echo "=================================================="
echo ""

# ==================================================
# Configuración
# ==================================================
APP_PATH="apps/delivery-api"
APP_NAME="Delivery API"
SERVICE_NAME="gunicorn_delivery"

# ==================================================
# Función para verificar errores
# ==================================================
check_error() {
    if [ $? -ne 0 ]; then
        echo "❌ Error: $1"
        exit 1
    fi
}

# ==================================================
# Actualizar aplicación
# ==================================================
echo "📦 Actualizando $APP_NAME..."

# Navegar al proyecto
cd ~/$APP_PATH
check_error "No se pudo acceder a $APP_PATH"

# Activar entorno virtual
source venv/bin/activate
check_error "No se pudo activar el entorno virtual"

# Descargar cambios de GitHub
echo "📥 Descargando cambios de GitHub..."
git pull origin main
check_error "Error al hacer git pull"

# Instalar nuevas dependencias
echo "📦 Instalando dependencias..."
pip install -r requirements.txt
check_error "Error al instalar dependencias"

# Crear y aplicar migraciones
echo "🔄 Creando y aplicando migraciones..."
python manage.py makemigrations
python manage.py migrate
check_error "Error al aplicar migraciones"

# Recopilar archivos estáticos
echo "📁 Recopilando archivos estáticos..."
python manage.py collectstatic --noinput
check_error "Error al recopilar archivos estáticos"

# Reiniciar Gunicorn
echo "🔄 Reiniciando servicio $SERVICE_NAME..."
sudo systemctl restart $SERVICE_NAME
check_error "Error al reiniciar Gunicorn"

# Recargar Nginx
echo "🔄 Recargando Nginx..."
sudo systemctl reload nginx

echo ""
echo "=================================================="
echo "✅ $APP_NAME actualizado exitosamente"
echo "=================================================="

# Verificación final
echo ""
echo "📊 Estado de servicios:"
sudo systemctl status $SERVICE_NAME nginx --no-pager | grep "Active:"

echo ""
echo "🌐 Prueba de conexión:"
curl -I https://sabi-x-delivery.duckdns.org 2>/dev/null | head -n 1

echo ""
echo "✅ Actualización completada!"
echo "=================================================="
