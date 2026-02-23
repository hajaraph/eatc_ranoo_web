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

    # Step 1: Check if format is selected, otherwise render selection page
    export_format = request.GET.get('format')
    if not export_format:
        from django.shortcuts import render
        return render(request, 'admin/db_export_options.html')

    db_settings = settings.DATABASES['default']
    db_name = db_settings['NAME']
    db_user = db_settings['USER']
    db_password = db_settings['PASSWORD']
    db_host = db_settings['HOST']
    db_port = db_settings['PORT']

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Configure extension and flags based on format
    if export_format == 'sql':
        filename = f"backup_global_{timestamp}.sql"
        format_flag = '-Fp' # Plain text
    else:
        filename = f"backup_global_{timestamp}.dump"
        format_flag = '-Fc' # Custom (compressed)

    # Prepare environment with password
    env = os.environ.copy()
    env['PGPASSWORD'] = str(db_password)

    # Try to find pg_dump path
    pg_dump_path = 'pg_dump'
    possible_paths = [
        r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\14\bin\pg_dump.exe",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            pg_dump_path = path
            break

    # Command to dump to stdout
    cmd = [
        pg_dump_path,
        '-h', str(db_host),
        '-p', str(db_port),
        '-U', str(db_user),
        format_flag,
        '-b',       # Include large objects (if supported by format)
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
        subprocess.run([pg_dump_path, '--version'], capture_output=True, check=True)
    except FileNotFoundError:
        return JsonResponse({'error': f'{pg_dump_path} introuvable sur le serveur.'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Erreur verification pg_dump: {str(e)}'}, status=500)

    response = StreamingHttpResponse(file_iterator(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
