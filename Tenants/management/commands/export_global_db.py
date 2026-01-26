import os
import subprocess
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Export the entire database (including all schemas) using pg_dump'

    def handle(self, *args, **options):
        db_settings = settings.DATABASES['default']
        db_name = db_settings['NAME']
        db_user = db_settings['USER']
        db_password = db_settings['PASSWORD']
        db_host = db_settings['HOST']
        db_port = db_settings['PORT']

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_global_{timestamp}.dump"
        
        # Env vars for password safety
        env = os.environ.copy()
        env['PGPASSWORD'] = str(db_password)

        cmd = [
            'pg_dump',
            '-h', str(db_host),
            '-p', str(db_port),
            '-U', str(db_user),
            '-F', 'c',  # Custom format (compressed)
            '-b',       # Include large objects
            '-v',       # Verbose
            '-f', filename,
            str(db_name)
        ]

        self.stdout.write(f"Starting export of {db_name} to {filename}...")
        
        try:
            subprocess.run(cmd, env=env, check=True)
            self.stdout.write(self.style.SUCCESS(f"Successfully exported to {filename}"))
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f"Export failed: {e}"))
