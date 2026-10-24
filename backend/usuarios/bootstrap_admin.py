"""Explicit interactive setup for the first active administrator."""

from getpass import getpass
import sys

from backend.database import initialize_database
from backend.usuarios.service import AccountConflictError, create_initial_admin


def main() -> int:
    initialize_database()
    print("Configuración inicial del primer administrador")
    full_name = input("Nombre completo: ")
    institutional_email = input("Correo institucional (@universidad.edu.co): ")
    password = getpass("Contraseña (mínimo 12 caracteres): ")

    try:
        user = create_initial_admin(
            full_name=full_name,
            institutional_email=institutional_email,
            password=password,
        )
    except (AccountConflictError, ValueError) as error:
        print(f"No se creó el administrador inicial: {error}", file=sys.stderr)
        return 1

    print(f"Administrador inicial creado para {user['institutional_email']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
