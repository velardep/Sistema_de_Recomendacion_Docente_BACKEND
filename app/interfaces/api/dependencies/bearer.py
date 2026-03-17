# app/interfaces/api/dependencies/bearer.py

# Este archivo maneja la extracción y validación
# del token de acceso Bearer desde los headers de las peticiones HTTP.
# Proporciona una función para obtener el token de autorización,
# verificando que esté presente y en el formato correcto.
# Se utiliza en las dependencias de FastAPI para autenticar usuarios.

# Importa componentes de FastAPI para manejar headers y excepciones HTTP
from fastapi import Header, HTTPException

# Extrae y valida el token Bearer del header de autorización
def get_access_token(authorization: str = Header(default="")) -> str:
    # Verifica que el header comience con "Bearer "
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    # Separa el token del prefijo y lo devuelve limpio
    return authorization.split(" ", 1)[1].strip()


