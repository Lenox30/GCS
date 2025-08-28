from flask import Flask
import redis
import time
import os
from featureflags.client import CfClient
from featureflags.evaluations.auth_target import Target

app = Flask(__name__)

# Configuración de Harness Feature Flags
HARNESS_SDK_KEY = os.getenv('HARNESS_SDK_KEY', 'tu_sdk_key_aqui')
client = CfClient(HARNESS_SDK_KEY)

def wait_for_redis():
    """Esperar a que Redis esté disponible"""
    max_retries = 10
    retry_delay = 1
    
    for i in range(max_retries):
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            redis_client.ping()
            print("✅ Redis conectado exitosamente")
            return redis_client
        except redis.ConnectionError:
            print(f"⏳ Esperando por Redis... ({i+1}/{max_retries})")
            time.sleep(retry_delay)
    
    raise Exception("❌ No se pudo conectar a Redis")

def get_styling_based_on_visits(visitas):
    """Determinar targeting basado en número de visitas"""
    target = Target(
        identifier=f"visit_{visitas}",
        name=f"Visit {visitas}",
        attributes={"visit_count": visitas}
    )
    
    # Feature flag para dark launch
    is_dark_launch_active = client.bool_variation('dark_launch_styling', target, False)
    
    if not is_dark_launch_active:
        # Estilo original (OFF)
        return {
            'background_color': '#f0f0f0',
            'text_color': '#333333',
            'accent_color': '#007bff',
            'status': 'Original Design'
        }
    else:
        # Nuevo estilo (ON) - más llamativo
        return {
            'background_color': '#1a1a1a',
            'text_color': '#00ff88',
            'accent_color': '#ff6b35',
            'status': '🚀 Dark Launch Active!'
        }

@app.route('/')
def contador_visitas():
    try:
        redis_client = wait_for_redis()
        visitas = redis_client.incr('visitas')
        
        # Obtener estilo basado en feature flag y visitas
        styling = get_styling_based_on_visits(visitas)
        
        return f'''
        <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        text-align: center;
                        padding: 50px;
                        background-color: {styling['background_color']};
                        color: {styling['text_color']};
                        transition: all 0.5s ease;
                    }}
                    .status {{
                        background-color: {styling['accent_color']};
                        padding: 10px;
                        border-radius: 5px;
                        margin: 20px auto;
                        width: fit-content;
                        color: white;
                        font-weight: bold;
                    }}
                    a {{
                        color: {styling['accent_color']};
                        text-decoration: none;
                        margin: 0 10px;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                </style>
            </head>
            <body>
                <h1>📊 Contador de Visitas</h1>
                <div class="status">{styling['status']}</div>
                <p style="font-size: 24px;">¡Número de visitas: <strong>{visitas}</strong>! 🎉</p>
                <p>✅ Redis funcionando correctamente</p>
                <p><small>Visit ID: visit_{visitas}</small></p>
                <div>
                    <a href="/reiniciar">🔄 Reiniciar contador</a> | 
                    <a href="/health">❤️ Health check</a> |
                    <a href="/flag-status">🏁 Flag Status</a>
                </div>
            </body>
        </html>
        '''
    except Exception as e:
        return f'❌ Error: {str(e)}'

@app.route('/flag-status')
def flag_status():
    """Mostrar estado actual del feature flag"""
    try:
        # Crear target genérico para consultar estado
        target = Target(identifier="admin", name="Admin User")
        flag_active = client.bool_variation('dark_launch_styling', target, False)
        
        return f'''
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2>🏁 Feature Flag Status</h2>
                <p><strong>dark_launch_styling:</strong> {'🟢 ACTIVE' if flag_active else '🔴 INACTIVE'}</p>
                <a href="/">← Volver al contador</a>
            </body>
        </html>
        '''
    except Exception as e:
        return f'❌ Error checking flag: {str(e)}'

@app.route('/reiniciar')
def reiniciar_contador():
    try:
        redis_client = wait_for_redis()
        redis_client.set('visitas', 0)
        return '''
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2>✅ ¡Contador reiniciado!</h2>
                <a href="/">Volver al contador</a>
            </body>
        </html>
        '''
    except Exception as e:
        return f'❌ Error: {str(e)}'

@app.route('/health')
def health_check():
    try:
        redis_client = wait_for_redis()
        redis_client.ping()
        
        # Verificar conexión con Harness
        try:
            target = Target(identifier="health", name="Health Check")
            client.bool_variation('dark_launch_styling', target, False)
            harness_status = "✅ Connected"
        except:
            harness_status = "❌ Disconnected"
        
        return f'''
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2>❤️ Health Check</h2>
                <p><strong>Flask:</strong> ✅ Running</p>
                <p><strong>Redis:</strong> ✅ Connected</p>
                <p><strong>Harness:</strong> {harness_status}</p>
                <a href="/">← Volver</a>
            </body>
        </html>
        '''
    except Exception as e:
        return f'❌ Health check failed: {str(e)}'

if __name__ == '__main__':
    print("🚀 Iniciando aplicación Flask + Redis + Feature Flags...")
    app.run(host='0.0.0.0', port=5000)