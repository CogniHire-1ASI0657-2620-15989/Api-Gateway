# PathBridge API Gateway

Punto de entrada público para los microservicios de PathBridge. El gateway valida los JWT en las rutas protegidas y reenvía las solicitudes a Identity Service, Job Discovery Service y Gap Analysis Service. Para las solicitudes de empleos e informes de brechas agrega la identidad validada en el encabezado `X-User-Id` (el nombre puede configurarse con `GATEWAY_USER_ID_HEADER`).

Ejecuta el sistema completo desde la raíz con `docker compose up --build`. Si el gateway está publicado en el puerto `8080`, la base URL es `http://localhost:8080`. La especificación OpenAPI interactiva queda en `http://localhost:8080/docs`.

Las rutas `/api/v1/internal/*` no se exponen desde este servicio.

## Convenciones de integración

- Los ejemplos usan la base URL `http://localhost:8080`; reemplázala por la URL del entorno correspondiente.
- Los endpoints protegidos requieren `Authorization: Bearer <access_token>`. El token debe ser JWT firmado con HS256 y contener un `sub` numérico positivo, además de coincidir con el issuer y audience configurados en el gateway.
- `Content-Type: application/json` se usa en las solicitudes con cuerpo JSON.
- El gateway valida los cuerpos y parámetros indicados abajo, pero reenvía el cuerpo de respuesta y el código HTTP del microservicio. Los microservicios no están incluidos en este repositorio y el gateway no define esquemas de respuesta para sus operaciones de negocio. Los fragmentos de respuesta marcados como ilustrativos no constituyen un contrato; confirmar sus campos exactos en el OpenAPI del servicio upstream.
- Cuando se muestra `204 No Content`, no se debe intentar parsear un cuerpo JSON.

### Respuestas de error generadas por el gateway

| HTTP | Cuándo ocurre | Ejemplo de cuerpo |
| --- | --- | --- |
| `401 Unauthorized` | Falta el bearer token o el JWT no es válido. | `{"detail":"Token de autenticación requerido."}` o `{"detail":"Token de autenticación inválido."}` |
| `422 Unprocessable Entity` | Un parámetro o cuerpo no cumple las validaciones del gateway. | `{"detail":[{"loc":["body","email"],"msg":"value is not a valid email address","type":"value_error"}]}` |
| `502 Bad Gateway` | El microservicio destino no responde o no se puede conectar. | `{"detail":"El microservicio solicitado no está disponible."}` |

Los errores HTTP devueltos por un microservicio se reenvían al cliente con el mismo status y cuerpo. La estructura de esos errores depende del servicio.

## Identity Service

### Registrar usuario

`POST /api/v1/auth/register` (sin autenticación)

Request:

```http
POST /api/v1/auth/register
Content-Type: application/json
```

```json
{
	"name": "Ana Pérez",
	"email": "ana@example.com",
	"password": "ClaveSegura123",
	"segment": "professional",
	"city": "Bogotá",
	"country": "Colombia"
}
```

`name` es obligatorio (1-150 caracteres), `email` debe ser válido, `password` es obligatorio (6-128 caracteres) y `segment` es obligatorio. `city` y `country` son opcionales.

Respuesta de éxito esperada: `201 Created`. El cuerpo lo define Identity Service. El gateway no declara un esquema para el usuario creado; el frontend debe tratar el cuerpo como respuesta del servicio, no asumir que coincide con el request.

### Iniciar sesión

`POST /api/v1/auth/login` (sin autenticación)

Request:

```json
{
	"email": "ana@example.com",
	"password": "ClaveSegura123"
}
```

`email` debe ser válido y `password` debe tener entre 1 y 128 caracteres.

Respuesta de éxito esperada: `200 OK`. La forma del resultado (por ejemplo, los campos del token y del usuario) la define Identity Service y no está especificada en este gateway. El frontend debe obtener ese contrato del OpenAPI del servicio antes de integrar el manejo de sesión.

### Solicitar recuperación de contraseña

`POST /api/v1/auth/password-recovery` (sin autenticación)

Request:

```json
{
	"email": "ana@example.com"
}
```

`email` debe ser una dirección válida.

Respuesta de éxito esperada: `200 OK`. El cuerpo y el mensaje de confirmación dependen de Identity Service; no se debe asumir que la respuesta confirma si el correo está registrado.

### Restablecer contraseña

`POST /api/v1/auth/password-reset` (sin autenticación)

Request:

```json
{
	"token": "token-de-recuperacion-recibido-por-correo",
	"new_password": "NuevaClaveSegura123"
}
```

`token` debe tener al menos 20 caracteres y `new_password` entre 6 y 128 caracteres.

Respuesta de éxito esperada: `204 No Content`; no hay cuerpo de respuesta.

### Consultar perfil propio

`GET /api/v1/profile/me` (requiere autenticación)

Request:

```http
GET /api/v1/profile/me
Authorization: Bearer <access_token>
```

Respuesta de éxito esperada: `200 OK`. Identity Service define los campos del perfil. El modelo de actualización permite los campos descritos en «Actualizar perfil», pero el gateway no garantiza que la respuesta de consulta tenga exactamente esa misma forma.

### Actualizar perfil propio

`PUT /api/v1/profile/me` (requiere autenticación)

Request: todos los campos son opcionales; envía solo los que se desean actualizar.

```json
{
	"name": "Ana Pérez Gómez",
	"segment": "professional",
	"city": "Medellín",
	"country": "Colombia",
	"target_position": "Backend Developer",
	"expected_city": "Medellín",
	"expected_country": "Colombia",
	"work_modality": "hibrido",
	"hard_skills": [
		{"name": "Python", "level": "avanzado"},
		{"name": "FastAPI", "level": "intermedio"}
	],
	"soft_skills": [{"name": "Comunicación", "level": "avanzado"}],
	"education": [
		{
			"degree": "Ingeniería de Sistemas",
			"institution": "Universidad Nacional",
			"field_of_study": "Sistemas",
			"start_year": 2018,
			"end_year": 2023
		}
	],
	"experience": [
		{
			"position": "Desarrolladora backend",
			"company": "Acme",
			"description": "Desarrollo de APIs.",
			"start_date": "2023-01",
			"end_date": null,
			"current": true
		}
	],
	"languages": [{"name": "Español", "level": "nativo"}],
	"professional_summary": "Desarrolladora backend enfocada en APIs y servicios web."
}
```

Campos admitidos: `name` (1-150 caracteres), `email` (válido), `segment`, `city`, `country`, `target_position` (máximo 150), `expected_city` y `expected_country` (máximo 100), `work_modality` (`remoto`, `hibrido` o `presencial`), `hard_skills`, `soft_skills`, `education`, `experience`, `languages` y `professional_summary` (máximo 2000). Cada elemento de skills/languages admite `name` (1-100) y `level` opcional (máximo 50). Educación admite `degree`, `institution`, `field_of_study` (máximo 150) y años opcionales entre 1900 y 2100. Experiencia admite `position`, `company` (máximo 150), `description` (máximo 2000), `start_date` y `end_date` (máximo 20), y `current` (booleano, por defecto `false`).

Respuesta de éxito esperada: `200 OK`. El cuerpo depende de Identity Service.

### Cambiar contraseña

`PUT /api/v1/profile/me/password` (requiere autenticación)

Request:

```json
{
	"current_password": "ClaveActual123",
	"new_password": "NuevaClaveSegura123"
}
```

`new_password` debe tener entre 6 y 128 caracteres. `current_password` es obligatorio.

Respuesta de éxito esperada: `200 OK`. La respuesta (con o sin cuerpo) depende de Identity Service.

### Agregar una habilidad

`POST /api/v1/profile/me/skills/{skill_type}` (requiere autenticación)

`skill_type` identifica el tipo de habilidad aceptado por Identity Service. El gateway no restringe sus valores.

Request:

```json
{
	"name": "Python",
	"level": "avanzado"
}
```

`name` es obligatorio (1-100 caracteres) y `level` es opcional (máximo 50).

Respuesta de éxito esperada: `200 OK`. La forma depende de Identity Service.

### Actualizar una habilidad

`PUT /api/v1/profile/me/skills/{skill_type}/{skill_name}` (requiere autenticación)

Request:

```json
{
	"name": "Python",
	"level": "experto"
}
```

El cuerpo sigue las mismas reglas que al agregar una habilidad. `skill_type` y `skill_name` forman parte de la ruta y se reenvían al servicio.

Respuesta de éxito esperada: `200 OK`. La forma depende de Identity Service.

### Eliminar una habilidad

`DELETE /api/v1/profile/me/skills/{skill_type}/{skill_name}` (requiere autenticación)

Request: no requiere cuerpo. `skill_type` y `skill_name` forman parte de la ruta.

Respuesta de éxito esperada: `200 OK` según el status predeterminado del gateway; el status real y cuerpo devueltos por Identity Service se reenvían sin cambios.

## Job Discovery Service

Todos los endpoints de este servicio requieren `Authorization: Bearer <access_token>`. El gateway valida el token y envía el identificador de usuario en `X-User-Id`.

### Buscar empleos

`GET /api/v1/jobs`

Parámetros query:

| Parámetro | Requerido | Reglas | Predeterminado |
| --- | --- | --- | --- |
| `keywords` | Sí | 1-200 caracteres | — |
| `location` | Sí | 1-200 caracteres | — |
| `page` | No | Entero entre 1 y 3 | `1` |
| `page_size` | No | Entero entre 1 y 20 | `10` |
| `radius_km` | No | `0`, `4`, `8`, `16`, `26`, `40` o `80` | `0` |

Request:

```http
GET /api/v1/jobs?keywords=Python&location=Bogota&page=1&page_size=10&radius_km=16
Authorization: Bearer <access_token>
```

Respuesta de éxito esperada: `200 OK`. El cuerpo (lista, paginación y campos de cada empleo) depende de Job Discovery Service. Ejemplo solo ilustrativo, no contractual:

```json
{
	"items": [
		{
			"id": 4821,
			"title": "Backend Developer",
			"company": "Acme",
			"location": "Bogotá",
			"is_favorite": false
		}
	],
	"page": 1,
	"page_size": 10
}
```

### Obtener detalle de empleo

`GET /api/v1/jobs/{job_id}` (requiere autenticación)

Request:

```http
GET /api/v1/jobs/4821
Authorization: Bearer <access_token>
```

`job_id` debe ser un entero. Respuesta de éxito esperada: `200 OK`; el esquema del detalle depende de Job Discovery Service. El servicio también puede devolver, por ejemplo, `404 Not Found` si el empleo no existe.

### Marcar empleo como favorito

`POST /api/v1/jobs/{job_id}/favorite` (requiere autenticación)

Request:

```http
POST /api/v1/jobs/4821/favorite
Authorization: Bearer <access_token>
```

No requiere cuerpo. Respuesta de éxito esperada: `200 OK`; cuerpo definido por Job Discovery Service.

### Quitar empleo de favoritos

`DELETE /api/v1/jobs/{job_id}/favorite` (requiere autenticación)

Request:

```http
DELETE /api/v1/jobs/4821/favorite
Authorization: Bearer <access_token>
```

No requiere cuerpo. Respuesta de éxito esperada: `204 No Content`; no hay cuerpo de respuesta.

### Listar empleos favoritos

`GET /api/v1/favorites` (requiere autenticación)

Parámetros query: `page` (entero desde 1, predeterminado `1`) y `page_size` (entero entre 1 y 50, predeterminado `20`).

Request:

```http
GET /api/v1/favorites?page=1&page_size=20
Authorization: Bearer <access_token>
```

Respuesta de éxito esperada: `200 OK`. La forma de la lista y su paginación depende de Job Discovery Service.

## Gap Analysis Service

Todos los endpoints de este servicio requieren `Authorization: Bearer <access_token>`. El gateway valida el token y envía el identificador de usuario en `X-User-Id`.

### Generar informe de brechas

`POST /api/v1/gap-reports` (requiere autenticación)

Request:

```json
{
	"job_id": 4821
}
```

`job_id` es obligatorio y debe ser un entero mayor que cero.

Respuesta de éxito esperada: `201 Created`. La estructura y el estado del informe (por ejemplo, si el análisis es inmediato o asíncrono) dependen de Gap Analysis Service; el gateway no los define.

### Consultar informe de brechas

`GET /api/v1/gap-reports/{job_id}` (requiere autenticación)

Request:

```http
GET /api/v1/gap-reports/4821
Authorization: Bearer <access_token>
```

`job_id` debe ser un entero. Respuesta de éxito esperada: `200 OK`. El esquema, el contenido del análisis y los estados de procesamiento dependen de Gap Analysis Service. El servicio puede responder, por ejemplo, `404 Not Found` si no hay un informe disponible.

### Listar informes de brechas

`GET /api/v1/gap-reports` (requiere autenticación)

Request:

```http
GET /api/v1/gap-reports
Authorization: Bearer <access_token>
```

Respuesta de éxito esperada: `200 OK`. La estructura de la colección depende de Gap Analysis Service.

## API Gateway

### Health check

`GET /health` (sin autenticación)

Request:

```http
GET /health
```

Respuesta `200 OK`:

```json
{
	"service": "api-gateway",
	"status": "healthy"
}
```
