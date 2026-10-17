#!/usr/bin/env bash
# Script de compilación y preparación para Render.com
set -o errexit

echo "==> Instalando dependencias de Python..."
pip install -r requirements.txt

echo "==> Recolectando archivos estáticos con WhiteNoise..."
python manage.py collectstatic --no-input

echo "==> Aplicando migraciones de base de datos..."
python manage.py migrate

echo "==> Poblando base de datos con demo completa (sucursales, barberos, servicios, inventario y citas)..."
python manage.py cargar_demo

echo "==> Build y carga de demo finalizados con éxito."
