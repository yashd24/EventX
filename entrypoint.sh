#!/bin/bash
set -e

echo "Waiting for database..."
echo $DB_HOST $DB_PORT
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done

echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server..."
exec "$@"
