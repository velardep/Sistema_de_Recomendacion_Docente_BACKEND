# app/interfaces/api/schemas/auth.py

# Este archivo define los esquemas de Pydantic para las solicitudes de autenticación.
# Incluye modelos para registro y login de usuarios, validando email y contraseña.
# Utiliza EmailStr para validación de correos y Field para restricciones de contraseña.
# Forma parte de la validación de entrada en los endpoints de auth.

# Librerías - Pydantic
from pydantic import BaseModel, EmailStr, Field

# Modelo Pydantic para solicitud de registro de usuario.
# Valida que el email sea válido y la contraseña tenga al menos 6 caracteres.
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)

# Modelo Pydantic para solicitud de login de usuario.
# Valida que el email sea válido y la contraseña tenga al menos 6 caracteres.
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
