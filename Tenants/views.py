import os
import subprocess
from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.http import StreamingHttpResponse, HttpResponseForbidden, JsonResponse
from django.utils.translation import gettext as _

def is_superuser(user):
    return user.is_superuser

@user_passes_test(is_superuser)
def export_database(request):
    """
    View to stream a global database dump (pg_dump) to the browser.
    Restricted to superusers.
    """
    if not request.user.is_superuser:
        return HttpResponseForbidden(_("Vous n'avez pas la permission d'effectuer cette action."))

    db_settings = settings.DATABASES['default']
    db_name = db_settings['NAME']
    db_user = db_settings['USER']
    db_password = db_settings['PASSWORD']
    db_host = db_settings['HOST']
    db_port = db_settings['PORT']

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"backup_global_{timestamp}.dump"

    # Prepare environment with password
    env = os.environ.copy()
    env['PGPASSWORD'] = str(db_password)

    # Command to dump to stdout
    cmd = [
        'pg_dump',
        '-h', str(db_host),
        '-p', str(db_port),
        '-U', str(db_user),
        '-F', 'c',  # Custom format (compressed)
        '-b',       # Include large objects
        str(db_name)
    ]

    def file_iterator(chunk_size=8192):
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            while True:
                chunk = process.stdout.read(chunk_size)
                if not chunk:
                    break
                yield chunk
                
            process.stdout.close()
            return_code = process.wait()
            
            if return_code != 0:
                error_output = process.stderr.read().decode('utf-8')
                print(f"Export Error (pg_dump): {error_output}")
                # In a real scenario, we might want to inject an error into the stream or log it.
                # Since headers are sent, we can only break.
                
        except FileNotFoundError:
            print("Error: pg_dump not found in PATH.")
            yield b"Error: pg_dump not found. Please install PostgreSQL tools."
        except Exception as e:
            print(f"Unexpected Error during export: {e}")
            yield f"Error: {e}".encode('utf-8')

    try:
        # Test if pg_dump exists before starting stream (optional but safer)
        subprocess.run(['pg_dump', '--version'], capture_output=True, check=True)
    except FileNotFoundError:
        return JsonResponse({'error': 'pg_dump introuvable sur le serveur.'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Erreur verification pg_dump: {str(e)}'}, status=500)

    response = StreamingHttpResponse(file_iterator(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
